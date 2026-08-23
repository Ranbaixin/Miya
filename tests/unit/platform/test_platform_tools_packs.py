"""平台工具包路由测试（2026-08 修订计划 Step 2/3）。

覆盖：
- classify_packs：0-2 扩展包、场景命中、上限封顶
- 描述瘦身：保留触发/禁止/参数语义，去掉示例段
- 参数描述瘦身：保留主规则与补充规则，去掉示例
- 策展描述覆盖（QQ 集人工压缩版）
- select_tools_for_message：qq_core 恒在、扩展包追加、非 QQ 平台维持全集
- 降级：任何失败回退 qq_core/空集，绝不回退全量 68
- S1 验收：qq_core 序列化（紧凑 JSON）保守估算 <= 2000 tokens
"""

import json

import pytest

from hub.platform_tools import (
    MAX_EXTRA_PACKS,
    QQ_CORE_PACK,
    QQ_DESC_OVERRIDES,
    TOOL_PACKS,
    PlatformToolsManager,
    classify_packs,
    trim_property_description,
    trim_tool_description,
    trim_tool_schemas,
)
from utils.token_budget import conservative_estimate


def _fake_schema(name, desc, props=None, required=None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": props or {},
                "required": required or [],
            },
        },
    }


class _FakeSubnet:
    """最小 fake：按名字生成 schema，可注入异常"""

    def __init__(self, names, raise_on_get=False):
        self.names = names
        self.raise_on_get = raise_on_get

    def get_tools_schema(self):
        if self.raise_on_get:
            raise RuntimeError("registry boom")
        return [_fake_schema(n, f"描述 {n}", {"a": {"type": "string", "description": "参数a"}}, ["a"]) for n in self.names]


# ==================== 分类 ====================

def test_classify_packs_greeting_returns_none():
    assert classify_packs("你好呀") == []


def test_classify_packs_scenario_hits():
    assert classify_packs("帮我搜一下今天的热搜") == ["search"]
    assert classify_packs("今天天气怎么样") == ["qq_social"]
    assert classify_packs("看看群里文件") == ["media"]
    assert classify_packs("给我抽个签") == ["entertainment"]
    assert classify_packs("掷个骰子") == ["game"]
    assert classify_packs("分析一下这张图片") == ["media"]


def test_classify_packs_caps_at_max_extra():
    # 命中 3 个包时只取 2 个（命中数降序）
    packs = classify_packs("搜一下新闻 顺便看看天气 分析图片", max_extra=MAX_EXTRA_PACKS)
    assert len(packs) <= MAX_EXTRA_PACKS
    assert len(packs) == 2


def test_classify_packs_empty_input():
    assert classify_packs("") == []
    assert classify_packs(None) == []


def test_pack_memberships_are_valid():
    """每个扩展包工具名都在 QQ 平台可用集内（核心+扩展）"""
    available = set(PlatformToolsManager.CORE_TOOLS) | set(PlatformToolsManager.QQ_EXTENDED_TOOLS)
    for pack, names in TOOL_PACKS.items():
        for n in names:
            assert n in available, f"{pack}.{n} 不在 QQ 平台可用集"


# ==================== 描述瘦身 ====================

def test_trim_tool_description_keeps_trigger_drops_examples():
    desc = (
        "Tavily AI 搜索引擎。\n\n当用户询问实时信息、新闻、事实查询或你不知道答案时使用此工具。"
        "\n\n适用场景:\n- 实时新闻/事件查询\n- 事实核查\n\n示例:\n- 搜索: 今天有什么AI新闻"
    )
    trimmed = trim_tool_description(desc)
    assert "当用户询问" in trimmed  # 触发时机保留
    assert "适用场景" not in trimmed  # 场景段删除
    assert "示例" not in trimmed  # 示例删除
    assert len(trimmed) <= 120


def test_trim_tool_description_keeps_forbidden():
    desc = "列出记忆。当用户问过去的事时调用。AI需要理解后用自己的话回答，不要直接复制工具输出。"
    trimmed = trim_tool_description(desc)
    assert "不要直接复制" in trimmed


def test_trim_tool_description_empty():
    assert trim_tool_description("") == ""
    assert trim_tool_description(None) == ""


