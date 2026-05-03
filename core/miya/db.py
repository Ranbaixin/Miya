"""
数据库管理器 - Database
"""

import logging

logger = logging.getLogger("miya.db")


class Database:
    """数据库"""

    def __init__(self) -> None:
        self._conn = None

    async def initialize(self) -> None:
        """初始化"""
        logger.info("[Database] 初始化 SQLite 数据库")


_database: any = None


def get_database() -> Database:
    global _database
    if _database is None:
        _database = Database()
    return _database


__all__ = ["Database", "get_database"]
