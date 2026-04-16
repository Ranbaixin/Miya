"""
message_manager 兼容层 - 支持多种调用方式
"""

import logging

logger = logging.getLogger(__name__)


class MessageManager:
    """消息管理器（占位符）"""

    def __init__(self):
        self.messages = []
        logger.info("[MessageManager] 初始化完成")

    def add_message(self, message):
        pass

    def get_messages(self):
        return []

    def load_recent_context(self, *args, **kwargs):
        """加载最近的上下文 - 支持多种调用方式"""
        # 提取参数
        user_id = args[0] if len(args) > 0 else kwargs.get("user_id", "default")
        limit = kwargs.get("limit", kwargs.get("max_messages", 10))
        days = kwargs.get("days", 7)
        max_messages = kwargs.get("max_messages", limit)

        logger.info(
            f"[MessageManager] 加载上下文: user={user_id}, limit={limit}, days={days}"
        )
        return []

    def context_load_days(self, *args, **kwargs):
        """加载最近N天的上下文"""
        days = args[0] if len(args) > 0 else kwargs.get("days", 7)
        max_messages = kwargs.get("max_messages", 10)
        logger.info(f"[MessageManager] 加载: days={days}, max_messages={max_messages}")
        return []


message_manager = MessageManager()
