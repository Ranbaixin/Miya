"""
统一攻击引擎 — 决策 + 错误恢复 + 工具编排

集成 IntelligentDecisionEngine(目标分析/工具选择/攻击链生成)
+ IntelligentErrorHandler(错误分类/恢复策略/优雅降级)
提供一键式的安全自动化入口。
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from .hextrike.decision_engine import (
    IntelligentDecisionEngine,
    TargetType,
    AttackChain,
    AttackStep,
)
from .hextrike.error_handler import (
    IntelligentErrorHandler,
    GracefulDegradation,
    ErrorType,
    RecoveryAction,
)

logger = logging.getLogger(__name__)

_engine: Optional["MiyaEngine"] = None


class MiyaEngine:
    """弥娅统一攻击引擎"""

    def __init__(self):
        self.decision = IntelligentDecisionEngine()
        self.error_handler = IntelligentErrorHandler()
        self.degrader = GracefulDegradation()
        self._stats = {"tasks": 0, "successes": 0, "failures": 0, "recoveries": 0}
        self._tools: Dict[str, callable] = {}

    def register_tool(self, name: str, executor: callable):
        self._tools[name] = executor

    async def analyze_target(self, target: str) -> Dict[str, Any]:
        """分析目标：自动识别类型/技术栈/攻击面

        Returns:
            target_type, description, recommended_tools, risk_score
        """
        profile = self.decision.create_target_profile(target)
        return {
            "target": target,
            "type": profile.target_type.value if profile and hasattr(profile, "target_type") else "unknown",
            "description": profile.description if profile and hasattr(profile, "description") else "",
            "risk_score": getattr(profile, "risk_score", 0),
            "technology": getattr(profile, "technology", "unknown"),
        }

    async def generate_attack_chain(self, target: str, mode: str = "auto") -> Optional[AttackChain]:
        """为目标生成攻击链"""
        try:
            profile = self.decision.create_target_profile(target)
            chain = self.decision.generate_attack_chain(profile, mode=mode)
            if chain:
                logger.info(f"攻击链生成: {len(chain.steps)} 步, 成功率 {chain.success_rate:.0%}")
            return chain
        except Exception as e:
            logger.error(f"攻击链生成失败: {e}")
            return None

    async def execute_chain(self, chain: AttackChain, progress_cb: Optional[callable] = None) -> Dict[str, Any]:
        """执行攻击链，含自动错误恢复"""
        results = []
        current_step = 0

        for step in chain.steps:
            current_step += 1
            if progress_cb:
                progress_cb(current_step, len(chain.steps), step.name)

            attempt = 0
            max_retries = 3
            success = False
            step_result = None

            while attempt < max_retries and not success:
                attempt += 1
                try:
                    step_result = await self._execute_attack_step(step)
                    success = True
                    self._stats["successes"] += 1
                except Exception as e:
                    error_type = self.error_handler.classify_error(e)
                    logger.warning(f"步骤 {current_step} 失败 ({error_type.value}): {e}")

                    # 自动恢复
                    recovery = self.error_handler.get_recovery_action(error_type, step.name)
                    if recovery == RecoveryAction.RETRY_DELAY:
                        await asyncio.sleep(min(2**attempt, 30))
                    elif recovery == RecoveryAction.SWITCH_TOOL:
                        fallback = self.degrader.get_fallback_tool(step.tool_name)
                        if fallback:
                            step.tool_name = fallback
                            logger.info(f"降级到替代工具: {fallback}")
                        else:
                            break
                    elif recovery == RecoveryAction.ABORT:
                        break

                    self._stats["recoveries"] += 1

            if not success:
                self._stats["failures"] += 1

            results.append(
                {
                    "step": step.name,
                    "tool": step.tool_name,
                    "success": success,
                    "result": str(step_result)[:2000] if step_result else None,
                    "attempts": attempt,
                }
            )

        self._stats["tasks"] += 1
        return {"target": chain.target, "steps": len(chain.steps), "results": results, "stats": self._stats}

    async def _execute_attack_step(self, step: AttackStep) -> Any:
        executor = self._tools.get(step.tool_name)
        if not executor:
            logger.warning(f"工具未注册: {step.tool_name}")
            return None
        if asyncio.iscoroutinefunction(executor):
            return await executor(step.parameters)
        return executor(step.parameters)

    def quick_scan(self, target: str) -> List[str]:
        """快速推荐扫描策略"""
        profile = self.decision.create_target_profile(target)
        recommendations = []

        if profile and hasattr(profile, "target_type"):
            ttype = profile.target_type
            if ttype == TargetType.WEB_APPLICATION:
                recommendations = ["端口扫描", "HTTP头分析", "目录爆破", "CVE查询", "子域名枚举"]
            elif ttype == TargetType.NETWORK_HOST:
                recommendations = ["Nmap深度扫描", "端口服务识别", "OS指纹", "漏洞数据库匹配"]
            elif ttype == TargetType.API_ENDPOINT:
                recommendations = ["HTTP方法枚举", "JWT分析", "参数Fuzzing", "CORS检测"]
            else:
                recommendations = ["基础侦察", "CVE查询", "在线资产搜索"]

        return recommendations

    def get_stats(self) -> Dict[str, int]:
        return self._stats


def get_engine() -> MiyaEngine:
    global _engine
    if _engine is None:
        _engine = MiyaEngine()
    return _engine
