"""关系维基层回归测试（摄入时编译的主题页面记忆）。

覆盖：WikiStore CRUD/版本/用户隔离/LRU 归档/统计、编译解析（反幻觉契约/
类目路由/畸形 JSON）、prompt 构造、注入格式化与截断、双开关、TaskManager 接线。
"""

import asyncio
import json

import pytest

from memory import relationship_wiki as rw


@pytest.fixture
def cfg(tmp_path):
    """独立配置：tmp 库 + 小页数上限便于测归档"""
    config = dict(rw.DEFAULT_CONFIG)
    config["db_path"] = str(tmp_path / "wiki_test.db")
    config["max_pages_per_user"] = 3
    rw._config_cache = config
    yield config
    rw._config_cache = None


@pytest.fixture
def store(cfg):
    return rw.WikiStore(db_path=cfg["db_path"])


def _run(coro):
    return asyncio.run(coro)


# ==================== WikiStore ====================

class TestWikiStore:
    def test_upsert_and_version_increment(self, store):
        v1 = _run(
            store.upsert_page("u1", "page_a", "披萨偏好", "饮食口味", "摘要", "正文v1", ["2026-09-12"])
        )
        v2 = _run(
            store.upsert_page("u1", "page_a", "披萨偏好", "饮食口味", "摘要", "正文v2", ["2026-09-13"])
        )
        assert v1 == 1 and v2 == 2
        pages = _run(store.list_pages("u1"))
        assert len(pages) == 1
        assert pages[0]["content_md"] == "正文v2"
        assert pages[0]["source_refs"] == ["2026-09-13"]

    def test_user_isolation(self, store):
        _run(store.upsert_page("u1", "secret", "隐私页", "其他", "s", "c", []))
        assert _run(store.list_pages("u2")) == []
        assert _run(store.list_pages("")) == []
        # dump 全量可见（调试口），指定用户只见自己的
        assert len(_run(store.dump_pages())) == 1
        assert _run(store.dump_pages("u2")) == []

    def test_lru_archive_on_cap(self, store):
        for i in range(4):  # 上限 3（fixture 配置）
            _run(
                store.upsert_page("u1", f"p{i}", f"页{i}", "其他", "s", "c", [])
            )
            if i < 3:
                import time

                time.sleep(0.01)  # 保证 updated_at 单调
        pages = _run(store.list_pages("u1"))
        assert len(pages) == 3
        assert all(p["status"] == "active" for p in pages)
        stats = _run(store.get_stats())
        assert stats["archived"] == 1
        assert stats["active"] == 3

    def test_stats_stale_no_source_oversized(self, store, cfg):
        _run(store.upsert_page("u1", "with_src", "有源页", "其他", "s", "c", ["2026-09-12"]))
        _run(store.upsert_page("u1", "no_src", "无源页", "其他", "s", "c", []))
        stats = _run(store.get_stats())
        assert stats["no_source"] == 1
        assert stats["active"] == 2

    def test_no_user_id_rejected(self, store):
        v = _run(store.upsert_page("", "x", "t", "其他", "s", "c", []))
        assert v == 0


# ==================== 编译解析与 prompt ====================

class TestExtractUpdates:
    def test_valid_update(self, cfg):
        raw = json.dumps(
            {
                "updates": [
                    {
                        "page_id": "pisa",
                        "title": "披萨偏好",
                        "category": "饮食口味",
                        "summary": "喜欢番茄酱多",
                        "content_md": "- [2026-09-12] 喜欢番茄酱多的披萨",
                        "source_refs": ["2026-09-12"],
                    }
                ]
            },
            ensure_ascii=False,
        )
        updates = rw.extract_updates(raw, cfg)
        assert len(updates) == 1
        assert updates[0]["category"] == "饮食口味"
        assert updates[0]["page_id"] == "pisa"

    def test_invalid_category_falls_back(self, cfg):
        raw = json.dumps(
            {"updates": [{"title": "T", "category": "不存在的类目", "content_md": "c"}]},
            ensure_ascii=False,
        )
        updates = rw.extract_updates(raw, cfg)
        assert updates[0]["category"] == "其他"
        assert updates[0]["page_id"]  # 标题自动规范化为 slug

    def test_malformed_json_returns_empty(self, cfg):
        assert rw.extract_updates("这不是JSON", cfg) == []
        assert rw.extract_updates('{"updates": "不是列表"}', cfg) == []
        assert rw.extract_updates("", cfg) == []

    def test_invalid_entries_skipped_and_truncated(self, cfg):
        raw = json.dumps(
            {
                "updates": [
                    {"title": "", "content_md": "无标题跳过"},
                    {"title": "超长页", "content_md": "长" * 5000},
                    "不是字典",
                ]
            },
            ensure_ascii=False,
        )
        updates = rw.extract_updates(raw, cfg)
        assert len(updates) == 1
        assert len(updates[0]["content_md"]) <= cfg["max_page_chars"]


