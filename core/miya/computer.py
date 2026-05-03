"""
计算机工具 - Computer
"""

import logging

logger = logging.getLogger("miya.computer")


class Computer:
    """计算机工具"""

    def __init__(self) -> None:
        self._allowed_dirs = []

    async def initialize(self) -> None:
        """初始化"""
        logger.info("[Computer] 初始化计算机工具")

    async def execute(self, code: str) -> str:
        """执行代码"""
        return "执行功能预留"


_computer: any = None


def get_computer() -> Computer:
    global _computer
    if _computer is None:
        _computer = Computer()
    return _computer


__all__ = ["Computer", "get_computer"]
