"""
AstrBot Computer Client - 沙盒执行客户端

提供安全的代码和Shell执行环境
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from .config import SandboxConfig

logger = logging.getLogger(__name__)


class ComputerClient:
    """
    沙盒执行客户端

    提供:
    - Shell命令执行
    - Python脚本执行
    - 文件系统操作
    - 浏览器自动化 (可选)
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._workspace: Optional[Path] = None
        self._sessions: Dict[str, Any] = {}

    async def initialize(self):
        """初始化沙盒"""
        if self.config.workspace_path:
            self._workspace = Path(self.config.workspace_path)
        else:
            self._workspace = Path.home() / ".miya" / "sandbox"

        self._workspace.mkdir(parents=True, exist_ok=True)
        logger.info(f"[ComputerClient] 沙盒初始化完成: {self._workspace}")

    async def execute_shell(
        self, command: str, timeout: Optional[int] = None, cwd: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行Shell命令"""
        if not self._check_command_allowed(command):
            return {
                "success": False,
                "error": f"命令被禁止: {command}",
                "stdout": "",
                "stderr": "",
            }

        timeout = timeout or self.config.max_execution_time

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or str(self._workspace),
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "执行超时",
                "stdout": "",
                "stderr": f"命令执行超过{timeout}秒",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "stdout": "", "stderr": str(e)}

    async def execute_python(
        self, script: str, timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """执行Python脚本"""
        timeout = timeout or self.config.max_execution_time

        try:
            result = subprocess.run(
                [self.config.python_env, "-c", script],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self._workspace),
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "执行超时",
                "stdout": "",
                "stderr": f"Python脚本执行超过{timeout}秒",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "stdout": "", "stderr": str(e)}

    async def read_file(self, filepath: str) -> Dict[str, Any]:
        """读取文件"""
        try:
            path = self._resolve_path(filepath)
            if not path.exists():
                return {"success": False, "error": "文件不存在"}

            content = path.read_text(encoding="utf-8")
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def write_file(self, filepath: str, content: str) -> Dict[str, Any]:
        """写入文件"""
        if not self.config.enable_filesystem_write:
            return {"success": False, "error": "文件系统写操作被禁止"}

        try:
            path = self._resolve_path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def edit_file(
        self, filepath: str, old_content: str, new_content: str
    ) -> Dict[str, Any]:
        """编辑文件"""
        if not self.config.enable_filesystem_write:
            return {"success": False, "error": "文件系统写操作被禁止"}

        try:
            path = self._resolve_path(filepath)
            if not path.exists():
                return {"success": False, "error": "文件不存在"}

            content = path.read_text(encoding="utf-8")
            if old_content not in content:
                return {"success": False, "error": "未找到要替换的内容"}

            new_content_full = content.replace(old_content, new_content)
            path.write_text(new_content_full, encoding="utf-8")
            return {"success": True, "path": str(path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_directory(self, path: str = ".") -> Dict[str, Any]:
        """列出目录"""
        try:
            dir_path = self._resolve_path(path)
            if not dir_path.exists():
                return {"success": False, "error": "目录不存在"}

            items = []
            for item in dir_path.iterdir():
                items.append(
                    {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else 0,
                    }
                )
            return {"success": True, "items": items}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _resolve_path(self, filepath: str) -> Path:
        """解析文件路径，防止路径穿越"""
        if self._workspace is None:
            raise RuntimeError("沙盒未初始化")

        resolved = (self._workspace / filepath).resolve()
        if not str(resolved).startswith(str(self._workspace.resolve())):
            raise ValueError("路径穿越被阻止")

        return resolved

    def _check_command_allowed(self, command: str) -> bool:
        """检查命令是否允许"""
        cmd_lower = command.lower().strip()

        for blocked in self.config.blocked_commands:
            if cmd_lower.startswith(blocked):
                return False

        if self.config.allowed_commands:
            return any(
                cmd_lower.startswith(allowed)
                for allowed in self.config.allowed_commands
            )

        return True

    def get_workspace(self) -> Optional[Path]:
        """获取工作区路径"""
        return self._workspace


_computer_client: Optional[ComputerClient] = None


def get_computer_client(config: Optional[SandboxConfig] = None) -> ComputerClient:
    """获取全局ComputerClient实例"""
    global _computer_client
    if _computer_client is None:
        _computer_client = ComputerClient(config)
    return _computer_client
