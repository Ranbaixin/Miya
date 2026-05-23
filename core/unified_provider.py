"""
Provider 统一管理模块

桥接 Miya 模型池和 MIYA Provider 系统
提供统一的模型调用接口
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Provider类型"""

    MIYA = "miya"
    MIXED = "mixed"


@dataclass
class ModelInfo:
    """模型信息"""

    id: str
    name: str
    provider_type: str
    capabilities: List[str] = field(default_factory=list)
    context_length: int = 0
    supports_streaming: bool = True


class UnifiedProviderManager:
    """
    统一的Provider管理器

    功能：
    - 统一模型入口
    - 智能模型选择
    - 模型热切换
    - 负载均衡
    """

    def __init__(self):
        self._miya_providers: Dict[str, Any] = {}
        self._current_provider: Optional[str] = None
        self._initialized = False

    async def initialize(self):
        """初始化统一Provider"""
        logger.info("[UnifiedProviderManager] 初始化...")

        await self._init_miya_providers()

        self._initialized = True
        logger.info("[UnifiedProviderManager] 初始化完成")

    async def _init_miya_providers(self):
        """初始化Miya Providers"""
        try:
            from core.model_pool_manager import ModelPoolManager

            self._miya_providers = {"default": ModelPoolManager()}
            logger.info("[UnifiedProviderManager] Miya模型池已加载")
        except Exception as e:
            logger.warning(f"[UnifiedProviderManager] Miya模型池加载失败: {e}")

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        stream: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """统一的聊天接口"""
        if not model:
            model = self._current_provider or "default"

        if model in self._miya_providers:
            return await self._chat_miya(model, messages, stream, **kwargs)
        else:
            return await self._chat_default(messages, stream, **kwargs)

    async def _chat_miya(
        self, model: str, messages: List[Dict[str, Any]], stream: bool, **kwargs
    ) -> Dict[str, Any]:
        """使用Miya模型池"""
        try:
            pool = self._miya_providers.get(model)
            if pool and hasattr(pool, "chat"):
                return await pool.chat(messages, stream=stream, **kwargs)

            return await self._chat_default(messages, stream, **kwargs)
        except Exception as e:
            logger.error(f"[UnifiedProviderManager] Miya聊天失败: {e}")
            return await self._chat_default(messages, stream, **kwargs)

    async def _chat_default(
        self, messages: List[Dict[str, Any]], stream: bool, **kwargs
    ) -> Dict[str, Any]:
        """默认聊天实现"""
        return {"success": False, "error": "无可用Provider"}

    def list_models(self) -> List[ModelInfo]:
        """列出所有可用模型"""
        models = []

        for name in self._miya_providers:
            models.append(
                ModelInfo(
                    id=name,
                    name=name,
                    provider_type="miya",
                    capabilities=["chat", "completion"],
                )
            )

        return models

    async def select_model(self, task_type: str) -> str:
        """根据任务类型智能选择模型"""
        if task_type in ["agent_task", "complex"] or task_type in ["tool_task", "fast"]:
            return "default"
        return "default"

    async def switch_model(self, model: str) -> bool:
        """切换当前模型"""
        if model in self._miya_providers:
            self._current_provider = model
            logger.info(f"[UnifiedProviderManager] 切换模型: {model}")
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "initialized": self._initialized,
            "current_model": self._current_provider,
            "miya_providers": list(self._miya_providers.keys()),
        }


_unified_provider: Optional[UnifiedProviderManager] = None


def get_unified_provider() -> UnifiedProviderManager:
    """获取全局统一Provider"""
    global _unified_provider
    if _unified_provider is None:
        _unified_provider = UnifiedProviderManager()
    return _unified_provider
