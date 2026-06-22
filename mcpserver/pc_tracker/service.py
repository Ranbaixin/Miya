"""PC Time Tracker MCP 服务"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("pc_tracker.service")

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    import aiohttp
    HAS_HTTPX = False


class PcTrackerService:
    """PC 时间追踪 MCP 服务"""

    def __init__(self):
        self.name = "pc_tracker"
        self.description = "电脑使用时间追踪数据 — 应用排行、多日趋势、工作习惯"
        self.version = "1.0.0"
        self.base_url = "http://127.0.0.1:8080/api/v1"
        self._available = None  # 延迟检测

    async def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if HAS_HTTPX:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    resp.raise_for_status()
                    return await resp.json()

    async def handle_handoff(self, tool_call: Dict[str, Any]) -> str:
        tool_name = tool_call.get("tool_name", "").lower()
        args = tool_call.get("parameters", tool_call.get("args", {}))

        try:
            if tool_name == "pc_context":
                return await self._handle_context()
            elif tool_name == "pc_daily":
                return await self._handle_daily(args)
            elif tool_name == "pc_processes":
                return await self._handle_processes(args)
            elif tool_name == "pc_current":
                return await self._handle_current()
            elif tool_name == "pc_insights":
                return await self._handle_insights()
            elif tool_name == "pc_status":
                return await self._handle_status()
            else:
                return f"未知的 PC Tracker 工具: {tool_name}"
        except Exception as e:
            logger.warning(f"[PC Tracker] 调用失败 ({tool_name}): {e}")
            return f"PC 时间追踪器不可用: {e}。请确认追踪器是否在运行 (http://127.0.0.1:8080/api/v1/status)"

    async def _handle_context(self) -> str:
        data = await self._get("/agent/context")
        d = data.get("data", {})
        summary = d.get("text_summary", "")
        current = d.get("current_session", {})
        active = current.get("active_window", {})

        parts = [summary]
        if active:
            parts.append(f"\n当前窗口: {active.get('process_name', '?')} — {active.get('window_title', '?')[:80]}")
        return "\n".join(parts)

    async def _handle_daily(self, args: Dict) -> str:
        days = args.get("days", 7)
        data = await self._get(f"/stats/daily?days={days}")
        items = data.get("data", [])
        if not items:
            return "暂无数据"
        lines = [f"最近 {len(items)} 天使用时长:"]
        for d in items:
            h = d.get("total_seconds", 0) / 3600
            lines.append(f"  {d.get('date', '?')}: {h:.1f}h")
        return "\n".join(lines)

    async def _handle_processes(self, args: Dict) -> str:
        date = args.get("date", "today")
        limit = args.get("limit", 10)
        data = await self._get(f"/stats/processes?date={date}&limit={limit}")
        items = data.get("data", [])
        if not items:
            return "暂无数据"
        lines = [f"应用使用排行 ({date}):"]
        for p in items[:limit]:
            h = p.get("total_seconds", 0) / 3600
            pct = p.get("percentage", 0)
            lines.append(f"  {p.get('process_name', '?')}: {h:.1f}h ({pct}%)")
        return "\n".join(lines)

    async def _handle_current(self) -> str:
        data = await self._get("/sessions/current")
        d = data.get("data", {})
        if not d:
            return "无活跃会话"
        elapsed_h = d.get("elapsed_seconds", 0) / 3600
        active = d.get("active_window", {})
        idle = d.get("is_idle", False)
        status = "空闲中" if idle else "活跃"
        return (
            f"当前会话已运行 {elapsed_h:.1f} 小时 ({status})\n"
            f"当前窗口: {active.get('process_name', '?')} — {active.get('window_title', '?')[:80]}"
        )

    async def _handle_insights(self) -> str:
        data = await self._get("/agent/insights")
        d = data.get("data", {})
        if not d:
            return "暂无洞察数据"
        parts = []
        for key, val in d.items():
            if isinstance(val, str):
                parts.append(f"{key}: {val[:200]}")
            elif isinstance(val, (int, float)):
                parts.append(f"{key}: {val}")
        return "\n".join(parts) if parts else "洞察数据为空"

    async def _handle_status(self) -> str:
        data = await self._get("/status")
        d = data.get("data", {})
        running = d.get("tracker_running", False)
        if running:
            return (
                f"PC 时间追踪器运行中\n"
                f"当前进程: {d.get('current_process', '?')}\n"
                f"空闲状态: {d.get('is_idle', False)}\n"
                f"数据库大小: {d.get('database_size_bytes', 0) / 1024:.0f} KB"
            )
        return "PC 时间追踪器未运行"


_pc_tracker_service: Optional[PcTrackerService] = None


def get_pc_tracker_service() -> PcTrackerService:
    global _pc_tracker_service
    if _pc_tracker_service is None:
        _pc_tracker_service = PcTrackerService()
    return _pc_tracker_service
