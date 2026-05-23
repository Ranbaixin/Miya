"""
智能缓存管理系统
"""

import asyncio
import hashlib
import logging
import pickle
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class CachePolicy(Enum):
    """缓存策略"""
    LRU = "lru"          # 最近最少使用
    LFU = "lfu"          # 最不经常使用
    FIFO = "fifo"        # 先进先出
    TTL = "ttl"          # 生存时间
    WRITE_THROUGH = "write_through"  # 直写
    WRITE_BACK = "write_back"        # 回写


class CacheLevel(Enum):
    """缓存级别"""
    MEMORY = "memory"    # 内存缓存
    DISK = "disk"        # 磁盘缓存
    REDIS = "redis"      # Redis缓存
    MULTI_LEVEL = "multi_level"  # 多级缓存


@dataclass
class CacheConfig:
    """缓存配置"""
    max_size: int = 1000                    # 最大缓存条目数
    default_ttl: int = 300                  # 默认生存时间（秒）
    cleanup_interval: int = 60              # 清理间隔（秒）
    memory_limit_mb: int = 100              # 内存限制（MB）
    disk_path: Optional[str] = None         # 磁盘缓存路径
    redis_url: Optional[str] = None         # Redis连接URL
    policy: CachePolicy = CachePolicy.LRU   # 缓存策略
    level: CacheLevel = CacheLevel.MEMORY   # 缓存级别
    compression: bool = True                # 是否压缩
    statistics_enabled: bool = True         # 是否启用统计


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    size: int = 0
    ttl: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() > self.created_at + self.ttl
    
    @property
    def age(self) -> float:
        """条目年龄（秒）"""
        return time.time() - self.created_at
    
    def touch(self):
        """更新访问时间"""
        self.accessed_at = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size: int = 0
    total_entries: int = 0
    hit_rate: float = 0.0
    avg_access_time: float = 0.0
    
    def update_hit_rate(self):
        """更新命中率"""
        total = self.hits + self.misses
        self.hit_rate = self.hits / total if total > 0 else 0.0


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._cache: Dict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats()
        self._lock = threading.RLock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._tag_index: Dict[str, List[str]] = {}
        
        # 初始化存储后端
        self._storage = self._init_storage()
        
        # 启动清理任务
        if self.config.cleanup_interval > 0:
            self._start_cleanup_task()
    
    def _init_storage(self):
        """初始化存储后端"""
        if self.config.level == CacheLevel.DISK and self.config.disk_path:
            try:
                import shelve
                return shelve.open(self.config.disk_path)
            except ImportError:
                logger.warning("shelve模块不可用，使用内存存储")
        
        elif self.config.level == CacheLevel.REDIS and self.config.redis_url:
            try:
                import redis
                return redis.Redis.from_url(self.config.redis_url)
            except ImportError:
                logger.warning("redis模块不可用，使用内存存储")
        
        return None  # 使用内存存储
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(self.config.cleanup_interval)
                self.cleanup()

        # FIX: 在无事件循环/非主线程环境下，get_event_loop() 可能抛异常或返回未运行的 loop。
        # 使用 get_running_loop() 更可靠；若当前没有运行中的 loop，则不启动后台清理任务。
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                self._cleanup_task = loop.create_task(cleanup_loop())
            else:
                logger.warning("事件循环未运行，无法启动清理任务")
        except RuntimeError:
            logger.warning("事件循环未运行，无法启动清理任务")
    
    def _generate_key(self, func: Callable, *args, **kwargs) -> str:
        """生成缓存键"""
        # 序列化参数
        args_repr = pickle.dumps(args)
        kwargs_repr = pickle.dumps(sorted(kwargs.items()))
        
        # 生成唯一键
        key_data = f"{func.__module__}.{func.__name__}:{args_repr}:{kwargs_repr}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _calculate_size(self, value: Any) -> int:
        """计算值的大小"""
        try:
            serialized = pickle.dumps(value)
            return len(serialized)
        except Exception:
            return 1024  # 默认大小
    
    def _evict_if_needed(self):
        """如果需要则驱逐条目"""
        if len(self._cache) >= self.config.max_size:
            self._evict_entries()
    
    def _evict_entries(self):
        """根据策略驱逐条目"""
        with self._lock:
            if self.config.policy == CachePolicy.LRU:
                # 移除最久未使用的条目
                while len(self._cache) >= self.config.max_size:
                    key, _ = self._cache.popitem(last=False)
                    self._remove_from_tag_index(key)
                    self._stats.evictions += 1
            
            elif self.config.policy == CachePolicy.LFU:
                # 移除访问次数最少的条目
                sorted_entries = sorted(
                    self._cache.items(),
                    key=lambda x: x[1].access_count
                )
                for key, _ in sorted_entries[:len(self._cache) - self.config.max_size + 1]:
                    del self._cache[key]
                    self._remove_from_tag_index(key)
                    self._stats.evictions += 1
            
            elif self.config.policy == CachePolicy.TTL:
                # 移除过期的条目
                expired_keys = [
                    key for key, entry in self._cache.items()
                    if entry.is_expired
                ]
                for key in expired_keys:
                    del self._cache[key]
                    self._remove_from_tag_index(key)
                    # FIX: 逐条驱逐时不应每次加 len(expired_keys)，否则统计会被放大 N 倍。
                    self._stats.evictions += 1
    
    def _add_to_tag_index(self, key: str, tags: List[str]):
        """添加到标签索引"""
        for tag in tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            if key not in self._tag_index[tag]:
                self._tag_index[tag].append(key)
    
    def _remove_from_tag_index(self, key: str):
        """从标签索引中移除"""
        for tag_keys in self._tag_index.values():
            if key in tag_keys:
                tag_keys.remove(key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值
        
        Args:
            key: 缓存键
            default: 默认值
            
        Returns:
            缓存值或默认值
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                
                if entry.is_expired:
                    del self._cache[key]
                    self._remove_from_tag_index(key)
                    self._stats.misses += 1
                    return default
                
                # 移动到最后（LRU策略）
                self._cache.move_to_end(key)
                entry.touch()
                self._stats.hits += 1
                return entry.value
            
            self._stats.misses += 1
            return default
    
    async def get_async(self, key: str, default: Any = None) -> Any:
        """异步获取缓存值"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.get, key, default
        )
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ):
        """设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）
            tags: 标签列表
        """
        with self._lock:
            # 计算大小
            size = self._calculate_size(value)
            
            # 创建条目
            entry = CacheEntry(
                key=key,
                value=value,
                ttl=ttl or self.config.default_ttl,
                tags=tags or [],
                size=size
            )
            
            # 添加到缓存
            self._cache[key] = entry
            self._add_to_tag_index(key, entry.tags)
            
            # 更新统计
            self._stats.total_entries = len(self._cache)
            self._stats.total_size += size
            
            # 检查是否需要驱逐
            self._evict_if_needed()
            
            # 更新存储后端
            if self._storage is not None:
                self._storage[key] = entry
    
    async def set_async(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ):
        """异步设置缓存值"""
        await asyncio.get_event_loop().run_in_executor(
            None, self.set, key, value, ttl, tags
        )
    
    def delete(self, key: str) -> bool:
        """删除缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._stats.total_size -= entry.size
                del self._cache[key]
                self._remove_from_tag_index(key)
                
                # 更新存储后端
                if self._storage is not None and key in self._storage:
                    del self._storage[key]
                
                return True
            return False
    
    async def delete_async(self, key: str) -> bool:
        """异步删除缓存值"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.delete, key
        )
    
    def clear(self):
        """清除所有缓存"""
        with self._lock:
            self._cache.clear()
            self._tag_index.clear()
            self._stats = CacheStats()
            
            if self._storage is not None:
                if hasattr(self._storage, 'clear'):
                    self._storage.clear()
                else:
                    for key in list(self._storage.keys()):
                        del self._storage[key]
    
    async def clear_async(self):
        """异步清除所有缓存"""
        await asyncio.get_event_loop().run_in_executor(None, self.clear)
    
    def invalidate_by_tag(self, tag: str):
        """根据标签使缓存失效
        
        Args:
            tag: 标签
        """
        with self._lock:
            if tag in self._tag_index:
                for key in self._tag_index[tag]:
                    if key in self._cache:
                        entry = self._cache[key]
                        self._stats.total_size -= entry.size
                        del self._cache[key]
                
                del self._tag_index[tag]
    
    async def invalidate_by_tag_async(self, tag: str):
        """异步根据标签使缓存失效"""
        await asyncio.get_event_loop().run_in_executor(
            None, self.invalidate_by_tag, tag
        )
    
    def exists(self, key: str) -> bool:
        """检查键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry.is_expired:
                    del self._cache[key]
                    self._remove_from_tag_index(key)
                    return False
                return True
            return False
    
    def get_stats(self) -> CacheStats:
        """获取缓存统计"""
        with self._lock:
            self._stats.update_hit_rate()
            self._stats.total_entries = len(self._cache)
            return self._stats
    
    def cleanup(self):
        """清理过期条目"""
        with self._lock:
            expired_keys = []
            
            for key, entry in self._cache.items():
                if entry.is_expired:
                    expired_keys.append(key)
            
            for key in expired_keys:
                entry = self._cache[key]
                self._stats.total_size -= entry.size
                del self._cache[key]
                self._remove_from_tag_index(key)
                self._stats.evictions += 1
            
            if expired_keys:
                logger.debug(f"清理了 {len(expired_keys)} 个过期缓存条目")
    
    def __contains__(self, key: str) -> bool:
        """检查键是否存在"""
        return self.exists(key)
    
    def __len__(self) -> int:
        """缓存条目数量"""
        return len(self._cache)
    
    def __del__(self):
        """析构函数"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
        
        if self._storage is not None and hasattr(self._storage, 'close'):
            self._storage.close()


# 缓存装饰器
def cached(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    tags: Optional[List[str]] = None,
    cache_instance: Optional[CacheManager] = None
):
    """缓存装饰器
    
    Args:
        ttl: 生存时间（秒）
        key_prefix: 键前缀
        tags: 标签列表
        cache_instance: 缓存管理器实例
    """
    cache = cache_instance or _global_cache_manager
    
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache._generate_key(func, *args, **kwargs)
            if key_prefix:
                cache_key = f"{key_prefix}:{cache_key}"
            
            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache.set(cache_key, result, ttl=ttl, tags=tags)
            
            return result
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache._generate_key(func, *args, **kwargs)
            if key_prefix:
                cache_key = f"{key_prefix}:{cache_key}"
            
            # 尝试从缓存获取
            cached_value = await cache.get_async(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            await cache.set_async(cache_key, result, ttl=ttl, tags=tags)
            
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def invalidate_cache(
    key_prefix: str = "",
    tags: Optional[List[str]] = None,
    cache_instance: Optional[CacheManager] = None
):
    """使缓存失效装饰器
    
    Args:
        key_prefix: 键前缀
        tags: 标签列表
        cache_instance: 缓存管理器实例
    """
    cache = cache_instance or _global_cache_manager
    
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # 使相关缓存失效
            if tags:
                for tag in tags:
                    cache.invalidate_by_tag(tag)
            
            return result
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # 使相关缓存失效
            if tags:
                for tag in tags:
                    await cache.invalidate_by_tag_async(tag)
            
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# 全局缓存管理器实例
_global_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager()
    return _global_cache_manager


def clear_cache():
    """清除全局缓存"""
    cache = get_cache_manager()
    cache.clear()


async def clear_cache_async():
    """异步清除全局缓存"""
    cache = get_cache_manager()
    await cache.clear_async()
