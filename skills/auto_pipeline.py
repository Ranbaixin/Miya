"""自动处理管线 (AutoPipeline)

借鉴 Undefined 的 auto_pipeline 设计：
- 可热重载的并行检测/处理管线
- 斜杠命令优先、自动管线并行
- 结果写入消息历史
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class AutoPipelineRule:
    """自动处理规则"""

    name: str
    detect: Callable[[str], bool]  # 检测函数：输入消息文本，返回是否匹配
    process: Callable[[str], Any]  # 处理函数：输入消息文本，返回处理结果
    priority: int = 0  # 越小越优先
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class AutoPipelineRegistry:
    """自动处理管线注册表

    核心设计：
        1. 消息到达 → 优先匹配命令
        2. 无命令匹配时 → 并行运行所有启用的 AutoPipeline 规则
        3. 各规则独立检测和处理，结果写入消息历史
        4. 支持热重载

    用法:
        registry = AutoPipelineRegistry()
        registry.register(AutoPipelineRule(
            name="bilibili",
            detect=lambda msg: "b23.tv" in msg or "BV" in msg,
            process=handle_bilibili,
        ))
        await registry.process_message("看看这个 BV12345", context={})
    """

    def __init__(self):
        self._rules: dict[str, AutoPipelineRule] = {}
        self._lock = asyncio.Lock()

    def register(self, rule: AutoPipelineRule) -> None:
        """注册规则"""
        self._rules[rule.name] = rule
        logger.debug("[AutoPipeline] 注册规则: %s", rule.name)

    def unregister(self, name: str) -> None:
        """注销规则"""
        self._rules.pop(name, None)
        logger.debug("[AutoPipeline] 注销规则: %s", name)

    def get_rule(self, name: str) -> AutoPipelineRule | None:
        return self._rules.get(name)

    def set_enabled(self, name: str, enabled: bool) -> None:
        rule = self._rules.get(name)
        if rule:
            rule.enabled = enabled

    async def process_message(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> list[tuple[str, Any]]:
        """处理消息：并行运行所有匹配的规则

        Returns:
            [(rule_name, result), ...] 按优先级排序
        """
        ctx = context or {}
        matched: list[tuple[int, AutoPipelineRule]] = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue
            try:
                if rule.detect(message):
                    matched.append((rule.priority, rule))
            except Exception as e:
                logger.debug("[AutoPipeline] 规则 %s 检测异常: %s", rule.name, e)

        if not matched:
            return []

        matched.sort(key=lambda x: x[0])

        coros = []
        for _, rule in matched:

            async def _process(r: AutoPipelineRule, msg: str):
                try:
                    result = r.process(msg)
                    if asyncio.iscoroutine(result):
                        result = await result
                    return r.name, result
                except Exception as e:
                    logger.warning("[AutoPipeline] 规则 %s 处理失败: %s", r.name, e)
                    return r.name, None

            coros.append(_process(rule, message))

        results = await asyncio.gather(*coros)
        return [(name, res) for name, res in results if res is not None]

    def list_rules(self) -> list[dict[str, Any]]:
        """列出所有规则"""
        return [
            {
                "name": r.name,
                "priority": r.priority,
                "enabled": r.enabled,
            }
            for r in sorted(self._rules.values(), key=lambda x: x.priority)
        ]


# ============================================================================
# 内置规则示例
# ============================================================================


def build_default_rules() -> list[AutoPipelineRule]:
    """构建默认的自动处理管线规则"""
    rules: list[AutoPipelineRule] = []

    # Bilibili 视频检测
    def _detect_bilibili(msg: str) -> bool:
        import re

        return bool(
            re.search(r"b23\.tv/\w+", msg)
            or re.search(r"BV[1-9A-HJ-NP-Za-km-z]{10}", msg)
        )

    def _handle_bilibili(msg: str) -> dict:
        return {"type": "bilibili", "message": "检测到B站视频链接"}

    rules.append(
        AutoPipelineRule(
            name="bilibili",
            detect=_detect_bilibili,
            process=_handle_bilibili,
            priority=10,
        )
    )

    # GitHub 仓库检测
    def _detect_github(msg: str) -> bool:
        import re

        return bool(re.search(r"github\.com/[\w.-]+/[\w.-]+", msg))

    def _handle_github(msg: str) -> dict:
        return {"type": "github", "message": "检测到GitHub仓库链接"}

    rules.append(
        AutoPipelineRule(
            name="github",
            detect=_detect_github,
            process=_handle_github,
            priority=20,
        )
    )

    # arXiv 论文检测
    def _detect_arxiv(msg: str) -> bool:
        import re

        return bool(
            re.search(r"arxiv\.org/(abs|pdf)/\d+", msg)
            or re.search(r"arXiv:\d+\.\d+", msg)
        )

    def _handle_arxiv(msg: str) -> dict:
        return {"type": "arxiv", "message": "检测到arXiv论文链接"}

    rules.append(
        AutoPipelineRule(
            name="arxiv",
            detect=_detect_arxiv,
            process=_handle_arxiv,
            priority=30,
        )
    )

    return rules
