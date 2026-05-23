"""
配置热重载系统
"""

import asyncio
import contextlib
import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class ConfigSource(Enum):
    """配置来源"""
    FILE = "file"
    ENV = "env"
    DATABASE = "database"
    API = "api"


class ConfigChangeType(Enum):
    """配置变更类型"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    RELOADED = "reloaded"


@dataclass
class ConfigChange:
    """配置变更"""
    source: ConfigSource
    path: str
    change_type: ConfigChangeType
    timestamp: float = field(default_factory=time.time)
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    checksum: Optional[str] = None


@dataclass
class ConfigWatcherConfig:
    """配置监视器配置"""
    watch_interval: float = 5.0  # 检查间隔（秒）
    debounce_time: float = 1.0   # 防抖时间（秒）
    recursive: bool = True       # 是否递归监视
    file_patterns: List[str] = field(default_factory=lambda: [
        "*.json", "*.yaml", "*.yml", "*.toml", ".env"
    ])
    ignore_patterns: List[str] = field(default_factory=lambda: [
        "*.tmp", "*.bak", "*.swp"
    ])


class ConfigFileHandler(FileSystemEventHandler):
    """配置文件事件处理器"""
    
    def __init__(self, hot_reloader: "ConfigHotReloader"):
        self.hot_reloader = hot_reloader
    
    def on_modified(self, event):
        if not event.is_directory:
            self.hot_reloader._handle_file_change(event.src_path, ConfigChangeType.MODIFIED)
    
    def on_created(self, event):
        if not event.is_directory:
            self.hot_reloader._handle_file_change(event.src_path, ConfigChangeType.CREATED)
    
    def on_deleted(self, event):
        if not event.is_directory:
            self.hot_reloader._handle_file_change(event.src_path, ConfigChangeType.DELETED)


class ConfigHotReloader:
    """配置热重载器"""
    
    def __init__(self, config: Optional[ConfigWatcherConfig] = None):
        self.config = config or ConfigWatcherConfig()
        self.watched_files: Dict[str, float] = {}
        self.file_checksums: Dict[str, str] = {}
        self.observers: List[Observer] = []
        self.change_handlers: List[Callable[[ConfigChange], None]] = []
        self._lock = threading.RLock()
        self._debounce_timers: Dict[str, asyncio.Task] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        logger.info("配置热重载器初始化完成")
    
    def add_watch_path(self, path: str):
        """添加监视路径
        
        Args:
            path: 要监视的路径
        """
        path_obj = Path(path)
        if not path_obj.exists():
            logger.warning(f"监视路径不存在: {path}")
            return
        
        with self._lock:
            if path in self.watched_files:
                logger.debug(f"路径已在监视中: {path}")
                return
            
            self.watched_files[path] = time.time()
            
            # 设置文件监视器
            if path_obj.is_file():
                self._setup_file_watcher(path_obj.parent, recursive=False)
            else:
                self._setup_file_watcher(path_obj, recursive=self.config.recursive)
            
            logger.info(f"已添加监视路径: {path}")
    
    def _setup_file_watcher(self, path: Path, recursive: bool = True):
        """设置文件监视器"""
        try:
            event_handler = ConfigFileHandler(self)
            observer = Observer()
            observer.schedule(event_handler, str(path), recursive=recursive)
            observer.start()
            self.observers.append(observer)
            logger.debug(f"已设置文件监视器: {path}")
        except Exception as e:
            logger.error(f"设置文件监视器失败: {e}")
    
    def add_change_handler(self, handler: Callable[[ConfigChange], None]):
        """添加变更处理器
        
        Args:
            handler: 变更处理函数
        """
        with self._lock:
            if handler not in self.change_handlers:
                self.change_handlers.append(handler)
                logger.debug(f"已添加变更处理器: {handler.__name__}")
    
    def remove_change_handler(self, handler: Callable[[ConfigChange], None]):
        """移除变更处理器"""
        with self._lock:
            if handler in self.change_handlers:
                self.change_handlers.remove(handler)
                logger.debug(f"已移除变更处理器: {handler.__name__}")
    
    def _handle_file_change(self, file_path: str, change_type: ConfigChangeType):
        """处理文件变更"""
        file_path = Path(file_path).resolve()
        
        # 检查文件模式
        if not self._should_watch_file(file_path):
            return
        
        # 防抖处理
        self._debounce_file_change(str(file_path), change_type)
    
    def _should_watch_file(self, file_path: Path) -> bool:
        """检查是否应该监视文件"""
        filename = file_path.name
        
        # 检查忽略模式
        for pattern in self.config.ignore_patterns:
            if filename.endswith(pattern.replace("*", "")):
                return False
        
        # 检查文件模式
        for pattern in self.config.file_patterns:
            if pattern.startswith("*."):
                ext = pattern[1:]  # 去掉*号
                if filename.endswith(ext):
                    return True
        
        return filename in [".env", "config.json", "settings.yaml"]
    
    def _debounce_file_change(self, file_path: str, change_type: ConfigChangeType):
        """防抖处理文件变更"""
        with self._lock:
            # 取消现有的防抖定时器
            if file_path in self._debounce_timers:
                self._debounce_timers[file_path].cancel()
            
            # 创建新的防抖任务
            async def debounced_change():
                await asyncio.sleep(self.config.debounce_time)
                await self._process_file_change(file_path, change_type)
                with self._lock:
                    if file_path in self._debounce_timers:
                        del self._debounce_timers[file_path]
            
            self._debounce_timers[file_path] = asyncio.create_task(debounced_change())
    
    async def _process_file_change(self, file_path: str, change_type: ConfigChangeType):
        """处理文件变更"""
        try:
            file_path_obj = Path(file_path)
            
            if change_type == ConfigChangeType.DELETED:
                # 文件被删除
                old_checksum = self.file_checksums.get(file_path)
                if old_checksum:
                    del self.file_checksums[file_path]
                
                change = ConfigChange(
                    source=ConfigSource.FILE,
                    path=file_path,
                    change_type=change_type,
                    old_value=None,
                    new_value=None,
                    checksum=old_checksum
                )
                
                await self._notify_change_handlers(change)
                return
            
            # 计算新文件的校验和
            if file_path_obj.exists():
                new_checksum = self._calculate_file_checksum(file_path)
                old_checksum = self.file_checksums.get(file_path)
                
                # 检查是否真的发生了变化
                if new_checksum == old_checksum:
                    logger.debug(f"文件未实际变化: {file_path}")
                    return
                
                # 更新校验和
                self.file_checksums[file_path] = new_checksum
                
                # 加载新配置
                new_config = self._load_config_file(file_path)
                
                change = ConfigChange(
                    source=ConfigSource.FILE,
                    path=file_path,
                    change_type=change_type,
                    old_value=None,  # 可以从其他地方获取旧值
                    new_value=new_config,
                    checksum=new_checksum
                )
                
                await self._notify_change_handlers(change)
                logger.info(f"配置文件已重新加载: {file_path}")
            
        except Exception as e:
            logger.error(f"处理文件变更失败: {e}")
    
    def _calculate_file_checksum(self, file_path: str) -> str:
        """计算文件校验和"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.error(f"计算文件校验和失败: {e}")
            return ""
    
    def _load_config_file(self, file_path: str) -> Any:
        """加载配置文件"""
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            return None
        
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            elif file_path.endswith(('.yaml', '.yml')):
                import yaml
                with open(file_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            
            elif file_path.endswith('.toml'):
                import tomli
                with open(file_path, 'rb') as f:
                    return tomli.load(f)
            
            elif file_path == '.env':
                # 加载环境变量文件
                env_vars = {}
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
                return env_vars
            
            else:
                # 尝试作为文本文件加载
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
                
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return None
    
    async def _notify_change_handlers(self, change: ConfigChange):
        """通知变更处理器"""
        for handler in self.change_handlers[:]:  # 复制列表以避免在迭代中修改
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(change)
                else:
                    handler(change)
            except Exception as e:
                logger.error(f"变更处理器执行失败: {e}")
    
    async def manual_reload(self, file_path: str) -> bool:
        """手动重新加载配置
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功重新加载
        """
        try:
            if not Path(file_path).exists():
                logger.error(f"文件不存在: {file_path}")
                return False
            
            await self._process_file_change(file_path, ConfigChangeType.RELOADED)
            return True
            
        except Exception as e:
            logger.error(f"手动重新加载失败: {e}")
            return False
    
    async def start(self):
        """启动热重载器"""
        if self._running:
            logger.warning("热重载器已在运行")
            return
        
        self._running = True
        
        async def watch_loop():
            while self._running:
                try:
                    await self._check_for_changes()
                    await asyncio.sleep(self.config.watch_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"监视循环错误: {e}")
                    await asyncio.sleep(5.0)
        
        self._task = asyncio.create_task(watch_loop())
        logger.info("配置热重载器已启动")
    
    async def _check_for_changes(self):
        """检查变更"""
        for file_path in list(self.watched_files.keys()):
            if Path(file_path).is_file():
                current_mtime = Path(file_path).stat().st_mtime
                last_mtime = self.watched_files.get(file_path, 0)
                
                if current_mtime > last_mtime:
                    self.watched_files[file_path] = current_mtime
                    await self._process_file_change(file_path, ConfigChangeType.MODIFIED)
    
    async def stop(self):
        """停止热重载器"""
        self._running = False
        
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        
        # 停止所有观察者
        for observer in self.observers:
            observer.stop()
            observer.join()
        
        self.observers.clear()
        logger.info("配置热重载器已停止")
    
    def __enter__(self):
        """上下文管理器入口"""
        asyncio.create_task(self.start())
        return self
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        asyncio.run(self.stop())
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()


# 全局热重载器实例
_global_hot_reloader: Optional[ConfigHotReloader] = None


def get_hot_reloader() -> ConfigHotReloader:
    """获取全局热重载器实例"""
    global _global_hot_reloader
    if _global_hot_reloader is None:
        _global_hot_reloader = ConfigHotReloader()
    return _global_hot_reloader


async def start_hot_reloading():
    """启动全局热重载"""
    reloader = get_hot_reloader()
    await reloader.start()


async def stop_hot_reloading():
    """停止全局热重载"""
    reloader = get_hot_reloader()
    await reloader.stop()


# 配置管理器集成
class HotReloadableConfig:
    """热重载配置管理器"""
    
    def __init__(self, config_path: str, default_config: Dict[str, Any]):
        self.config_path = config_path
        self.default_config = default_config
        self.current_config = self._load_config()
        self.hot_reloader = get_hot_reloader()
        self._change_handlers: List[Callable[[Dict[str, Any]], None]] = []
        
        # 添加监视路径
        self.hot_reloader.add_watch_path(config_path)
        
        # 添加变更处理器
        self.hot_reloader.add_change_handler(self._on_config_change)
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config_path_obj = Path(self.config_path)
        
        if not config_path_obj.exists():
            logger.warning(f"配置文件不存在，使用默认配置: {self.config_path}")
            return self.default_config.copy()
        
        try:
            loaded_config = self.hot_reloader._load_config_file(self.config_path)
            if loaded_config is None:
                return self.default_config.copy()
            
            # 合并默认配置和加载的配置
            merged_config = self.default_config.copy()
            merged_config.update(loaded_config)
            return merged_config
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return self.default_config.copy()
    
    def _on_config_change(self, change: ConfigChange):
        """配置变更处理"""
        if change.path == self.config_path and change.new_value is not None:
            self.current_config.copy()
            self.current_config = self._load_config()
            
            # 通知变更处理器
            for handler in self._change_handlers:
                try:
                    handler(self.current_config)
                except Exception as e:
                    logger.error(f"配置变更处理器执行失败: {e}")
            
            logger.info(f"配置已热重载: {self.config_path}")
    
    def add_change_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """添加配置变更处理器"""
        if handler not in self._change_handlers:
            self._change_handlers.append(handler)
    
    def remove_change_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """移除配置变更处理器"""
        if handler in self._change_handlers:
            self._change_handlers.remove(handler)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.current_config.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置值（仅内存中）"""
        self.current_config[key] = value
    
    async def save(self):
        """保存配置到文件"""
        try:
            Path(self.config_path)
            
            if self.config_path.endswith('.json'):
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.current_config, f, indent=2, ensure_ascii=False)
            
            elif self.config_path.endswith(('.yaml', '.yml')):
                import yaml
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self.current_config, f, default_flow_style=False)
            
            else:
                logger.error(f"不支持的配置文件格式: {self.config_path}")
                return False
            
            logger.info(f"配置已保存: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def __getitem__(self, key: str) -> Any:
        """获取配置项"""
        return self.current_config[key]
    
    def __setitem__(self, key: str, value: Any):
        """设置配置项"""
        self.current_config[key] = value
    
    def __contains__(self, key: str) -> bool:
        """检查配置项是否存在"""
        return key in self.current_config
