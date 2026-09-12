"""
关系维基层 — 摄入时编译的主题页面记忆（LLM Wiki 思想的关系记忆实现）

设计（三段式）：
  1. 原始情节层（现有 SQLite 记忆核心，永不删除）——事实源头
  2. 维基内容层（本模块 wiki_pages 表）——对话摄入时由 LLM 编译的主题页面，
     每页 = 一个演化中的话题状态（多事实、带日期、最新在前）
  3. 规则层（编译 prompt 内置）——反幻觉条款 / 矛盾以后到为准并留历史注记 / 只记稳定事实

隐私硬约束（对齐 core/stable_persona.py 惯例）：无 user_id 不读不写，页按用户隔离。
失败语义：编译超时/解析失败整体跳过，页面保持上一版（宁缺毋滥，绝不写半页）。

配置段：config/text_config.json 顶层 "relationship_wiki"（类目/双开关/阈值）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "compile_enabled": True,
    "inject_enabled": True,
    "db_path": "data/memory/miya_memory.db",
    "categories": [
        "饮食口味",
        "生活作息",
        "工作学习",
        "兴趣爱好",
        "身体健康",
        "情绪心理",
        "人际关系",
        "共同经历",
        "计划打算",
        "其他",
    ],
    "timeout": 30,
    "min_content_len": 6,
    "max_pages_per_user": 50,
    "max_page_chars": 2000,
    "candidate_pages": 2,
    "candidate_page_chars": 1500,
    "index_pages": 50,
    "inject_max_pages": 2,
    "inject_max_chars": 800,
    "stale_days": 30,
}

_config_cache: Optional[Dict[str, Any]] = None


def _get_config(force_reload: bool = False) -> Dict[str, Any]:
    """加载关系维基配置（DEFAULT_CONFIG ⊆ text_config.relationship_wiki）"""
    global _config_cache
    if _config_cache is None or force_reload:
        cfg = dict(DEFAULT_CONFIG)
        try:
            from memory.memory_config import get_memory_section

            cfg.update(get_memory_section("relationship_wiki") or {})
        except Exception as e:  # noqa: BLE001 — 配置失败用内置默认
            logger.debug(f"[关系维基] 配置加载失败，使用默认: {e}")
        _config_cache = cfg
    return _config_cache


# ==================== WikiStore ====================

class WikiStore:
    """wiki_pages 表存储（复用 miya_memory.db，DDL 风格对齐 graph_store）"""

    def __init__(self, db_path: Optional[str] = None):
        cfg = _get_config()
        self.db_path = Path(db_path or cfg.get("db_path", "data/memory/miya_memory.db"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._init_db()

    def _init_db(self):
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wiki_pages (
                page_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '其他',
                summary TEXT NOT NULL DEFAULT '',
                content_md TEXT NOT NULL DEFAULT '',
                source_refs TEXT NOT NULL DEFAULT '[]',
                version INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'active',
                updated_at REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, page_id)
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wiki_user ON wiki_pages(user_id, status, updated_at DESC)"
        )
        self._conn.commit()

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        d = dict(row)
        try:
            d["source_refs"] = json.loads(d.get("source_refs") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["source_refs"] = []
        return d

    async def upsert_page(
        self,
        user_id: str,
        page_id: str,
        title: str,
        category: str,
        summary: str,
        content_md: str,
        source_refs: Optional[List[str]] = None,
    ) -> int:
        """写入页面（同 user+page_id 覆盖，version 递增）；超限 LRU 归档"""
        if not user_id or not page_id:
            return 0
        cfg = _get_config()
        max_chars = int(cfg.get("max_page_chars", 2000))
        content_md = (content_md or "")[:max_chars]
        row = self._conn.execute(
            "SELECT version FROM wiki_pages WHERE user_id=? AND page_id=?",
            (user_id, page_id),
        ).fetchone()
        version = (row["version"] + 1) if row else 1
        self._conn.execute(
            """
            INSERT OR REPLACE INTO wiki_pages
                (page_id, user_id, title, category, summary, content_md, source_refs, version, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
            """,
            (
                page_id,
                user_id,
                title,
                category,
                summary,
                content_md,
                json.dumps(source_refs or [], ensure_ascii=False),
                version,
                time.time(),
            ),
        )
        self._conn.commit()
        await self._enforce_page_cap(user_id)
        return version

    async def _enforce_page_cap(self, user_id: str):
        """每用户 active 页数超限时，按 updated_at 最旧归档"""
        cfg = _get_config()
        cap = int(cfg.get("max_pages_per_user", 50))
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM wiki_pages WHERE user_id=? AND status='active'", (user_id,)
        ).fetchone()
        overflow = row["n"] - cap
        if overflow <= 0:
            return
        stale_rows = self._conn.execute(
            """
            SELECT page_id FROM wiki_pages
            WHERE user_id=? AND status='active'
            ORDER BY updated_at ASC LIMIT ?
            """,
            (user_id, overflow),
        ).fetchall()
        for r in stale_rows:
            self._conn.execute(
                "UPDATE wiki_pages SET status='archived' WHERE user_id=? AND page_id=?",
                (user_id, r["page_id"]),
            )
        self._conn.commit()
        logger.info(f"[关系维基] 用户 {user_id} 页数超限，归档 {overflow} 个最旧页面")

    async def list_pages(self, user_id: str, status: str = "active", limit: int = 0) -> List[Dict[str, Any]]:
        if not user_id:
            return []
        sql = "SELECT * FROM wiki_pages WHERE user_id=? AND status=? ORDER BY updated_at DESC"
        params: list = [user_id, status]
        if limit > 0:
            sql += " LIMIT ?"
            params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    async def get_stats(self) -> Dict[str, int]:
        cfg = _get_config()
        stale_cutoff = time.time() - int(cfg.get("stale_days", 30)) * 86400
        max_chars = int(cfg.get("max_page_chars", 2000))
        row = self._conn.execute(
            """
            SELECT
                SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN status='archived' THEN 1 ELSE 0 END) AS archived,
                SUM(CASE WHEN status='active' AND updated_at < ? THEN 1 ELSE 0 END) AS stale,
                SUM(CASE WHEN status='active' AND source_refs='[]' THEN 1 ELSE 0 END) AS no_source,
                SUM(CASE WHEN status='active' AND length(content_md) > ? THEN 1 ELSE 0 END) AS oversized
            FROM wiki_pages
            """,
            (stale_cutoff, max_chars),
        ).fetchone()
        return {
            "active": row["active"] or 0,
            "archived": row["archived"] or 0,
            "stale": row["stale"] or 0,
            "no_source": row["no_source"] or 0,
            "oversized": row["oversized"] or 0,
        }

    async def dump_pages(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """调试接口：导出页面（全量或指定用户）供人工审阅"""
        if user_id:
            rows = self._conn.execute(
                "SELECT * FROM wiki_pages WHERE user_id=? ORDER BY updated_at DESC", (user_id,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM wiki_pages ORDER BY updated_at DESC").fetchall()
        return [self._row_to_dict(r) for r in rows]


_wiki_store: Optional[WikiStore] = None


def get_wiki_store() -> WikiStore:
    global _wiki_store
    if _wiki_store is None:
        _wiki_store = WikiStore()
    return _wiki_store


# ==================== 编译：候选页预选 / prompt / 解析 ====================

def normalize_page_id(title: str) -> str:
    """标题 → 页面 slug（保留中英文数字，截 40 字；空则 md5 兜底）"""
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "", (title or "").strip()).lower()[:40]
    return slug or hashlib.md5(str(time.time()).encode()).hexdigest()[:12]


def extract_keywords_from_text(text: str) -> List[str]:
    """页面匹配关键词：优先复用认知引擎的分词（与认知记忆同一视角），失败回退正则"""
    text = text or ""
    try:
        from memory.cognitive_engine import get_cognitive_engine

        engine = get_cognitive_engine()
        kws = list(engine._extract_topics(text)) + list(engine._extract_keywords(text))  # noqa: SLF001
        if kws:
            return [k for k in dict.fromkeys(kws) if k]
    except Exception as e:  # noqa: BLE001 — 认知引擎不可用时回退
        logger.debug(f"[关系维基] 认知引擎分词不可用，回退正则: {e}")
    return [seg for seg in re.findall(r"[\u4e00-\u9fff]{2,6}|[a-zA-Z0-9]{2,}", text)][:12]


def score_pages(pages: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
    """关键词对页面打分：标题命中×3 + 摘要命中×2 + 类目命中×1，按分降序"""
    scored = []
    for page in pages:
        title = page.get("title", "")
        summary = page.get("summary", "")
        category = page.get("category", "")
        score = 0.0
        for kw in keywords:
            if kw and kw in title:
                score += 3
            if kw and kw in summary:
                score += 2
            if kw and kw in category:
                score += 1
        scored.append((score, page))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored]


def select_candidate_pages(
    pages: List[Dict[str, Any]], keywords: List[str], limit: int, max_chars: int
) -> List[Dict[str, Any]]:
    """编译候选页：按分取 top-N，正文截断（进 prompt 的全量页）"""
    candidates = []
    for page in score_pages(pages, keywords)[:limit]:
        capped = dict(page)
        capped["content_md"] = (page.get("content_md") or "")[:max_chars]
        candidates.append(capped)
    return candidates


def build_pages_index_text(pages: List[Dict[str, Any]], limit: int) -> str:
    """页面索引进 prompt：每页一行《标题》[类目] 摘要"""
    lines = []
    for page in pages[:limit]:
        lines.append(f"《{page.get('title', '')}》[{page.get('category', '其他')}] {page.get('summary', '')}")
    return "\n".join(lines)


def build_compile_prompt(
    conversation_text: str,
    index_text: str,
    candidates_text: str,
    categories: List[str],
    max_page_chars: int,
    max_updates: int,
) -> str:
    """编译 prompt：反幻觉条款 + 矛盾处理 + 类目路由 + 边界说明"""
    cat_text = "、".join(categories)
    return f"""你是弥娅的记忆编译器。根据下面的对话片段，维护"关系维基"主题页面（记录这位用户生活中持续演化的 topics）。

