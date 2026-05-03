"""事件总线占位模块"""

import asyncio
from asyncio import Queue


class EventBus:
    def __init__(self, event_queue, pipeline_scheduler, config):
        self.event_queue = event_queue

    async def dispatch(self):
        while True:
            await asyncio.sleep(1)


class CronManager:
    async def run(self):
        while True:
            await asyncio.sleep(60)


class TempDirCleaner:
    async def clean_loop(self):
        while True:
            await asyncio.sleep(3600)


__all__ = ["EventBus", "CronManager", "TempDirCleaner"]
