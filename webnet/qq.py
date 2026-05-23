"""
QQ交互子网 - 向后兼容层

该文件保留用于向后兼容，实际实现已迁移到 webnet/qq/ 目录

新结构:
- webnet/qq/__init__.py - 主导出接口
- webnet/qq/models.py - 数据模型 (QQMessage, QQNotice)
- webnet/qq/client.py - QQOneBotClient WebSocket客户端
- webnet/qq/core.py - QQNet 核心子网逻辑
- webnet/qq/message_handler.py - 消息处理逻辑
- webnet/qq/tts_handler.py - TTS语音处理
- webnet/qq/utils.py - 工具函数

向后兼容: 所有旧的导入仍然有效:
- from webnet.qq import QQNet, QQOneBotClient, QQMessage, QQNotice
"""

# 从新模块导入所有公开接口
from webnet.qq import (
    QQMessage,
    QQNet,
    QQNotice,
    QQOneBotClient,
)

# 导出所有公开接口
__all__ = [
    'QQMessage',
    'QQNotice',
    'QQOneBotClient',
    'QQNet',
]
