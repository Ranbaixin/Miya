"""请求级轮次上下文（contextvar）。

DM 私聊连续输入合并（core/unified_platform_impl/dm_merger.py）在生成期间
设置当前轮次凭证与草稿上下文；工具执行层（webnet/ToolNet/registry.py）读取
它们判断本轮是否已被新输入替代、以及是否可复用本批次内已执行的工具结果。
独立轻量模块：避免 ai_client / webnet 反向依赖平台实现层
（先例：core/ai_client.py 的 _tool_context_var）。
"""
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


class TurnHandleProtocol(Protocol):
    def is_superseded(self) -> bool:
        ...


turn_handle_var: ContextVar[Optional[TurnHandleProtocol]] = ContextVar(
    "miya_turn_handle", default=None
)


def current_turn_handle() -> Optional[TurnHandleProtocol]:
    """当前协程关联的 DM 合并轮次凭证；非合并路径返回 None。"""
    return turn_handle_var.get()


@dataclass
class ToolExecutionRecord:
    """一次工具执行的记录（草稿观测与同批次复用）。"""

    tool_name: str
    args_normalized: str  # json.dumps(args, sort_keys=True) 规范化
    status: str  # ok | error | unknown（unknown=执行状态不明，不得自动重做）
    result: str = ""


def normalize_tool_args(args: Any) -> str:
    """工具参数规范化：同批次内相同工具+相同参数的匹配键。"""
    import json

    try:
        return json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001 — 规范化失败退化为 repr，仅影响复用命中
        return repr(args)


@dataclass
class DraftContext:
    """请求级草稿上下文（DM 合并被替代轮次的数据）。

    - draft_reply：最近一次未发送回答，下一轮注入提示词时明确标记为
      「未发送参考、新输入可修正」；不携带模型内部推理过程。
    - tool_records：本批次（自首条输入至最终发送）累计的工具执行记录，
      供同批次内相同工具+相同参数的修改操作复用结果；批次结束即清理。
    每次生成使用新的上下文副本，禁止在上一轮上下文上叠加。"""

    draft_reply: Optional[str] = None
    tool_records: List[ToolExecutionRecord] = field(default_factory=list)

    def find_reusable(self, tool_name: str, args: Any) -> Optional[ToolExecutionRecord]:
        """仅修改类（status=ok/error）结果可复用；unknown 不得自动重做也不复用。"""
        key = normalize_tool_args(args)
        for rec in self.tool_records:
            if rec.tool_name == tool_name and rec.args_normalized == key and rec.status in ("ok", "error"):
                return rec
        return None

    def add_record(self, tool_name: str, args: Any, status: str, result: str) -> None:
        self.tool_records.append(
            ToolExecutionRecord(
                tool_name=tool_name,
                args_normalized=normalize_tool_args(args),
                status=status,
                result=result,
            )
        )

    def snapshot_for_prompt(self) -> Optional[str]:
        """生成提示词用的草稿说明文本；无内容时返回 None。"""
        parts: List[str] = []
        if self.draft_reply:
            parts.append(
                "【未发送草稿】你在上一轮曾准备以下回答，但用户随即补充了新输入，"
                "该回答未发送，仅供参考；请以用户新输入为准修正后统一回应：\n" + self.draft_reply
            )
        if self.tool_records:
            lines = []
            for rec in self.tool_records:
                if rec.status == "unknown":
                    lines.append(f"- {rec.tool_name}：执行状态不确定，请勿再次自动执行，回复中需提示用户核实")
                else:
                    state = "已执行成功" if rec.status == "ok" else "已执行但报错"
                    lines.append(f"- {rec.tool_name}（{state}）结果：{rec.result[:200]}")
            parts.append(
                "【本批次已执行的工具】以下操作已经发生、不会因重新回答而撤销：\n" + "\n".join(lines)
            )
        if not parts:
            return None
        return "\n\n".join(parts)


draft_context_var: ContextVar[Optional[DraftContext]] = ContextVar(
    "miya_draft_context", default=None
)


def current_draft_context() -> Optional[DraftContext]:
    """当前协程关联的草稿上下文；非合并路径返回 None。"""
    return draft_context_var.get()