class TestCompilePrompt:
    def test_contains_anti_hallucination_and_categories(self, cfg):
        prompt = rw.build_compile_prompt(
            conversation_text="用户: 我爱吃番茄酱多的披萨\n弥娅: 记住啦~",
            index_text="《旧页》[其他] 摘要",
            candidates_text="《旧页》[其他] 正文",
            categories=cfg["categories"],
            max_page_chars=2000,
            max_updates=2,
        )
        assert "禁止推测" in prompt
        assert "禁止补全" in prompt
        assert "饮食口味" in prompt
        assert "其他" in prompt
        assert "番茄酱" in prompt  # 对话片段在 prompt 中
        assert "矛盾" in prompt and "历史注记" in prompt  # 矛盾处理规则

    def test_no_updates_output_documented(self, cfg):
        prompt = rw.build_compile_prompt("对话", "索引", "候选", cfg["categories"], 2000, 2)
        assert '"updates": []' in prompt


class TestScoreAndFormat:
    def _pages(self):
        return [
            {"title": "披萨偏好", "category": "饮食口味", "summary": "番茄酱", "content_md": "正文A"},
            {"title": "游戏进度", "category": "兴趣爱好", "summary": "某游戏", "content_md": "正文B"},
        ]

    def test_title_hit_ranks_higher(self, cfg):
        ranked = rw.score_pages(self._pages(), ["披萨"])
        assert ranked[0]["title"] == "披萨偏好"

    def test_select_candidate_truncates(self, cfg):
        pages = [{"title": "长页", "category": "其他", "summary": "s", "content_md": "长" * 3000}]
        picked = rw.select_candidate_pages(pages, ["长页"], 2, 100)
        assert len(picked[0]["content_md"]) == 100

    def test_format_contains_declaration_and_truncates(self, cfg):
        pages = [{"title": "披萨偏好", "category": "饮食口味", "summary": "s", "content_md": "正文" * 500}]
        ctx = _run(rw.fetch_wiki_context("u1", "披萨好吃吗", config=cfg, store=_FakeStore(pages)))
        assert "关系维基" in ctx
        assert "可能有误" in ctx  # 框架声明
        assert "以原文为准" in ctx
        assert len(ctx) <= cfg["inject_max_chars"] + 2  # 截断 + 省略号

    def test_format_empty_pages_returns_empty(self, cfg):
        assert _run(rw.fetch_wiki_context("u1", "任意", config=cfg, store=_FakeStore([]))) == ""


class _FakeStore:
    def __init__(self, pages):
        self._pages = pages

    async def list_pages(self, user_id, status="active", limit=0):
        if not user_id:
            return []
        return self._pages


# ==================== fetch / compile 端到端（mock client） ====================

class _FakeClient:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    async def chat(self, messages, **kwargs):
        self.kwargs = kwargs
        return self.response


class TestFetchWikiContext:
    async def test_empty_user_id_returns_empty(self, cfg, store):
        assert await rw.fetch_wiki_context("", "x", config=cfg, store=store) == ""

    async def test_inject_disabled_returns_empty(self, cfg, store):
        cfg2 = dict(cfg, inject_enabled=False)
        await store.upsert_page("u1", "p", "T", "其他", "s", "c", [])
        assert await rw.fetch_wiki_context("u1", "T", config=cfg2, store=store) == ""