def test_trim_property_description_cuts_example():
    desc = "群号。如果用户没有明确指定，则使用当前对话群号（即消息所在群）。例如当前群号是1092980378，就填1092980378"
    trimmed = trim_property_description(desc)
    assert "例如" not in trimmed
    assert "当前对话群号" in trimmed  # 补充规则保留
    assert len(trimmed) <= 80


def test_trim_tool_schemas_preserves_structure():
    schemas = [
        _fake_schema(
            "web_search",
            "网络搜索工具。当用户需要搜索信息时使用。\n\n示例:\n- 搜索: 今天有什么AI新闻",
            {
                "query": {"type": "string", "description": "搜索查询内容"},
                "max_results": {"type": "integer", "description": "返回结果数 (默认5)", "default": 5},
            },
            ["query"],
        )
    ]
    trimmed = trim_tool_schemas(schemas)
    assert trimmed[0]["type"] == "function"
    f = trimmed[0]["function"]
    assert f["name"] == "web_search"
    assert "示例" not in f["description"]
    assert f["parameters"]["properties"]["query"]["description"] == "搜索查询内容"
    assert f["parameters"]["properties"]["max_results"]["default"] == 5  # 默认值保留
    assert f["parameters"]["required"] == ["query"]  # 必填保留


# ==================== 策展覆盖 ====================

def test_curated_descriptions_are_short():
    for name, desc in QQ_DESC_OVERRIDES.items():
        assert len(desc) <= 90, f"{name} 策展描述过长: {len(desc)}"


def test_curated_descriptions_keep_semantics():
    """策展描述仍含触发时机（当/必须）"""
    for name, desc in QQ_DESC_OVERRIDES.items():
        assert any(k in desc for k in ("当", "必须", "需要")), f"{name} 缺少触发时机"


# ==================== 选包 ====================

def test_select_qq_core_always_included():
    mgr = PlatformToolsManager(_FakeSubnet(QQ_CORE_PACK))
    tools = mgr.select_tools_for_message("aiocqhttp", "你好呀")
    names = [t["function"]["name"] for t in tools]
    for core in QQ_CORE_PACK:
        assert core in names


def test_select_extension_pack_appended():
    mgr = PlatformToolsManager(_FakeSubnet(QQ_CORE_PACK + TOOL_PACKS["media"]))
    tools = mgr.select_tools_for_message("aiocqhttp", "看看群里文件")
    names = [t["function"]["name"] for t in tools]
    assert "qq_file_reader" in names
    assert "send_message" in names  # qq_core 仍在


def test_select_non_qq_returns_platform_set():
    names = ["send_message", "get_user_info", "memory_add", "memory_list", "web_search"]
    mgr = PlatformToolsManager(_FakeSubnet(names))
    tools = mgr.select_tools_for_message("lark", "随便")
    got = [t["function"]["name"] for t in tools]
    assert got == names  # 非 QQ 平台不裁剪不改选


def test_select_fallback_never_returns_all_tools(monkeypatch):
    """注册表异常时：QQ 平台回退 qq_core/空集，绝不回退全量"""
    mgr = PlatformToolsManager(_FakeSubnet([], raise_on_get=True))
    tools = mgr.select_tools_for_message("aiocqhttp", "你好")
    assert len(tools) == 0  # 双重保险后为空（不回退全量）


def test_get_platform_specific_tools_fallback_never_all(monkeypatch):
    """get_platform_specific_tools 的 except 分支同样不回退全量"""
    mgr = PlatformToolsManager(_FakeSubnet([], raise_on_get=True))
    tools = mgr.get_platform_specific_tools("aiocqhttp")
    assert tools == []


# ==================== S1 验收：qq_core 预算 ====================

@pytest.mark.integration
def test_qq_core_token_budget_s1():
    """S1：QQ core 序列化（紧凑 JSON）保守估算 <= 2000 tokens"""
    from webnet.ToolNet.subnet import ToolSubnet

    sub = ToolSubnet()
    mgr = PlatformToolsManager(sub)
    core = mgr.get_qq_core_schemas()
    assert len(core) == len(QQ_CORE_PACK)
    serialized = json.dumps(core, ensure_ascii=False, separators=(",", ":"))
    tokens = conservative_estimate(serialized)
    assert tokens <= 2000, f"qq_core 预算超标: {tokens} > 2000"