【维基页面索引（现有页面）】
{index_text or "（暂无页面）"}

【候选页面全文（可能与本对话相关）】
{candidates_text or "（无）"}

【对话片段】
{conversation_text}

【编译规则】
1. 只提取对话中明确出现的稳定事实与状态变化，禁止推测、禁止补全对话之外的内容（反幻觉：宁缺毋滥）
2. 寒暄、客套、一次性细节（"今天吃了"若无长期意义）不值得记页面，直接返回空更新
3. 与稳定画像的边界：恒定核心属性（身份/关系定性）不进维基页；这里记演化中的话题状态
4. 矛盾处理：新事实与页面旧事实冲突时，新事实在前，旧事实降级为历史注记（"曾…（后变化）"），不删除
5. 每条事实必须带 [YYYY-MM-DD] 日期标注（今天为 {time.strftime("%Y-%m-%d")}）
6. category 只能从这些类目里选：{cat_text}；拿不准就选"其他"
7. 单页正文不超过 {max_page_chars} 字；本次最多更新 {max_updates} 个页面；page_id 用标题的规范化形式

【输出格式】只返回 JSON 对象，不要 markdown 代码块：
{{"updates": [{{"page_id": "...", "title": "...", "category": "...", "summary": "一句话", "content_md": "整页Markdown正文", "source_refs": ["{time.strftime("%Y-%m-%d")}")"}}]}}
没有值得更新的内容时返回：{{"updates": []}}"""


def extract_updates(raw: str, config: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """解析 LLM 返回的 updates（宽松 JSON 提取；非法项跳过；类目非法回退"其他"；正文截断）"""
    cfg = config or _get_config()
    categories = list(cfg.get("categories", DEFAULT_CONFIG["categories"]))
    max_chars = int(cfg.get("max_page_chars", 2000))
    try:
        match = re.search(r"\{.*\}", raw or "", re.DOTALL)
        if not match:
            return []
        data = json.loads(match.group(0))
        updates = data.get("updates") if isinstance(data, dict) else None
        if not isinstance(updates, list):
            return []
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.debug(f"[关系维基] 编译结果解析失败，跳过: {e}")
        return []

    valid = []
    for item in updates:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        content_md = str(item.get("content_md", "")).strip()
        if not title or not content_md:
            continue  # 缺标题或正文 = 无效页
        category = str(item.get("category", "")).strip()
        if category not in categories:
            category = "其他"
        valid.append(
            {
                "page_id": str(item.get("page_id", "")).strip() or normalize_page_id(title),
                "title": title,
                "category": category,
                "summary": str(item.get("summary", "")).strip()[:120],
                "content_md": content_md[:max_chars],
                "source_refs": [str(x) for x in (item.get("source_refs") or [])][:20],
            }
        )
    return valid


# ==================== 编译执行（TaskManager handler） ====================

_compiled_hashes: set = set()


async def compile_and_store(
    payload: Dict[str, Any],
    client: Any = None,
    config: Optional[Dict] = None,
    store: Optional[WikiStore] = None,
) -> Dict[str, Any]:
    """编译一次对话并落库（TaskManager worker 中执行；任何失败跳过不抛出）"""
    cfg = config or _get_config()
    result: Dict[str, Any] = {"pages_updated": 0, "skipped": None}

    if not cfg.get("compile_enabled", True):
        result["skipped"] = "disabled"
        return result
    user_id = str(payload.get("user_id") or "").strip()
    if not user_id:
        result["skipped"] = "no_user_id"
        return result
    user_input = str(payload.get("user_input") or "")
    ai_response = str(payload.get("ai_response") or "")
    if len(user_input) + len(ai_response) < int(cfg.get("min_content_len", 6)):
        result["skipped"] = "too_short"
        return result

    conversation_text = f"用户: {user_input}\n弥娅: {ai_response}"
    text_hash = hashlib.md5(conversation_text.encode()).hexdigest()
    if text_hash in _compiled_hashes:
        result["skipped"] = "duplicate"
        return result
    _compiled_hashes.add(text_hash)
    if len(_compiled_hashes) > 1024:
        _compiled_hashes.clear()

    store = store or get_wiki_store()
    pages = await store.list_pages(user_id)
    keywords = extract_keywords_from_text(user_input)
    candidates = select_candidate_pages(
        pages,
        keywords,
        int(cfg.get("candidate_pages", 2)),
        int(cfg.get("candidate_page_chars", 1500)),
    )
    candidates_text = "\n\n".join(
        f"《{p['title']}》[{p['category']}]（版本 {p.get('version', 1)}）\n{p['content_md']}" for p in candidates
    )
    prompt = build_compile_prompt(
        conversation_text=conversation_text,
        index_text=build_pages_index_text(pages, int(cfg.get("index_pages", 50))),
        candidates_text=candidates_text,
        categories=list(cfg.get("categories", DEFAULT_CONFIG["categories"])),
        max_page_chars=int(cfg.get("max_page_chars", 2000)),
        max_updates=int(cfg.get("candidate_pages", 2)),
    )

    try:
        if client is None:
            from core.model_pool_compat import get_model_pool

            client = get_model_pool().create_ai_client(task_type="simple_chat", endpoint="qq")
        if not client:
            result["skipped"] = "no_client"
            return result
        from core.ai_client import AIMessage

        response = await asyncio.wait_for(
            client.chat(
                [AIMessage(role="user", content=prompt)],
                tools=[],
                tool_choice="none",
                use_miya_prompt=False,
            ),
            timeout=float(cfg.get("timeout", 30)),
        )
    except asyncio.TimeoutError:
        logger.warning(f"[关系维基] 用户 {user_id} 编译超时，跳过本次更新")
        result["skipped"] = "timeout"
        return result
    except Exception as e:  # noqa: BLE001 — 编译失败宁缺毋滥
        logger.debug(f"[关系维基] 编译调用失败，跳过: {e}")
        result["skipped"] = f"error: {e}"
        return result

    updates = extract_updates(response if isinstance(response, str) else str(response), cfg)
    today = time.strftime("%Y-%m-%d")
    for upd in updates:
        refs = upd["source_refs"] or [today]
        await store.upsert_page(
            user_id=user_id,
            page_id=normalize_page_id(upd["page_id"]),
            title=upd["title"],
            category=upd["category"],
            summary=upd["summary"],
            content_md=upd["content_md"],
            source_refs=refs,
        )
    result["pages_updated"] = len(updates)
    if updates:
        logger.info(
            f"[关系维基] 用户 {user_id} 编译更新 {len(updates)} 页: "
            f"{', '.join(u['title'] for u in updates)}"
        )
    return result


async def handle_wiki_update(payload: Dict[str, Any]) -> Dict[str, Any]:
    """TaskManager handler 入口"""
    return await compile_and_store(payload)


# ==================== 读取：确定性注入 ====================

WIKI_CONTEXT_HEADER = "【关系维基（自己整理的记忆笔记，可能有误；与对话原文冲突时以原文为准，自然化用，不要罗列）】"


async def fetch_wiki_context(
    user_id: Optional[str],
    user_input: str,
    config: Optional[Dict] = None,
    store: Optional[WikiStore] = None,
) -> str:
    """检索并格式化维基页（决策层并行任务调用；隐私：无 user_id 返回空串）"""
    cfg = config or _get_config()
    if not cfg.get("inject_enabled", True):
        return ""
    if not user_id:
        return ""
    try:
        store = store or get_wiki_store()
        pages = await store.list_pages(user_id)
        if not pages:
            return ""
        keywords = extract_keywords_from_text(user_input)
        selected = score_pages(pages, keywords)[: int(cfg.get("inject_max_pages", 2))]
        if not selected:
            return ""

        blocks = []
        for page in selected:
            body = (page.get("content_md") or "").strip()
            blocks.append(f"◆《{page.get('title', '')}》[{page.get('category', '其他')}]\n{body}")
        context = WIKI_CONTEXT_HEADER + "\n" + "\n\n".join(blocks)

        max_chars = int(cfg.get("inject_max_chars", 800))
        if len(context) > max_chars:
            context = context[:max_chars].rsplit("\n", 1)[0] + "\n…"
        return context
    except Exception as e:  # noqa: BLE001 — 维基层为增强功能，失败降级空串
        logger.debug(f"[关系维基] 注入检索失败: {e}")
        return ""


# ==================== TaskManager 接线 ====================

def register_wiki_handler(task_manager: Any) -> None:
    """注册 wiki_update 处理器（幂等：重复注册为覆盖）"""
    task_manager.register_handler("wiki_update", handle_wiki_update)


async def submit_wiki_update(payload: Dict[str, Any], task_manager: Any = None) -> Optional[str]:
    """提交一次维基编译任务（调用方：memory_manager assistant 分支；失败返回 None 不抛出）"""
    try:
        cfg = _get_config()
        if not cfg.get("compile_enabled", True):
            return None
        if not str(payload.get("user_id") or "").strip():
            return None

        from core.task_manager import get_task_manager, start_task_manager

        tm = task_manager or get_task_manager()
        register_wiki_handler(tm)
        await start_task_manager()
        task_id = await tm.add_task(
            task_type="wiki_update",
            payload=payload,
            max_retries=2,
        )
        logger.debug(f"[关系维基] 已提交编译任务: {task_id}")
        return task_id
    except Exception as e:  # noqa: BLE001 — 提交失败不影响主流程
        logger.debug(f"[关系维基] 编译任务提交失败: {e}")
        return None