class TestCompileAndStore:
    async def test_disabled_skips(self, cfg, store):
        cfg2 = dict(cfg, compile_enabled=False)
        result = await rw.compile_and_store(
            {"user_id": "u1", "user_input": "abc", "ai_response": "def"},
            config=cfg2,
            store=store,
        )
        assert result["skipped"] == "disabled"

    async def test_no_user_id_skips(self, cfg, store):
        result = await rw.compile_and_store(
            {"user_id": "", "user_input": "abc", "ai_response": "def"}, config=cfg, store=store
        )
        assert result["skipped"] == "no_user_id"

    async def test_happy_path_stores_page_and_passes_flags(self, cfg, store):
        response = json.dumps(
            {
                "updates": [
                    {
                        "page_id": "pisa",
                        "title": "披萨偏好",
                        "category": "饮食口味",
                        "summary": "喜欢番茄酱",
                        "content_md": "- [2026-09-12] 喜欢番茄酱多的披萨",
                        "source_refs": ["2026-09-12"],
                    }
                ]
            },
            ensure_ascii=False,
        )
        fake = _FakeClient(response)
        result = await rw.compile_and_store(
            {"user_id": "u1", "user_input": "我爱吃番茄酱多的披萨", "ai_response": "记住啦"},
            client=fake,
            config=cfg,
            store=store,
        )
        assert result["pages_updated"] == 1
        # 关键契约：判断调用不得带弥娅人设/工具
        assert fake.kwargs["use_miya_prompt"] is False
        assert fake.kwargs["tools"] == []
        pages = await store.list_pages("u1")
        assert pages[0]["title"] == "披萨偏好"

    async def test_duplicate_conversation_skipped(self, cfg, store):
        payload = {"user_id": "u1", "user_input": "同一句话测试", "ai_response": "好的"}
        fake = _FakeClient('{"updates": []}')
        await rw.compile_and_store(payload, client=fake, config=cfg, store=store)
        result = await rw.compile_and_store(payload, client=fake, config=cfg, store=store)
        assert result["skipped"] == "duplicate"

    async def test_client_error_skips_without_write(self, cfg, store):
        class _BoomClient:
            async def chat(self, messages, **kwargs):
                raise RuntimeError("api down")

        result = await rw.compile_and_store(
            {"user_id": "u1", "user_input": " 内容足够长 ", "ai_response": "回复也长"},
            client=_BoomClient(),
            config=cfg,
            store=store,
        )
        assert result["pages_updated"] == 0
        assert result["skipped"].startswith("error")
        assert await store.list_pages("u1") == []

    async def test_short_conversation_skipped(self, cfg, store):
        result = await rw.compile_and_store(
            {"user_id": "u1", "user_input": "嗯", "ai_response": "好"}, config=cfg, store=store
        )
        assert result["skipped"] == "too_short"


# ==================== TaskManager 接线 ====================

class _StubTaskManager:
    def __init__(self):
        self.handlers = {}
        self.tasks = []

    def register_handler(self, task_type, handler):
        self.handlers[task_type] = handler

    async def add_task(self, task_type, payload, task_id=None, max_retries=3):
        self.tasks.append((task_type, payload, max_retries))
        return "tid-1"


async def test_submit_registers_and_enqueues():
    tm = _StubTaskManager()
    task_id = await rw.submit_wiki_update(
        {"user_id": "u1", "user_input": "a", "ai_response": "b"}, task_manager=tm
    )
    assert task_id == "tid-1"
    assert "wiki_update" in tm.handlers
    assert tm.tasks[0][0] == "wiki_update"
    assert tm.tasks[0][2] == 2  # max_retries

async def test_submit_disabled_returns_none():
    old = rw._config_cache
    rw._config_cache = dict(rw.DEFAULT_CONFIG, compile_enabled=False)
    try:
        assert await rw.submit_wiki_update({"user_id": "u1"}, task_manager=_StubTaskManager()) is None
    finally:
        rw._config_cache = old


async def test_submit_no_user_returns_none():
    assert await rw.submit_wiki_update({"user_id": ""}, task_manager=_StubTaskManager()) is None


def test_handler_registered_callable():
    tm = _StubTaskManager()
    rw.register_wiki_handler(tm)
    assert callable(tm.handlers["wiki_update"])
