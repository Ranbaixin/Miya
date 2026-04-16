"""
NagaAgent config_manager 兼容层
"""

import logging

logger = logging.getLogger(__name__)


def update_config(key, value=None):
    """更新配置（空实现）"""
    logger.info(f"[config_manager] update_config: key={key}, value={value}")
    return True


def get_config(key):
    """获取配置"""
    return None
