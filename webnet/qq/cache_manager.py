"""
QQ子网缓存管理器
统一管理QQ子网的所有缓存操作
遵循Miya Subnet架构设计

这个模块是QQ子网缓存集成的核心，提供统一的缓存接口
替代了之前分散在各个模块的本地缓存实现。
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """缓存配置"""
    message_ttl: float = 3600  # 消息缓存1小时
    image_ttl: float = 86400  # 图片缓存24小时
    config_ttl: float = 3600  # 配置缓存1小时
    user_ttl: float = 3600  # 用户资料缓存1小时
    group_ttl: float = 3600  # 群组信息缓存1小时
    session_ttl: float = 1800  # 会话缓存30分钟


class QQCacheManager:
    """QQ子网独立缓存管理器
    
    为了避免对 core.cache 模块的强依赖，提供本地缓存实现。
    支持后续升级到统一缓存系统。
    
    缓存结构:
    {
        'qq_messages': {...},  # 消息缓存
        'qq_images': {...},    # 图片分析结果缓存
        'qq_config': {...},    # 配置缓存
        'qq_users': {...},     # 用户资料缓存
        'qq_groups': {...},    # 群组信息缓存
        'qq_sessions': {...},  # 会话缓存
    }
    """
    
    # 缓存类型常量
    CACHE_MESSAGES = "qq_messages"
    CACHE_IMAGES = "qq_images"
    CACHE_CONFIG = "qq_config"
    CACHE_USERS = "qq_users"
    CACHE_GROUPS = "qq_groups"
    CACHE_SESSIONS = "qq_sessions"
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """初始化QQ子网缓存管理器
        
        Args:
            config: 缓存配置
        """
        self.config = config or CacheConfig()
        
        # 各个缓存存储
        self._caches: Dict[str, Dict[str, Any]] = {
            self.CACHE_MESSAGES: {},
            self.CACHE_IMAGES: {},
            self.CACHE_CONFIG: {},
            self.CACHE_USERS: {},
            self.CACHE_GROUPS: {},
            self.CACHE_SESSIONS: {},
        }
        
        # 缓存元数据（简单的过期时间跟踪）
        self._metadata: Dict[str, Dict[str, float]] = {
            cache_type: {} for cache_type in self._caches
        }
        
        # 统计信息
        self._stats = {
            cache_type: {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}
            for cache_type in self._caches
        }
        
        logger.info("[QQCache] 缓存管理器初始化完成")
    
    # ==================== 内部方法 ====================
    
    def _is_expired(self, cache_type: str, key: str) -> bool:
        """检查缓存是否过期"""
        if cache_type not in self._metadata:
            return True
        
        metadata = self._metadata[cache_type]
        if key not in metadata:
            return True
        
        import time
        ttl = metadata[key]
        return time.time() > ttl
    
    def _cleanup_expired(self, cache_type: str) -> None:
        """清理过期缓存"""
        import time
        now = time.time()
        
        expired_keys = [
            key for key, ttl in self._metadata[cache_type].items()
            if now > ttl
        ]
        
        for key in expired_keys:
            self._caches[cache_type].pop(key, None)
            self._metadata[cache_type].pop(key, None)
        
        if expired_keys:
            logger.debug(f"[QQCache] 清理 {cache_type} 中的 {len(expired_keys)} 个过期项")
    
    # ==================== 消息缓存方法 ====================
    
    def set_message_history(self, chat_id: int, messages: list) -> None:
        """缓存聊天历史
        
        Args:
            chat_id: 聊天ID
            messages: 消息列表
        """
        import time
        key = f"history:{chat_id}"
        
        self._caches[self.CACHE_MESSAGES][key] = messages
        self._metadata[self.CACHE_MESSAGES][key] = time.time() + self.config.message_ttl
        self._stats[self.CACHE_MESSAGES]["sets"] += 1
        
        logger.debug(f"[QQCache] 消息缓存设置: {key}")
    
    def get_message_history(self, chat_id: int) -> Optional[list]:
        """获取缓存的聊天历史
        
        Args:
            chat_id: 聊天ID
            
        Returns:
            消息列表或None
        """
        key = f"history:{chat_id}"
        
        if self._is_expired(self.CACHE_MESSAGES, key):
            self._stats[self.CACHE_MESSAGES]["misses"] += 1
            return None
        
        messages = self._caches[self.CACHE_MESSAGES].get(key)
        if messages:
            self._stats[self.CACHE_MESSAGES]["hits"] += 1
        else:
            self._stats[self.CACHE_MESSAGES]["misses"] += 1
        
        return messages
    
    def cache_message(self, chat_id: int, message: Dict[str, Any]) -> None:
        """缓存单个消息"""
        import time
        key = f"msg:{chat_id}:{message.get('msg_id')}"
        
        self._caches[self.CACHE_MESSAGES][key] = message
        self._metadata[self.CACHE_MESSAGES][key] = time.time() + self.config.message_ttl
        self._stats[self.CACHE_MESSAGES]["sets"] += 1
    
    # ==================== 图片缓存方法 ====================
    
    def set_image_analysis(self, image_id: str, analysis_result: Dict) -> None:
        """缓存图片分析结果
        
        Args:
            image_id: 图片ID
            analysis_result: 分析结果
        """
        import time
        key = f"analysis:{image_id}"
        
        self._caches[self.CACHE_IMAGES][key] = analysis_result
        self._metadata[self.CACHE_IMAGES][key] = time.time() + self.config.image_ttl
        self._stats[self.CACHE_IMAGES]["sets"] += 1
        
        logger.debug(f"[QQCache] 图片分析缓存设置: {key}")
    
    def get_image_analysis(self, image_id: str) -> Optional[Dict]:
        """获取缓存的图片分析结果
        
        Args:
            image_id: 图片ID
            
        Returns:
            分析结果或None
        """
        key = f"analysis:{image_id}"
        
        if self._is_expired(self.CACHE_IMAGES, key):
            self._stats[self.CACHE_IMAGES]["misses"] += 1
            return None
        
        result = self._caches[self.CACHE_IMAGES].get(key)
        if result:
            self._stats[self.CACHE_IMAGES]["hits"] += 1
        else:
            self._stats[self.CACHE_IMAGES]["misses"] += 1
        
        return result
    
    def set_image_url(self, image_id: str, url: str) -> None:
        """缓存图片URL"""
        import time
        key = f"url:{image_id}"
        
        self._caches[self.CACHE_IMAGES][key] = url
        self._metadata[self.CACHE_IMAGES][key] = time.time() + self.config.image_ttl
        self._stats[self.CACHE_IMAGES]["sets"] += 1
    
    def get_image_url(self, image_id: str) -> Optional[str]:
        """获取缓存的图片URL"""
        key = f"url:{image_id}"
        
        if self._is_expired(self.CACHE_IMAGES, key):
            self._stats[self.CACHE_IMAGES]["misses"] += 1
            return None
        
        url = self._caches[self.CACHE_IMAGES].get(key)
        if url:
            self._stats[self.CACHE_IMAGES]["hits"] += 1
        else:
            self._stats[self.CACHE_IMAGES]["misses"] += 1
        
        return url
    
    # ==================== 配置缓存方法 ====================
    
    def set_config(self, config_key: str, config_value: Dict) -> None:
        """缓存QQ配置
        
        Args:
            config_key: 配置键
            config_value: 配置值
        """
        import time
        key = f"config:{config_key}"
        
        self._caches[self.CACHE_CONFIG][key] = config_value
        self._metadata[self.CACHE_CONFIG][key] = time.time() + self.config.config_ttl
        self._stats[self.CACHE_CONFIG]["sets"] += 1
        
        logger.debug(f"[QQCache] 配置缓存设置: {key}")
    
    def get_config(self, config_key: str) -> Optional[Dict]:
        """获取缓存的QQ配置
        
        Args:
            config_key: 配置键
            
        Returns:
            配置值或None
        """
        key = f"config:{config_key}"
        
        if self._is_expired(self.CACHE_CONFIG, key):
            self._stats[self.CACHE_CONFIG]["misses"] += 1
            return None
        
        config = self._caches[self.CACHE_CONFIG].get(key)
        if config:
            self._stats[self.CACHE_CONFIG]["hits"] += 1
        else:
            self._stats[self.CACHE_CONFIG]["misses"] += 1
        
        return config
    
    def invalidate_config(self, config_key: str) -> None:
        """失效指定的配置缓存"""
        key = f"config:{config_key}"
        self._caches[self.CACHE_CONFIG].pop(key, None)
        self._metadata[self.CACHE_CONFIG].pop(key, None)
        self._stats[self.CACHE_CONFIG]["deletes"] += 1
        logger.debug(f"[QQCache] 配置缓存失效: {key}")
    
    # ==================== 用户缓存方法 ====================
    
    def set_user_profile(self, user_id: int, profile: Dict) -> None:
        """缓存用户资料"""
        import time
        key = f"user:{user_id}"
        
        self._caches[self.CACHE_USERS][key] = profile
        self._metadata[self.CACHE_USERS][key] = time.time() + self.config.user_ttl
        self._stats[self.CACHE_USERS]["sets"] += 1
    
    def get_user_profile(self, user_id: int) -> Optional[Dict]:
        """获取缓存的用户资料"""
        key = f"user:{user_id}"
        
        if self._is_expired(self.CACHE_USERS, key):
            self._stats[self.CACHE_USERS]["misses"] += 1
            return None
        
        profile = self._caches[self.CACHE_USERS].get(key)
        if profile:
            self._stats[self.CACHE_USERS]["hits"] += 1
        else:
            self._stats[self.CACHE_USERS]["misses"] += 1
        
        return profile
    
    # ==================== 群组缓存方法 ====================
    
    def set_group_info(self, group_id: int, group_info: Dict) -> None:
        """缓存群组信息"""
        import time
        key = f"group:{group_id}"
        
        self._caches[self.CACHE_GROUPS][key] = group_info
        self._metadata[self.CACHE_GROUPS][key] = time.time() + self.config.group_ttl
        self._stats[self.CACHE_GROUPS]["sets"] += 1
    
    def get_group_info(self, group_id: int) -> Optional[Dict]:
        """获取缓存的群组信息"""
        key = f"group:{group_id}"
        
        if self._is_expired(self.CACHE_GROUPS, key):
            self._stats[self.CACHE_GROUPS]["misses"] += 1
            return None
        
        group_info = self._caches[self.CACHE_GROUPS].get(key)
        if group_info:
            self._stats[self.CACHE_GROUPS]["hits"] += 1
        else:
            self._stats[self.CACHE_GROUPS]["misses"] += 1
        
        return group_info
    
    # ==================== 会话缓存方法 ====================
    
    def set_session(self, session_id: str, session_data: Dict) -> None:
        """缓存会话数据"""
        import time
        key = f"session:{session_id}"
        
        self._caches[self.CACHE_SESSIONS][key] = session_data
        self._metadata[self.CACHE_SESSIONS][key] = time.time() + self.config.session_ttl
        self._stats[self.CACHE_SESSIONS]["sets"] += 1
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取缓存的会话数据"""
        key = f"session:{session_id}"
        
        if self._is_expired(self.CACHE_SESSIONS, key):
            self._stats[self.CACHE_SESSIONS]["misses"] += 1
            return None
        
        session = self._caches[self.CACHE_SESSIONS].get(key)
        if session:
            self._stats[self.CACHE_SESSIONS]["hits"] += 1
        else:
            self._stats[self.CACHE_SESSIONS]["misses"] += 1
        
        return session
    
    # ==================== 统计和管理方法 ====================
    
    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """获取所有缓存的统计信息"""
        stats = {}
        
        for cache_type, cache_stats in self._stats.items():
            # 计算命中率
            total = cache_stats["hits"] + cache_stats["misses"]
            hit_rate = cache_stats["hits"] / total if total > 0 else 0.0
            
            # 清理已过期的缓存
            self._cleanup_expired(cache_type)
            
            stats[cache_type] = {
                **cache_stats,
                "size": len(self._caches[cache_type]),
                "hit_rate": f"{hit_rate:.2%}",
            }
        
        return stats
    
    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """清理缓存
        
        Args:
            cache_type: 缓存类型，不指定则清理所有
        """
        if cache_type:
            if cache_type in self._caches:
                self._caches[cache_type].clear()
                self._metadata[cache_type].clear()
                logger.info(f"[QQCache] 已清理: {cache_type}")
        else:
            for cache_type in self._caches:
                self._caches[cache_type].clear()
                self._metadata[cache_type].clear()
            logger.info("[QQCache] 所有缓存已清理")
    
    def __repr__(self):
        stats = self.get_stats()
        total_size = sum(s.get("size", 0) for s in stats.values())
        return f"<QQCacheManager: total_size={total_size}, caches={len(self._caches)}>"


# 全局QQ缓存管理器实例
_qq_cache_manager: Optional[QQCacheManager] = None


def get_qq_cache_manager(config: Optional[CacheConfig] = None) -> QQCacheManager:
    """获取QQ子网缓存管理器（单例）
    
    Args:
        config: 缓存配置（仅在首次创建时有效）
        
    Returns:
        QQCacheManager 实例
    """
    global _qq_cache_manager
    if _qq_cache_manager is None:
        _qq_cache_manager = QQCacheManager(config)
    return _qq_cache_manager
