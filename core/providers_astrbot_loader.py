"""
AstrBot Provider 加载器

自动加载 AstrBot 的模型源并适配到弥娅系统。
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AstrBotProviderLoader:
    """
    AstrBot Provider 加载器

    自动扫描并加载 AstrBot 的模型源。
    """

    def __init__(self):
        self._providers: Dict[str, Any] = {}
        self._sources_dir = Path(__file__).parent / "providers_astrbot" / "sources"

    async def load_all_providers(self) -> Dict[str, Any]:
        """
        加载所有 AstrBot Provider

        Returns:
            {provider_id: provider_instance}
        """
        if not self._sources_dir.exists():
            logger.warning(f"Sources directory not found: {self._sources_dir}")
            return {}

        # 扫描所有 Python 文件
        source_files = list(self._sources_dir.glob("*_source.py"))
        logger.info(f"Found {len(source_files)} AstrBot provider sources")

        for source_file in source_files:
            try:
                await self._load_provider_from_file(source_file)
            except Exception as e:
                logger.error(f"Failed to load provider from {source_file}: {e}")

        logger.info(f"Loaded {len(self._providers)} AstrBot providers")
        return self._providers

    async def _load_provider_from_file(self, source_file: Path):
        """从文件加载 Provider"""
        # 提取 Provider ID
        provider_id = source_file.stem.replace("_source", "").replace("_api", "")

        # 动态导入模块
        module_path = f"core.providers_astrbot.sources.{source_file.stem}"
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            logger.warning(f"Cannot import {module_path}: {e}")
            return

        # 查找 Provider 类
        provider_class = self._find_provider_class(module)
        if not provider_class:
            logger.warning(f"No provider class found in {module_path}")
            return

        # 创建 Provider 实例（需要配置）
        # 注意：这里只是注册 Provider 类，实际实例化需要配置
        self._providers[provider_id] = {
            "class": provider_class,
            "module": module_path,
            "file": str(source_file),
            "id": provider_id,
        }

        logger.debug(f"Registered provider: {provider_id}")

    def _find_provider_class(self, module) -> Optional[type]:
        """在模块中查找 Provider 类"""
        # 查找所有类
        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            # 检查是否是类
            if not isinstance(attr, type):
                continue

            # 检查是否是 Provider 子类
            if self._is_provider_class(attr):
                return attr

        return None

    def _is_provider_class(self, cls: type) -> bool:
        """检查是否是 Provider 类"""
        # 检查类名
        if "Provider" not in cls.__name__:
            return False

        # 检查是否有 chat 方法
        if not hasattr(cls, "chat"):
            return False

        # 检查是否有 initialize 方法
        return hasattr(cls, "initialize")

    def get_provider_class(self, provider_id: str) -> Optional[type]:
        """获取 Provider 类"""
        provider_info = self._providers.get(provider_id)
        if provider_info:
            return provider_info.get("class")
        return None

    def list_providers(self) -> List[Dict[str, str]]:
        """列出所有可用的 Provider"""
        return [
            {
                "id": provider_id,
                "class": info["class"].__name__,
                "module": info["module"],
            }
            for provider_id, info in self._providers.items()
        ]


class AstrBotProviderManager:
    """
    AstrBot Provider 管理器

    管理 AstrBot Provider 的加载和实例化。
    """

    def __init__(self):
        self._loader = AstrBotProviderLoader()
        self._instances: Dict[str, Any] = {}
        self._configs: Dict[str, Dict] = {}

    async def initialize(self, configs: Dict[str, Dict] = None):
        """
        初始化管理器

        Args:
            configs: Provider 配置 {provider_id: config}
        """
        # 加载所有 Provider 类
        await self._loader.load_all_providers()

        # 应用配置
        if configs:
            self._configs = configs

        logger.info(f"Initialized with {len(self._loader.list_providers())} providers")

    async def create_provider(
        self,
        provider_id: str,
        config: Dict[str, Any],
    ) -> Optional[Any]:
        """
        创建 Provider 实例

        Args:
            provider_id: Provider ID
            config: Provider 配置

        Returns:
            Provider 实例
        """
        # 获取 Provider 类
        provider_class = self._loader.get_provider_class(provider_id)
        if not provider_class:
            logger.error(f"Provider not found: {provider_id}")
            return None

        try:
            # 创建实例
            instance = provider_class(config)

            # 初始化
            if hasattr(instance, "initialize"):
                await instance.initialize()

            # 缓存实例
            self._instances[provider_id] = instance
            self._configs[provider_id] = config

            logger.info(f"Created provider: {provider_id}")
            return instance

        except Exception as e:
            logger.error(f"Failed to create provider {provider_id}: {e}")
            return None

    def get_provider(self, provider_id: str) -> Optional[Any]:
        """获取 Provider 实例"""
        return self._instances.get(provider_id)

    def list_available_providers(self) -> List[Dict[str, str]]:
        """列出所有可用的 Provider"""
        return self._loader.list_providers()

    def list_active_providers(self) -> List[Dict[str, Any]]:
        """列出所有活跃的 Provider"""
        return [
            {
                "id": provider_id,
                "config": self._configs.get(provider_id, {}),
            }
            for provider_id in self._instances
        ]


# 全局实例
_provider_manager: Optional[AstrBotProviderManager] = None


async def get_provider_manager() -> AstrBotProviderManager:
    """获取全局 Provider 管理器"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = AstrBotProviderManager()
        await _provider_manager.initialize()
    return _provider_manager


# 导出
__all__ = [
    "AstrBotProviderLoader",
    "AstrBotProviderManager",
    "get_provider_manager",
]
