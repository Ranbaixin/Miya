"""
AstrBot 平台加载器

自动加载 AstrBot 的平台适配器并集成到弥娅系统。
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AstrBotPlatformLoader:
    """
    AstrBot 平台加载器

    自动扫描并加载 AstrBot 的平台适配器。
    """

    def __init__(self):
        self._platforms: Dict[str, Any] = {}
        self._sources_dir = Path(__file__).parent / "platform_astrbot" / "sources"

    async def load_all_platforms(self) -> Dict[str, Any]:
        """
        加载所有 AstrBot 平台

        Returns:
            {platform_id: platform_info}
        """
        if not self._sources_dir.exists():
            logger.warning(f"Sources directory not found: {self._sources_dir}")
            return {}

        # 扫描所有子目录
        platform_dirs = [d for d in self._sources_dir.iterdir() if d.is_dir()]
        logger.info(f"Found {len(platform_dirs)} AstrBot platforms")

        for platform_dir in platform_dirs:
            try:
                await self._load_platform_from_dir(platform_dir)
            except Exception as e:
                logger.error(f"Failed to load platform from {platform_dir}: {e}")

        logger.info(f"Loaded {len(self._platforms)} AstrBot platforms")
        return self._platforms

    async def _load_platform_from_dir(self, platform_dir: Path):
        """从目录加载平台"""
        # 提取平台 ID
        platform_id = platform_dir.name

        # 查找适配器文件
        adapter_file = self._find_adapter_file(platform_dir)
        if not adapter_file:
            logger.warning(f"No adapter file found in {platform_dir}")
            return

        # 动态导入模块
        module_path = f"core.platform_astrbot.sources.{platform_id}.{adapter_file.stem}"
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            logger.warning(f"Cannot import {module_path}: {e}")
            return

        # 查找适配器类
        adapter_class = self._find_adapter_class(module)
        if not adapter_class:
            logger.warning(f"No adapter class found in {module_path}")
            return

        # 注册平台
        self._platforms[platform_id] = {
            "class": adapter_class,
            "module": module_path,
            "dir": str(platform_dir),
            "id": platform_id,
        }

        logger.debug(f"Registered platform: {platform_id}")

    def _find_adapter_file(self, platform_dir: Path) -> Optional[Path]:
        """查找适配器文件"""
        # 常见的适配器文件名模式
        patterns = [
            "*_adapter.py",
            "*_platform.py",
            "adapter.py",
            "platform.py",
        ]

        for pattern in patterns:
            files = list(platform_dir.glob(pattern))
            if files:
                return files[0]

        # 如果没有找到，返回第一个 Python 文件
        py_files = list(platform_dir.glob("*.py"))
        if py_files:
            return py_files[0]

        return None

    def _find_adapter_class(self, module) -> Optional[type]:
        """在模块中查找适配器类"""
        # 查找所有类
        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            # 检查是否是类
            if not isinstance(attr, type):
                continue

            # 检查是否是适配器子类
            if self._is_adapter_class(attr):
                return attr

        return None

    def _is_adapter_class(self, cls: type) -> bool:
        """检查是否是适配器类"""
        # 检查类名
        if "Adapter" not in cls.__name__ and "Platform" not in cls.__name__:
            return False

        # 检查是否有必要的方法
        required_methods = ["initialize", "connect", "send_message"]
        return all(hasattr(cls, method) for method in required_methods)

    def get_platform_class(self, platform_id: str) -> Optional[type]:
        """获取平台类"""
        platform_info = self._platforms.get(platform_id)
        if platform_info:
            return platform_info.get("class")
        return None

    def list_platforms(self) -> List[Dict[str, str]]:
        """列出所有可用的平台"""
        return [
            {
                "id": platform_id,
                "class": info["class"].__name__,
                "module": info["module"],
            }
            for platform_id, info in self._platforms.items()
        ]


class AstrBotPlatformManager:
    """
    AstrBot 平台管理器

    管理 AstrBot 平台的加载和实例化。
    """

    def __init__(self):
        self._loader = AstrBotPlatformLoader()
        self._instances: Dict[str, Any] = {}
        self._configs: Dict[str, Dict] = {}

    async def initialize(self, configs: Dict[str, Dict] = None):
        """
        初始化管理器

        Args:
            configs: 平台配置 {platform_id: config}
        """
        # 加载所有平台类
        await self._loader.load_all_platforms()

        # 应用配置
        if configs:
            self._configs = configs

        logger.info(f"Initialized with {len(self._loader.list_platforms())} platforms")

    async def create_platform(
        self,
        platform_id: str,
        config: Dict[str, Any],
    ) -> Optional[Any]:
        """
        创建平台实例

        Args:
            platform_id: 平台 ID
            config: 平台配置

        Returns:
            平台实例
        """
        # 获取平台类
        platform_class = self._loader.get_platform_class(platform_id)
        if not platform_class:
            logger.error(f"Platform not found: {platform_id}")
            return None

        try:
            # 创建实例
            instance = platform_class(config)

            # 初始化
            if hasattr(instance, "initialize"):
                await instance.initialize()

            # 缓存实例
            self._instances[platform_id] = instance
            self._configs[platform_id] = config

            logger.info(f"Created platform: {platform_id}")
            return instance

        except Exception as e:
            logger.error(f"Failed to create platform {platform_id}: {e}")
            return None

    def get_platform(self, platform_id: str) -> Optional[Any]:
        """获取平台实例"""
        return self._instances.get(platform_id)

    def list_available_platforms(self) -> List[Dict[str, str]]:
        """列出所有可用的平台"""
        return self._loader.list_platforms()

    def list_active_platforms(self) -> List[Dict[str, Any]]:
        """列出所有活跃的平台"""
        return [
            {
                "id": platform_id,
                "config": self._configs.get(platform_id, {}),
            }
            for platform_id in self._instances
        ]


# 全局实例
_platform_manager: Optional[AstrBotPlatformManager] = None


async def get_platform_manager() -> AstrBotPlatformManager:
    """获取全局平台管理器"""
    global _platform_manager
    if _platform_manager is None:
        _platform_manager = AstrBotPlatformManager()
        await _platform_manager.initialize()
    return _platform_manager


# 导出
__all__ = [
    "AstrBotPlatformLoader",
    "AstrBotPlatformManager",
    "get_platform_manager",
]
