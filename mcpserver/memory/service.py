#!/usr/bin/env python3
"""
MCP Memory 服务 - 弥娅记忆系统
"""

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict


class MemoryService:
    """MCP Memory 服务 - 持久化记忆存储"""

    def __init__(self):
        self.name = "memory"
        self.description = "记忆存储服务 - 持久化存储关键信息"
        self.version = "1.0.0"
        self._storage_path = Path(".miya/memory")
        self._storage_path.mkdir(parents=True, exist_ok=True)

    async def handle_handoff(self, tool_call: Dict[str, Any]) -> str:
        """处理工具调用"""
        tool_name = tool_call.get("tool_name", "")

        if "store" in tool_name.lower() or "save" in tool_name.lower():
            return await self._store(tool_call)
        elif (
            "recall" in tool_name.lower()
            or "get" in tool_name.lower()
            or "search" in tool_name.lower()
        ):
            return await self._recall(tool_call)
        elif "delete" in tool_name.lower() or "remove" in tool_name.lower():
            return await self._delete(tool_call)
        elif "list" in tool_name.lower():
            return await self._list(tool_call)
        else:
            return json.dumps({"error": f"未知工具: {tool_name}"})

    async def _store(self, tool_call: Dict[str, Any]) -> str:
        """存储记忆"""
        key = tool_call.get("key", "")
        value = tool_call.get("value", "")
        tags = tool_call.get("tags", [])
        category = tool_call.get("category", "general")

        if not key:
            return json.dumps({"error": "缺少 key 参数"})

        memory_id = str(uuid.uuid4())[:8]
        memory = {
            "id": memory_id,
            "key": key,
            "value": value,
            "tags": tags,
            "category": category,
            "timestamp": time.time(),
        }

        file_path = self._storage_path / f"{memory_id}.json"
        file_path.write_text(json.dumps(memory, ensure_ascii=False), encoding="utf-8")

        return json.dumps(
            {
                "success": True,
                "id": memory_id,
                "key": key,
                "message": f"记忆已存储: {key}",
            }
        )

    async def _recall(self, tool_call: Dict[str, Any]) -> str:
        """回忆/检索记忆"""
        query = tool_call.get("query", "")
        key = tool_call.get("key", "")
        memory_id = tool_call.get("id", "")

        memories = []

        if memory_id:
            file_path = self._storage_path / f"{memory_id}.json"
            if file_path.exists():
                memories.append(json.loads(file_path.read_text(encoding="utf-8")))
        elif key:
            for f in self._storage_path.glob("*.json"):
                m = json.loads(f.read_text(encoding="utf-8"))
                if m.get("key") == key:
                    memories.append(m)
        elif query:
            query_lower = query.lower()
            for f in self._storage_path.glob("*.json"):
                m = json.loads(f.read_text(encoding="utf-8"))
                if (
                    query_lower in m.get("key", "").lower()
                    or query_lower in m.get("value", "").lower()
                ):
                    memories.append(m)

        if not memories:
            return json.dumps({"error": "未找到相关记忆"})

        return json.dumps(
            {"success": True, "count": len(memories), "memories": memories[:10]}
        )

    async def _delete(self, tool_call: Dict[str, Any]) -> str:
        """删除记忆"""
        memory_id = tool_call.get("id", "")

        if not memory_id:
            return json.dumps({"error": "缺少 id 参数"})

        file_path = self._storage_path / f"{memory_id}.json"
        if file_path.exists():
            file_path.unlink()
            return json.dumps({"success": True, "message": f"记忆已删除: {memory_id}"})

        return json.dumps({"error": f"记忆不存在: {memory_id}"})

    async def _list(self, tool_call: Dict[str, Any]) -> str:
        """列出所有记忆"""
        category = tool_call.get("category", "")

        memories = []
        for f in self._storage_path.glob("*.json"):
            m = json.loads(f.read_text(encoding="utf-8"))
            if not category or m.get("category") == category:
                memories.append(m)

        return json.dumps(
            {
                "success": True,
                "count": len(memories),
                "memories": sorted(
                    memories, key=lambda x: x.get("timestamp", 0), reverse=True
                )[:20],
            }
        )


service = MemoryService()


if __name__ == "__main__":
    import asyncio

    async def test():
        result = await service.handle_handoff(
            {
                "tool_name": "store",
                "key": "test_key",
                "value": "test_value",
                "category": "test",
            }
        )
        print(result)

    asyncio.run(test())
