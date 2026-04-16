"""
task_service_manager 兼容层
"""

import logging

logger = logging.getLogger(__name__)


class TaskServiceManager:
    """任务服务管理器（占位符）"""

    def __init__(self):
        self._ui_callback = None
        logger.info("[TaskServiceManager] 初始化完成")

    def set_ui_message_callback(self, callback):
        """设置 UI 消息回调"""
        self._ui_callback = callback
        logger.info("[TaskServiceManager] UI回调已设置")

    def record_interaction(self):
        """记录交互时间"""
        pass


def get_task_service_manager():
    """获取任务服务管理器"""
    return TaskServiceManager()
