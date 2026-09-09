"""web_search 首个成功引擎即返回回归测试（链路修复 Fix 3）。

修复前：search() 聚合所有引擎结果，默认引擎含两个国内不可达的 DDG →
每次搜索白等 20s+；且 decision_hub 对同步 search() 使用 await 导致结果从未注入。
修复后：首个返回非空结果的引擎即停止，默认引擎只保留国内可达的 baidu/bing_cn（tavily 有 key 时最前）。
"""

from webnet.ToolNet.tools.network.web_search import EnhancedWebSearch


class TestFirstSuccessWins:
    def test_empty_result_continues_to_next_engine(self, monkeypatch):
        """引擎返回空结果视为失败，继续尝试下一个。"""
        searcher = EnhancedWebSearch()
        calls = []

        def fake_engine(query, engine, num_results):
            calls.append(engine)
            if engine == "tavily":
                return []
            return [{"title": "t", "url": "http://x/1", "snippet": "s", "source": engine}]

        monkeypatch.setattr(searcher, "_search_engine", fake_engine)
        results = searcher.search("q", engines=["tavily", "baidu"])

        assert calls == ["tavily", "baidu"]
        assert len(results) == 1
        assert results[0]["source"] == "baidu"

    def test_first_nonempty_stops_iteration(self, monkeypatch):
        """首个成功引擎即返回，不再请求后续引擎。"""
        searcher = EnhancedWebSearch()
        calls = []

        def fake_engine(query, engine, num_results):
            calls.append(engine)
            return [{"title": "a", "url": "http://a/1", "snippet": "", "source": engine}]

        monkeypatch.setattr(searcher, "_search_engine", fake_engine)
        results = searcher.search("q", engines=["tavily", "baidu", "bing_cn"])

        assert calls == ["tavily"]
        assert results[0]["source"] == "tavily"

    def test_exception_continues_to_next_engine(self, monkeypatch):
        """引擎抛异常不中断，继续下一个。"""
        searcher = EnhancedWebSearch()

        def fake_engine(query, engine, num_results):
            if engine == "baidu":
                raise RuntimeError("boom")
            return [{"title": "b", "url": "http://b/1", "snippet": "", "source": engine}]

        monkeypatch.setattr(searcher, "_search_engine", fake_engine)
        results = searcher.search("q", engines=["baidu", "bing_cn"])
        assert len(results) == 1
        assert results[0]["source"] == "bing_cn"

    def test_all_engines_fail_returns_empty(self, monkeypatch):
        searcher = EnhancedWebSearch()
        monkeypatch.setattr(searcher, "_search_engine", lambda q, e, n: [])
        assert searcher.search("q", engines=["baidu", "bing_cn"]) == []


class TestDefaultEngines:
    def test_default_engines_exclude_unreachable_ddg(self):
        """默认免费引擎不含国内不可达的 DDG（此前每次搜索白等 20s）。"""
        searcher = EnhancedWebSearch()
        assert "duckduckgo_html" not in searcher._free_engines
        assert "duckduckgo_api" not in searcher._free_engines
        # 只允许国内可达引擎（tavily 有 key 时在最前）
        assert set(searcher._free_engines) <= {"tavily", "baidu", "bing_cn"}

    def test_explicit_engines_still_respected(self, monkeypatch):
        """调用方显式传入 engines 顺序时按传入顺序尝试。"""
        searcher = EnhancedWebSearch()
        calls = []

        def fake_engine(query, engine, num_results):
            calls.append(engine)
            return [{"title": "a", "url": "http://a/1", "snippet": "", "source": engine}]

        monkeypatch.setattr(searcher, "_search_engine", fake_engine)
        searcher.search("q", engines=["bing_cn", "tavily"])
        assert calls == ["bing_cn"]
