"""
工具系统标准化模块

统一 ToolNet、Computer工具和Skills的接口
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """工具定义"""

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    category: str = "general"
    source: str = "unknown"


class UnifiedToolRegistry:
    """
    统一工具注册表

    功能：
    - 统一工具入口
    - 工具分类管理
    - 智能路由
    """

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._categories: Dict[str, List[str]] = {}
        self._initialized = False

    async def initialize(self):
        """初始化统一工具系统"""
        logger.info("[UnifiedToolRegistry] 初始化...")

        await self._register_toolnet_tools()
        await self._register_computer_tools()
        await self._register_skill_tools()

        self._initialized = True
        logger.info(f"[UnifiedToolRegistry] 初始化完成，共 {len(self._tools)} 个工具")

    async def _register_toolnet_tools(self):
        """注册ToolNet工具"""
        try:
            from webnet.ToolNet.registry import get_tool_registry

            tool_registry = get_tool_registry()
            if tool_registry and hasattr(tool_registry, "get_tools_schema"):
                tools = tool_registry.get_tools_schema()
                for tool in tools:
                    self._register_tool(
                        name=tool.get("name", ""),
                        description=tool.get("description", ""),
                        parameters=tool.get("parameters", {}),
                        category="toolnet",
                        source="ToolNet",
                    )
                logger.info(f"[UnifiedToolRegistry] 已注册 {len(tools)} 个ToolNet工具")
        except Exception as e:
            logger.warning(f"[UnifiedToolRegistry] ToolNet工具注册失败: {e}")

    async def _register_computer_tools(self):
        """注册Computer工具"""
        try:
            from core.computer_astrbot.tools import get_all_tools

            tools = get_all_tools()
            for tool in tools:
                schema = tool.to_schema()
                self._register_tool(
                    name=schema.get("name", ""),
                    description=schema.get("description", ""),
                    parameters=schema.get("parameters", {}),
                    category="computer",
                    source="Computer",
                )
            logger.info(f"[UnifiedToolRegistry] 已注册 {len(tools)} 个Computer工具")
        except Exception as e:
            logger.warning(f"[UnifiedToolRegistry] Computer工具注册失败: {e}")

    async def _register_skill_tools(self):
        """注册Skill工具"""
        try:
            from core.skills.registry import get_skills_registry

            skills_registry = get_skills_registry()
            if skills_registry and hasattr(skills_registry, "list_skills"):
                skills = skills_registry.list_skills()
                for skill in skills:
                    self._register_tool(
                        name=f"skill_{skill.get('name', '')}",
                        description=skill.get("description", ""),
                        parameters={},
                        category="skill",
                        source="Skills",
                    )
                logger.info(f"[UnifiedToolRegistry] 已注册 {len(skills)} 个Skill工具")
        except Exception as e:
            logger.warning(f"[UnifiedToolRegistry] Skill工具注册失败: {e}")

    def _register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        category: str,
        source: str,
    ):
        """注册单个工具"""
        if not name:
            return

        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "category": category,
            "source": source,
        }

        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行工具"""
        if tool_name not in self._tools:
            return {"success": False, "error": f"工具不存在: {tool_name}"}

        tool_info = self._tools[tool_name]
        category = tool_info.get("category")

        try:
            if category == "computer":
                return await self._execute_computer(tool_name, arguments)
            elif category == "skill":
                return await self._execute_skill(tool_name, arguments, context)
            elif category == "toolnet":
                return await self._execute_toolnet(tool_name, arguments, context)
            else:
                return {"success": False, "error": "未知工具类型"}
        except Exception as e:
            logger.error(f"[UnifiedToolRegistry] 工具执行失败: {e}")
            return {"success": False, "error": str(e)}

    async def _execute_computer(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行Computer工具"""
        try:
            from core.computer_astrbot.client import get_computer_client

            client = get_computer_client()

            if tool_name == "execute_shell":
                return await client.execute_shell(arguments.get("command", ""))
            elif tool_name == "execute_python":
                return await client.execute_python(arguments.get("script", ""))
            elif tool_name == "file_read":
                return await client.read_file(arguments.get("filepath", ""))
            elif tool_name == "file_write":
                return await client.write_file(
                    arguments.get("filepath", ""), arguments.get("content", "")
                )

            return {"success": False, "error": f"未知Computer工具: {tool_name}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_skill(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """执行Skill工具"""
        return {"success": True, "message": "Skill执行功能待实现"}

    async def _execute_toolnet(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """执行ToolNet工具"""
        return {"success": True, "message": "ToolNet执行功能待实现"}

    def list_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出工具"""
        if category:
            tool_names = self._categories.get(category, [])
            return [self._tools[name] for name in tool_names]

        return list(self._tools.values())

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具schema"""
        return self._tools.get(tool_name)

    def get_categories(self) -> List[str]:
        """获取工具分类"""
        return list(self._categories.keys())


_unified_tool_registry: Optional[UnifiedToolRegistry] = None


def get_unified_tool_registry() -> UnifiedToolRegistry:
    """获取全局统一工具注册表"""
    global _unified_tool_registry
    if _unified_tool_registry is None:
        _unified_tool_registry = UnifiedToolRegistry()
    return _unified_tool_registry
