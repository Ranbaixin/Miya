"""
Miya Provider Manager
融合 AstrBot 的多实例管理和 Miya 的模型选择特性
"""

import asyncio
import copy
import os
import traceback
from collections.abc import Callable
from typing import Any, Optional

from .provider import (
    AbstractProvider,
    LLMProvider,
    TTSProvider,
    STTProvider,
    EmbeddingProvider,
    RerankProvider,
    ProviderType,
    ProviderMeta,
)
from .entities import LLMResponse
import logging

logger = logging.getLogger(__name__)


class ProviderManager:
    """Miya Provider 管理器 - 融合两家之长"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.reload_lock = asyncio.Lock()
        self.resource_lock = asyncio.Lock()

        self.providers_config: list = []
        self.provider_settings: dict = {}
        self.stt_settings: dict = {}
        self.tts_settings: dict = {}

        self.provider_insts: list[LLMProvider] = []
        self.stt_provider_insts: list[STTProvider] = []
        self.tts_provider_insts: list[TTSProvider] = []
        self.embedding_provider_insts: list[EmbeddingProvider] = []
        self.rerank_provider_insts: list[RerankProvider] = []

        self.inst_map: dict[str, AbstractProvider] = {}
        """Provider 实例映射: {provider_id: Provider 实例}"""

        self.curr_provider: LLMProvider | None = None
        self.curr_stt_provider: STTProvider | None = None
        self.curr_tts_provider: TTSProvider | None = None

        self._provider_change_callbacks: list[Callable] = []
        self._mcp_init_task: asyncio.Task | None = None

        self._initialized = True
        logger.info("[ProviderManager] 实例化完成")

    def set_provider_change_hook(self, hook: Callable) -> None:
        """设置 Provider 变更钩子"""
        if hook not in self._provider_change_callbacks:
            self._provider_change_callbacks.append(hook)

    def _notify_provider_changed(
        self,
        provider_id: str,
        provider_type: ProviderType,
        umo: str | None,
    ) -> None:
        """通知 Provider 变更"""
        for hook in self._provider_change_callbacks:
            try:
                hook(provider_id, provider_type, umo)
            except Exception as e:
                logger.warning(f"[ProviderManager] 钩子执行失败: {e}")

    async def initialize(self, config: dict) -> None:
        """初始化所有 Providers"""
        self.providers_config = config.get("provider", [])
        self.provider_settings = config.get("provider_settings", {})
        self.stt_settings = config.get("provider_stt_settings", {})
        self.tts_settings = config.get("provider_tts_settings", {})

        for provider_config in self.providers_config:
            try:
                await self.load_provider(provider_config)
            except Exception as e:
                logger.error(f"[ProviderManager] 加载Provider失败: {e}")
                traceback.print_exc()

        default_provider_id = self.provider_settings.get("default_provider_id")
        if default_provider_id and default_provider_id in self.inst_map:
            self.curr_provider = self.inst_map[default_provider_id]
            logger.info(f"[ProviderManager] 默认Provider: {default_provider_id}")
        elif self.provider_insts:
            self.curr_provider = self.provider_insts[0]

        logger.info(
            f"[ProviderManager] 初始化完成: "
            f"LLM={len(self.provider_insts)}, "
            f"STT={len(self.stt_provider_insts)}, "
            f"TTS={len(self.tts_provider_insts)}"
        )

    def dynamic_import_provider(self, provider_type: str) -> AbstractProvider:
        """动态导入 Provider - 按需加载"""
        from .sources.openai_provider import OpenAIProvider
        from .sources.anthropic_provider import AnthropicProvider
        from .sources.deepseek_provider import DeepSeekProvider
        from .sources.zhipu_provider import ZhipuProvider
        from .sources.siliconflow_provider import SiliconFlowProvider

        provider_map = {
            "openai_chat_completion": OpenAIProvider,
            "anthropic_chat_completion": AnthropicProvider,
            "deepseek_chat_completion": DeepSeekProvider,
            "zhipu_chat_completion": ZhipuProvider,
            "siliconflow_chat_completion": SiliconFlowProvider,
        }

        cls = provider_map.get(provider_type)
        if not cls:
            raise ValueError(f"未知Provider类型: {provider_type}")
        return cls

    async def load_provider(self, provider_config: dict) -> None:
        """加载单个 Provider"""
        if not provider_config.get("enable", True):
            logger.info(
                f"[ProviderManager] Provider {provider_config.get('id')} 已禁用"
            )
            return

        provider_type = provider_config.get("type", "")
        provider_id = provider_config.get("id", "default")

        try:
            cls = self.dynamic_import_provider(provider_type)
        except (ImportError, ValueError) as e:
            logger.warning(f"[ProviderManager] 导入失败: {provider_type} - {e}")
            return

        settings = self._get_provider_settings(provider_config)
        try:
            inst = cls(provider_config, settings)
        except Exception as e:
            logger.error(f"[ProviderManager] 实例化失败: {provider_id} - {e}")
            traceback.print_exc()
            return

        try:
            await inst.initialize()
        except Exception as e:
            logger.warning(f"[ProviderManager] 初始化失败: {provider_id} - {e}")

        self._register_provider_inst(provider_config, inst)
        self.inst_map[provider_id] = inst

        logger.info(f"[ProviderManager] 已加载: {provider_id} ({provider_type})")

    def _register_provider_inst(
        self, provider_config: dict, inst: AbstractProvider
    ) -> None:
        """注册 Provider 实例"""
        provider_type = provider_config.get("type", "")
        provider_id = provider_config.get("id", "default")

        if "chat_completion" in provider_type:
            if isinstance(inst, LLMProvider):
                self.provider_insts.append(inst)
                if self.provider_settings.get("default_provider_id") == provider_id:
                    self.curr_provider = inst
                    logger.info(f"[ProviderManager] 设为默认LLM: {provider_id}")
                if not self.curr_provider:
                    self.curr_provider = inst
        elif "stt" in provider_type:
            if isinstance(inst, STTProvider):
                self.stt_provider_insts.append(inst)
                if not self.curr_stt_provider:
                    self.curr_stt_provider = inst
        elif "tts" in provider_type:
            if isinstance(inst, TTSProvider):
                self.tts_provider_insts.append(inst)
                if not self.curr_tts_provider:
                    self.curr_tts_provider = inst

    def _get_provider_settings(self, provider_config: dict) -> dict:
        """获取 Provider 配置"""
        return self.provider_settings

    async def get_provider(
        self, provider_type: ProviderType, umo: str | None = None
    ) -> AbstractProvider | None:
        """获取 Provider - 支持会话隔离"""
        if umo:
            provider_id = await self._get_provider_from_session(umo, provider_type)
            if provider_id and provider_id in self.inst_map:
                return self.inst_map[provider_id]

        return self._get_default_provider(provider_type)

    def _get_default_provider(
        self, provider_type: ProviderType
    ) -> AbstractProvider | None:
        """获取默认 Provider"""
        if provider_type == ProviderType.CHAT_COMPLETION:
            return self.curr_provider
        elif provider_type == ProviderType.SPEECH_TO_TEXT:
            return self.curr_stt_provider
        elif provider_type == ProviderType.TEXT_TO_SPEECH:
            return self.curr_tts_provider
        return self.curr_provider

    async def _get_provider_from_session(
        self, umo: str, provider_type: ProviderType
    ) -> str | None:
        """从会话获取 Provider ID"""
        try:
            from core.session import get_session_var

            return await get_session_var(umo, f"provider_{provider_type.value}")
        except Exception:
            return None

    async def set_provider(
        self,
        provider_id: str,
        provider_type: ProviderType,
        umo: str | None = None,
    ) -> None:
        """设置当前 Provider - 支持会话隔离"""
        if provider_id not in self.inst_map:
            raise ValueError(f"Provider不存在: {provider_id}")

        if umo:
            try:
                from core.session import set_session_var

                await set_session_var(
                    umo, f"provider_{provider_type.value}", provider_id
                )
            except Exception:
                pass
            self._notify_provider_changed(provider_id, provider_type, umo)
            return

        provider = self.inst_map[provider_id]
        if provider_type == ProviderType.CHAT_COMPLETION and isinstance(
            provider, LLMProvider
        ):
            self.curr_provider = provider
        elif provider_type == ProviderType.SPEECH_TO_TEXT and isinstance(
            provider, STTProvider
        ):
            self.curr_stt_provider = provider
        elif provider_type == ProviderType.TEXT_TO_SPEECH and isinstance(
            provider, TTSProvider
        ):
            self.curr_tts_provider = provider

        self._notify_provider_changed(provider_id, provider_type, None)

    def get_provider_by_id(self, provider_id: str) -> AbstractProvider | None:
        """根据 ID 获取 Provider"""
        return self.inst_map.get(provider_id)

    async def reload(self, provider_config: dict) -> None:
        """重载 Provider - 热重载"""
        async with self.reload_lock:
            provider_id = provider_config.get("id")
            if provider_id in self.inst_map:
                await self.terminate_provider(provider_id)

            if provider_config.get("enable", True):
                await self.load_provider(provider_config)

    async def terminate_provider(self, provider_id: str) -> None:
        """终止 Provider"""
        if provider_id not in self.inst_map:
            return

        logger.info(f"[ProviderManager] 终止: {provider_id}")

        inst = self.inst_map[provider_id]
        if inst in self.provider_insts:
            self.provider_insts.remove(inst)
        elif inst in self.stt_provider_insts:
            self.stt_provider_insts.remove(inst)
        elif inst in self.tts_provider_insts:
            self.tts_provider_insts.remove(inst)

        if self.curr_provider and self.curr_provider.meta().id == provider_id:
            self.curr_provider = None
        if self.curr_stt_provider and self.curr_stt_provider.meta().id == provider_id:
            self.curr_stt_provider = None
        if self.curr_tts_provider and self.curr_tts_provider.meta().id == provider_id:
            self.curr_tts_provider = None

        if hasattr(inst, "terminate"):
            await inst.terminate()

        del self.inst_map[provider_id]
        logger.info(f"[ProviderManager] 已终止: {provider_id}")

    async def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        provider_id: str | None = None,
    ) -> LLMResponse:
        """简便聊天接口"""
        provider = None
        if provider_id and provider_id in self.inst_map:
            provider = self.inst_map[provider_id]
        else:
            provider = self.curr_provider

        if not provider:
            raise ValueError("没有可用的Provider")

        messages = (
            [{"role": "system", "content": system_prompt}] if system_prompt else []
        )
        return await provider.text_chat(
            prompt=prompt,
            messages=messages,
            tools=tools,
        )

    async def chat_with_functions(
        self,
        prompt: str,
        system_prompt: str,
        tools: list[dict],
        max_iterations: int = 10,
    ) -> tuple[str, list[dict]]:
        """带工具调用的聊天"""
        if not self.curr_provider:
            raise ValueError("没有可用的LLM Provider")

        return await self.curr_provider.chat_with_functions(
            prompt=prompt,
            system_prompt=system_prompt,
            tools=tools,
            max_iterations=max_iterations,
        )

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "llm_providers": len(self.provider_insts),
            "stt_providers": len(self.stt_provider_insts),
            "tts_providers": len(self.tts_provider_insts),
            "embedding_providers": len(self.embedding_provider_insts),
            "rerank_providers": len(self.rerank_provider_insts),
            "curr_provider": self.curr_provider.meta().id
            if self.curr_provider
            else None,
            "curr_stt": self.curr_stt_provider.meta().id
            if self.curr_stt_provider
            else None,
            "curr_tts": self.curr_tts_provider.meta().id
            if self.curr_tts_provider
            else None,
        }

    async def terminate(self) -> None:
        """终止所有 Providers"""
        for inst in self.provider_insts:
            if hasattr(inst, "terminate"):
                await inst.terminate()
        for inst in self.stt_provider_insts:
            if hasattr(inst, "terminate"):
                await inst.terminate()
        for inst in self.tts_provider_insts:
            if hasattr(inst, "terminate"):
                await inst.terminate()

        self.inst_map.clear()
        self.provider_insts.clear()
        self.stt_provider_insts.clear()
        self.tts_provider_insts.clear()
        logger.info("[ProviderManager] 已终止所有Providers")


_provider_manager_instance: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """获取全局 ProviderManager 实例"""
    global _provider_manager_instance
    if _provider_manager_instance is None:
        _provider_manager_instance = ProviderManager()
    return _provider_manager_instance
