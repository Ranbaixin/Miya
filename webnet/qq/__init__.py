"""
QQ交互子网模块包
拆分超大文件 qq.py (55.7KB) 为模块化结构

结构:
- __init__.py: 主导出接口
- models.py: 数据模型 (QQMessage, QQNotice)
- client.py: QQOneBotClient WebSocket客户端
- core.py: QQNet 核心子网逻辑
- message_handler.py: 消息处理逻辑
- tts_handler.py: TTS语音处理
- cache_manager.py: 缓存管理器（新增）
- utils.py: 工具函数
"""

from .cache_manager import CacheConfig, QQCacheManager, get_qq_cache_manager
from .client import QQOneBotClient
from .core import QQNet
from .message_handler import QQMessageHandler
from .models import QQMessage, QQNotice
from .tts_handler import QQTTsHandler

__all__ = [
    'QQMessage',
    'QQNotice',
    'QQOneBotClient',
    'QQNet',
    'QQMessageHandler',
    'QQTTsHandler',
    'QQCacheManager',
    'get_qq_cache_manager',
    'CacheConfig',
]
