"""请求级轮次上下文（contextvar）。

DM 私聊连续输入合并（core/unified_platform_impl/dm_merger.py）在生成期间
设置当前轮次凭证，工具执行层（webnet/ToolNet/registry.py）读取它判断本轮
是否已被新输入替代。独立轻量模块：避免 ai_client / webnet 反向依赖平台实现层
（先例：core/ai_client.py 的 _tool_context_var）。
"""
from contextvars import ContextVar
from typing import Optional, Protocol


class TurnHandleProtocol(Protocol):
    def is_superseded(self) -> bool:
        ...


turn_handle_var: ContextVar[Optional[TurnHandleProtocol]] = ContextVar(
    "miya_turn_handle", default=None
)


def current_turn_handle() -> Optional[TurnHandleProtocol]:
    """当前协程关联的 DM 合并轮次凭证；非合并路径返回 None。"""
    return turn_handle_var.get()
