"""工具暂停闸门测试：已替代轮次中，非只读工具必须被跳过（返回说明文本，
不执行）；只读工具与无轮次上下文的路径不受影响。"""
import types

from webnet.ToolNet.registry import BaseTool, ToolRegistry


class _Handle:
    def __init__(self, superseded: bool):
        self._superseded = superseded
        self.executed_tools = []

    def is_superseded(self) -> bool:
        return self._superseded


class _Tool:
    read_only = False

    def __init__(self, name: str, read_only: bool = False):
        self.name = name
        self.read_only = read_only
        self.executed = 0

    async def execute(self, args, context):  # noqa: ARG002
        self.executed += 1
        return "ok"


def _reg() -> ToolRegistry:
    """只测纯逻辑，不经构造器（构造器会装配全部工具加载器）。"""
    return ToolRegistry.__new__(ToolRegistry)


def test_basetool_default_not_read_only():
    assert getattr(BaseTool, "read_only", None) is False


def test_gate_blocks_mutating_tool_when_superseded():
    reg = _reg()
    handle = _Handle(superseded=True)
    tool = _Tool("qq_send_message", read_only=False)
    assert ToolRegistry._turn_gate_blocks(reg, tool, handle) is True
    assert tool.executed == 0


def test_gate_allows_readonly_tool_when_superseded():
    reg = _reg()
    tool = _Tool("memory_search", read_only=True)
    assert ToolRegistry._turn_gate_blocks(reg, tool, _Handle(superseded=True)) is False


def test_gate_inactive_without_supersession():
    reg = _reg()
    tool = _Tool("reminder_create", read_only=False)
    assert ToolRegistry._turn_gate_blocks(reg, tool, _Handle(superseded=False)) is False
    assert ToolRegistry._turn_gate_blocks(reg, tool, None) is False


def test_executed_tools_recorded_via_handle():
    """执行成功的工具名追加到 handle.executed_tools（草稿观测）。"""
    handle = _Handle(superseded=False)
    ToolRegistry._record_executed_tool(handle, "pc_context")
    assert handle.executed_tools == ["pc_context"]
    ToolRegistry._record_executed_tool(None, "pc_context")  # 无 handle 时空操作


def test_readonly_class_allowlist():
    """类名白名单生效（无 read_only 属性的纯类）。"""
    reg = _reg()

    class MemoryQueryTool:  # 类名命中白名单
        pass

    class SendMessageTool:  # 不在白名单、无属性 → 非只读
        pass

    assert ToolRegistry._is_read_only(reg, MemoryQueryTool()) is True
    assert ToolRegistry._is_read_only(reg, SendMessageTool()) is False


def test_readonly_mcp_caps():
    """MCP 只读能力集合：类名为 MCPTool 且 service.cap 命中集合。"""
    reg = _reg()

    class MCPTool:
        def __init__(self, service: str, cap: str):
            self._service_name = service
            self._tool_name = cap

    query = ToolRegistry._is_read_only(reg, MCPTool("pc_tracker", "pc_context"))
    send = ToolRegistry._is_read_only(reg, MCPTool("pc_tracker", "pc_unknown"))
    assert query is True
    assert send is False
    assert ToolRegistry._turn_gate_blocks(reg, MCPTool("pc_tracker", "pc_context"), _Handle(True)) is False
    assert ToolRegistry._turn_gate_blocks(reg, MCPTool("pc_tracker", "pc_unknown"), _Handle(True)) is True


# ---------- 同批次工具结果复用（2026-09-29） ----------


class _PermRegistry(ToolRegistry):
    """注入固定权限通过 + 可控执行的测试注册表。"""

    def __init__(self, tool):
        import logging

        self._test_tool = tool
        self.logger = logging.getLogger("test.toolgate")

    def get_tool(self, name):
        return self._test_tool

    async def _check_tool_permission(self, tool_name, context):
        return {"allowed": True, "required_permission": ""}


class _ExecTool:
    read_only = False

    name = "reminder_create"

    async def execute(self, args, context):
        self.executed += 1
        return f"结果#{self.executed}"

    def __init__(self):
        self.executed = 0


async def _run_with_draft(tool, draft, args):
    from core.turn_context import draft_context_var

    reg = _PermRegistry(tool)
    token = draft_context_var.set(draft)
    try:
        return await reg.execute_tool("reminder_create", {}, **args)
    finally:
        draft_context_var.reset(token)


async def test_same_batch_reuse_avoids_duplicate_execution():
    """同批次相同工具+相同参数：第二次调用复用结果，不重复执行。"""
    from core.turn_context import DraftContext

    tool = _ExecTool()
    draft = DraftContext()
    await _run_with_draft(tool, draft, {"task": "买牛奶"})
    out2 = await _run_with_draft(tool, draft, {"task": "买牛奶"})
    assert tool.executed == 1, "修改操作不得重复执行"
    assert "复用" in out2 and "结果#1" in out2


async def test_different_args_execute_again():
    from core.turn_context import DraftContext

    tool = _ExecTool()
    draft = DraftContext()
    await _run_with_draft(tool, draft, {"task": "A"})
    await _run_with_draft(tool, draft, {"task": "B"})
    assert tool.executed == 2, "参数不同不复用"


async def test_unknown_status_never_reused():
    """执行状态不明的记录不得复用（不得自动重做也不得冒充成功）。"""
    from core.turn_context import DraftContext

    tool = _ExecTool()
    draft = DraftContext()
    draft.add_record("reminder_create", {"task": "X"}, "unknown", "")
    out = await _run_with_draft(tool, draft, {"task": "X"})
    assert tool.executed == 1, "unknown 记录不阻塞真实执行判断（走闸门后正常路径）"
    assert "复用" not in out


async def test_readonly_tools_not_reused():
    """只读工具不复用（查询类允许重跑获取最新值）。"""
    from core.turn_context import DraftContext

    tool = _ExecTool()
    tool.read_only = True
    tool.name = "memory_search"
    draft = DraftContext()
    await _run_with_draft(tool, draft, {"q": "x"})
    await _run_with_draft(tool, draft, {"q": "x"})
    assert tool.executed == 2
