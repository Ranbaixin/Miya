"""
MIYA Tools 工具系统

内置工具:
- 文件操作
- Shell 命令
- Web 搜索
- Python 执行
- 知识库工具
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==================== Tool 基类 ====================


@dataclass
class ToolResult:
    """工具执行结果"""

    success: bool
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class Tool(ABC):
    """工具基类"""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = None

    def __init__(self):
        self._enabled = True

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        pass

    async def validate_params(self, params: Dict) -> bool:
        """验证参数"""
        return True

    def get_schema(self) -> Dict:
        """获取工具 schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters or {},
        }


# ==================== 文件工具 ====================


class FileReadTool(Tool):
    """读取文件工具"""

    name = "file_read"
    description = "读取文件内容"

    async def execute(self, path: str, encoding: str = "utf-8", **kwargs) -> ToolResult:
        try:
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            return ToolResult(success=True, result=content)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FileWriteTool(Tool):
    """写入文件工具"""

    name = "file_write"
    description = "写入文件内容"

    async def execute(
        self, path: str, content: str, encoding: str = "utf-8", **kwargs
    ) -> ToolResult:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
            return ToolResult(success=True, result=path)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FileListTool(Tool):
    """列出文件工具"""

    name = "file_list"
    description = "列出目录文件"

    async def execute(
        self, path: str = ".", pattern: str = "*", **kwargs
    ) -> ToolResult:
        try:
            from pathlib import Path

            files = list(Path(path).glob(pattern))
            result = [str(f) for f in files]
            return ToolResult(success=True, result=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== Shell 工具 ====================


class ShellTool(Tool):
    """Shell 命令工具"""

    name = "shell"
    description = "执行 Shell 命令"

    async def execute(self, command: str, timeout: int = 30, **kwargs) -> ToolResult:
        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                result = {
                    "stdout": stdout.decode("utf-8") if stdout else "",
                    "stderr": stderr.decode("utf-8") if stderr else "",
                    "returncode": process.returncode,
                }

                return ToolResult(
                    success=process.returncode == 0,
                    result=result,
                    error=stderr.decode("utf-8") if stderr else None,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(success=False, error="命令执行超时")

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== Python 执行工具 ====================


class PythonTool(Tool):
    """Python 代码执行工具"""

    name = "python"
    description = "执行 Python 代码"

    async def execute(self, code: str, **kwargs) -> ToolResult:
        try:
            # 注意：这是一个简化版，实际使用需要沙箱
            result = {"output": "", "error": None}

            # 创建输出捕获
            import sys
            from io import StringIO

            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()

            try:
                exec(code, {"__builtins__": __builtins__})
                result["output"] = sys.stdout.getvalue()
            except Exception as e:
                result["error"] = str(e)
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

            return ToolResult(success=result["error"] is None, result=result)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== Web 搜索工具 ====================


class WebSearchTool(Tool):
    """网页搜索工具"""

    name = "web_search"
    description = "搜索网页"

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.search_engine = config.get("search_engine", "tavily")
        self.api_key = config.get("api_key", "")

    async def execute(self, query: str, num_results: int = 5, **kwargs) -> ToolResult:
        try:
            import httpx

            if self.search_engine == "tavily":
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "query": query,
                            "max_results": num_results,
                            "api_key": self.api_key,
                        },
                    )
                    results = resp.json().get("results", [])
                    return ToolResult(success=True, result=results)

            elif self.search_engine == "ddg":
                # DuckDuckGo 搜索
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        "https://api.duckduckgo.com/",
                        params={"q": query, "format": "json"},
                    )
                    data = resp.json()
                    results = [
                        {"title": r.get("Text"), "url": r.get("URL")}
                        for r in data.get("RelatedTopics", [])
                    ][:num_results]
                    return ToolResult(success=True, result=results)

            else:
                return ToolResult(
                    success=False, error=f"不支持的搜索引擎: {self.search_engine}"
                )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== 知识库工具 ====================


class KnowledgeBaseTool(Tool):
    """知识库查询工具"""

    name = "knowledge_base"
    description = "查询知识库"

    def __init__(self, kb_manager):
        super().__init__()
        self.kb_manager = kb_manager

    async def execute(
        self,
        query: str,
        kb_id: str = "default",
        top_k: int = 5,
        method: str = "hybrid",
        **kwargs,
    ) -> ToolResult:
        try:
            results = await self.kb_manager.query(
                kb_id=kb_id, query=query, top_k=top_k, method=method
            )

            formatted = [
                {"content": r.content, "score": r.score, "metadata": r.metadata}
                for r in results
            ]

            return ToolResult(success=True, result=formatted)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== 工具注册表 ====================


class ToolRegistry:
    """工具注册表"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._tools: Dict[str, Tool] = {}
        self._register_default_tools()
        self._initialized = True

        logger.info("[ToolRegistry] 初始化完成")

    def _register_default_tools(self):
        """注册默认工具"""
        self._tools = {
            "file_read": FileReadTool(),
            "file_write": FileWriteTool(),
            "file_list": FileListTool(),
            "shell": ShellTool(),
            "python": PythonTool(),
            "web_search": WebSearchTool({"search_engine": "ddg"}),
        }

        logger.info(f"[ToolRegistry] 已注册 {len(self._tools)} 个工具")

    def register(self, name: str, tool: Tool):
        """注册工具"""
        self._tools[name] = tool
        logger.info(f"[ToolRegistry] 注册工具: {name}")

    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict]:
        """列出工具"""
        return [
            {"name": name, "description": tool.description, "enabled": tool._enabled}
            for name, tool in self._tools.items()
            if tool._enabled
        ]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """执行工具"""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"工具不存在: {tool_name}")

        if not tool._enabled:
            return ToolResult(success=False, error=f"工具未启用: {tool_name}")

        return await tool.execute(**kwargs)


# 工具定义 (用于 LLM Function Calling)


def get_tools_definition() -> List[Dict]:
    """获取工具定义 (JSON Schema)"""
    ToolRegistry()
    return [
        {
            "type": "function",
            "function": {
                "name": "file_read",
                "description": "读取文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"}
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "file_write",
                "description": "写入文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "content": {"type": "string", "description": "文件内容"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "shell",
                "description": "执行Shell命令",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "要执行的命令"}
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "python",
                "description": "执行Python代码",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Python代码"}
                    },
                    "required": ["code"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "搜索网页",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词"},
                        "num_results": {"type": "integer", "description": "结果数量"},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "knowledge_base",
                "description": "查询知识库",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "查询内容"},
                        "kb_id": {"type": "string", "description": "知识库ID"},
                        "top_k": {"type": "integer", "description": "返回结果数量"},
                    },
                    "required": ["query"],
                },
            },
        },
    ]


# 全局实例
_tool_registry = None


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


__all__ = [
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "get_tool_registry",
    "get_tools_definition",
    # 工具
    "FileReadTool",
    "FileWriteTool",
    "FileListTool",
    "ShellTool",
    "PythonTool",
    "WebSearchTool",
    "KnowledgeBaseTool",
]
