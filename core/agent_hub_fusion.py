"""
AstrBot Agent 与 Miya Hub 融合模块

将AstrBot的Agent执行能力深度集成到Miya的DecisionHub中
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field

from core.agent_astrbot.runner import AgentRunner, AgentContext, AgentConfig
from core.agent_astrbot.config import AgentConfig as MiyaAgentConfig
from hub.decision_hub import DecisionHub

logger = logging.getLogger(__name__)


@dataclass
class HubAgentConfig:
    """Hub Agent 融合配置"""

    use_astrbot_agent: bool = True
    fallback_to_hub: bool = True
    agent_timeout: int = 120
    max_retries: int = 3
    enable_streaming: bool = True


class AgentHubFusion:
    """
    Agent 与 Hub 融合器

    功能：
    - 统一入口：DecisionHub 和 AgentRunner 的统一调用
    - 智能路由：根据任务类型选择合适的执行器
    - 结果标准化：统一输出格式
    - 错误处理：自动降级和重试
    """

    def __init__(
        self,
        decision_hub: Optional[DecisionHub] = None,
        agent_runner: Optional[AgentRunner] = None,
        config: Optional[HubAgentConfig] = None,
    ):
        self.decision_hub = decision_hub
        self.agent_runner = agent_runner
        self.config = config or HubAgentConfig()
        self._initialized = False

    async def initialize(
        self, provider=None, tool_registry=None, personality=None, memory=None
    ):
        """初始化融合器"""
        logger.info("[AgentHubFusion] 初始化...")

        if self.config.use_astrbot_agent and not self.agent_runner:
            from core.agent_astrbot.runner import AgentRunner

            miya_config = MiyaAgentConfig(
                tool_call_timeout=self.config.agent_timeout,
                streaming_response=self.config.enable_streaming,
            )
            self.agent_runner = AgentRunner(miya_config)
            await self.agent_runner.initialize(provider, tool_registry)
            logger.info("[AgentHubFusion] AgentRunner 已初始化")

        self._initialized = True
        logger.info("[AgentHubFusion] 初始化完成")

    async def process(
        self, user_input: str, context_data: Dict[str, Any], session_id: str = ""
    ) -> Dict[str, Any]:
        """
        统一处理入口

        智能选择：
        - 需要Agent能力 → 使用AstrBot Agent
        - 简单对话 → 使用DecisionHub
        - 工具调用 → 路由到对应系统
        """
        if not self._initialized:
            return {"success": False, "error": "AgentHubFusion未初始化"}

        task_type = self._analyze_task_type(user_input, context_data)

        if task_type == "agent_task":
            return await self._execute_agent(user_input, context_data, session_id)
        elif task_type == "tool_task":
            return await self._execute_tool(user_input, context_data)
        else:
            return await self._execute_hub(user_input, context_data)

    def _analyze_task_type(self, user_input: str, context_data: Dict[str, Any]) -> str:
        """分析任务类型"""
        input_lower = user_input.lower()

        agent_indicators = [
            "分析",
            "执行",
            "操作",
            "创建",
            "生成",
            "search",
            "execute",
            "run",
            "create",
        ]

        tool_indicators = [
            "天气",
            "时间",
            "搜索",
            "计算",
            "weather",
            "time",
            "search",
            "calc",
        ]

        for indicator in agent_indicators:
            if indicator in input_lower:
                return "agent_task"

        for indicator in tool_indicators:
            if indicator in input_lower:
                return "tool_task"

        return "conversation"

    async def _execute_agent(
        self, user_input: str, context_data: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """使用AstrBot Agent执行"""
        try:
            if not self.agent_runner:
                return await self._execute_hub(user_input, context_data)

            context = AgentContext(
                session_id=session_id,
                user_id=context_data.get("user_id", ""),
                platform=context_data.get("platform", ""),
                provider_id=context_data.get("provider_id"),
                persona=context_data.get("persona"),
                history=context_data.get("history", []),
            )

            result = await self.agent_runner.execute(
                context=context,
                user_input=user_input,
                stream=self.config.enable_streaming,
            )

            return {"success": True, "result": result, "source": "astrbot_agent"}

        except Exception as e:
            logger.error(f"[AgentHubFusion] Agent执行失败: {e}")
            if self.config.fallback_to_hub:
                return await self._execute_hub(user_input, context_data)
            return {"success": False, "error": str(e)}

    async def _execute_tool(
        self, user_input: str, context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用工具系统执行"""
        try:
            if self.decision_hub and hasattr(self.decision_hub, "tool_subnet"):
                tool_subnet = self.decision_hub.tool_subnet
                result = await tool_subnet.execute(user_input, context_data)
                return {"success": True, "result": result, "source": "tool_subnet"}

            return await self._execute_hub(user_input, context_data)

        except Exception as e:
            logger.error(f"[AgentHubFusion] 工具执行失败: {e}")
            return {"success": False, "error": str(e)}

    async def _execute_hub(
        self, user_input: str, context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用DecisionHub执行"""
        try:
            if self.decision_hub:
                from mlink.message import Message, MessageType

                msg = Message(
                    msg_type=MessageType.TEXT,
                    content=user_input,
                    sender=context_data.get("user_id", "unknown"),
                )

                result = await self.decision_hub.process_message(msg)
                return {"success": True, "result": result, "source": "decision_hub"}

            return {"success": False, "error": "无可用执行器"}

        except Exception as e:
            logger.error(f"[AgentHubFusion] Hub执行失败: {e}")
            return {"success": False, "error": str(e)}

    async def get_capabilities(self) -> Dict[str, Any]:
        """获取当前融合器的能力"""
        return {
            "astrbot_agent": self.agent_runner is not None,
            "decision_hub": self.decision_hub is not None,
            "streaming": self.config.enable_streaming,
            "fallback": self.config.fallback_to_hub,
        }

    def switch_executor(self, executor: str):
        """切换执行器"""
        if executor == "agent":
            self.config.use_astrbot_agent = True
        elif executor == "hub":
            self.config.use_astrbot_agent = False
        logger.info(f"[AgentHubFusion] 切换执行器: {executor}")


_agent_hub_fusion: Optional[AgentHubFusion] = None


def get_agent_hub_fusion() -> AgentHubFusion:
    """获取全局AgentHubFusion实例"""
    global _agent_hub_fusion
    if _agent_hub_fusion is None:
        _agent_hub_fusion = AgentHubFusion()
    return _agent_hub_fusion
