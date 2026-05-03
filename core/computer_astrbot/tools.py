"""
AstrBot Computer Tools - 沙盒工具集

提供各种沙盒操作的工具接口
"""

from typing import Dict, Any, Optional
from .client import ComputerClient, get_computer_client


class ExecuteShellTool:
    """Shell命令执行工具"""

    name = "execute_shell"
    description = "执行Shell命令并返回结果"

    def __init__(self, client: Optional[ComputerClient] = None):
        self.client = client or get_computer_client()

    async def execute(
        self, command: str, timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        return await self.client.execute_shell(command, timeout)

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的Shell命令"},
                    "timeout": {
                        "type": "integer",
                        "description": "超时时间(秒)，默认120",
                    },
                },
                "required": ["command"],
            },
        }


class PythonTool:
    """Python脚本执行工具"""

    name = "execute_python"
    description = "执行Python代码并返回结果"

    def __init__(self, client: Optional[ComputerClient] = None):
        self.client = client or get_computer_client()

    async def execute(
        self, script: str, timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        return await self.client.execute_python(script, timeout)

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "要执行的Python代码"},
                    "timeout": {
                        "type": "integer",
                        "description": "超时时间(秒)，默认120",
                    },
                },
                "required": ["script"],
            },
        }


class FileReadTool:
    """文件读取工具"""

    name = "file_read"
    description = "读取文件内容"

    def __init__(self, client: Optional[ComputerClient] = None):
        self.client = client or get_computer_client()

    async def execute(self, filepath: str) -> Dict[str, Any]:
        return await self.client.read_file(filepath)

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "要读取的文件路径"}
                },
                "required": ["filepath"],
            },
        }


class FileWriteTool:
    """文件写入工具"""

    name = "file_write"
    description = "写入文件内容"

    def __init__(self, client: Optional[ComputerClient] = None):
        self.client = client or get_computer_client()

    async def execute(self, filepath: str, content: str) -> Dict[str, Any]:
        return await self.client.write_file(filepath, content)

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "要写入的文件路径"},
                    "content": {"type": "string", "description": "要写入的内容"},
                },
                "required": ["filepath", "content"],
            },
        }


class FileEditTool:
    """文件编辑工具"""

    name = "file_edit"
    description = "编辑文件内容 (替换)"

    def __init__(self, client: Optional[ComputerClient] = None):
        self.client = client or get_computer_client()

    async def execute(
        self, filepath: str, old_content: str, new_content: str
    ) -> Dict[str, Any]:
        return await self.client.edit_file(filepath, old_content, new_content)

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "要编辑的文件路径"},
                    "old_content": {"type": "string", "description": "要替换的旧内容"},
                    "new_content": {"type": "string", "description": "新内容"},
                },
                "required": ["filepath", "old_content", "new_content"],
            },
        }


class BrowserExecTool:
    """浏览器自动化工具 (可选)"""

    name = "browser_execute"
    description = "执行浏览器自动化操作"

    def __init__(self, client: Optional[ComputerClient] = None):
        self.client = client or get_computer_client()

    async def execute(
        self, action: str, url: str = "", params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        if not self.client.config.enable_browser:
            return {"success": False, "error": "浏览器自动化未启用"}

        return {"success": False, "error": "浏览器自动化需要配置Bay服务"}

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "操作类型: navigate, click, type, screenshot等",
                    },
                    "url": {"type": "string", "description": "URL地址"},
                    "params": {"type": "object", "description": "其他参数"},
                },
                "required": ["action"],
            },
        }


def get_all_tools(client: Optional[ComputerClient] = None):
    """获取所有工具实例"""
    return [
        ExecuteShellTool(client),
        PythonTool(client),
        FileReadTool(client),
        FileWriteTool(client),
        FileEditTool(client),
        BrowserExecTool(client),
    ]
