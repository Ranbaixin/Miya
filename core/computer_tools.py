"""
计算机工具 - 文件操作、Shell 执行等

参考 AstrBot 的 computer_tools
"""

import asyncio
import logging
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger("miya.computer_tools")


class ComputerTools:
    """计算机工具集"""

    def __init__(self, workspace: str = None) -> None:
        self.workspace = Path(workspace) if workspace else Path.cwd()
        self._allowed_dirs = [self.workspace]

    def add_allowed_dir(self, path: str) -> None:
        """添加允许访问的目录"""
        self._allowed_dirs.append(Path(path))

    def _is_safe_path(self, path: Path) -> bool:
        """检查路径是否安全（在允许目录内）"""
        path = path.resolve()
        for allowed in self._allowed_dirs:
            try:
                path.relative_to(allowed.resolve())
                return True
            except ValueError:
                continue
        return False

    async def read_file(self, path: str) -> str:
        """读取文件"""
        file_path = self.workspace / path
        if not self._is_safe_path(file_path):
            return f"Error: 路径不在允许范围内: {path}"

        try:
            content = file_path.read_text(encoding="utf-8")
            return content[:10000]  # 限制长度
        except Exception as e:
            return f"Error: 读取失败: {e}"

    async def write_file(self, path: str, content: str) -> str:
        """写入文件"""
        file_path = self.workspace / path
        if not self._is_safe_path(file_path.parent):
            return f"Error: 路径不在允许范围内: {path}"

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return f"已写入: {path}"
        except Exception as e:
            return f"Error: 写入失败: {e}"

    async def list_dir(self, path: str = ".") -> str:
        """列出目录"""
        dir_path = self.workspace / path
        if not self._is_safe_path(dir_path):
            return f"Error: 路径不在允许范围内: {path}"

        try:
            items = []
            for item in dir_path.iterdir():
                item_type = "DIR" if item.is_dir() else "FILE"
                size = ""
                if item.is_file():
                    size = f" ({item.stat().st_size} bytes)"
                items.append(f"{item_type}: {item.name}{size}")
            return "\n".join(items) if items else "目录为空"
        except Exception as e:
            return f"Error: 列出失败: {e}"

    async def create_dir(self, path: str) -> str:
        """创建目录"""
        dir_path = self.workspace / path
        if not self._is_safe_path(dir_path):
            return f"Error: 路径不在允许范围内: {path}"

        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return f"已创建目录: {path}"
        except Exception as e:
            return f"Error: 创建失败: {e}"

    async def delete(self, path: str, recursive: bool = False) -> str:
        """删除"""
        target = self.workspace / path
        if not self._is_safe_path(target):
            return f"Error: 路径不在允许范围内: {path}"

        try:
            if target.is_file():
                target.unlink()
                return f"已删除文件: {path}"
            elif target.is_dir():
                if recursive:
                    shutil.rmtree(target)
                    return f"已删除目录: {path}"
                else:
                    return "Error: 目录非空，请使用 recursive=True"
        except Exception as e:
            return f"Error: 删除失败: {e}"

    async def execute_shell(self, command: str, timeout: int = 30) -> str:
        """执行 Shell 命令"""
        try:
            # 简单检查危险命令
            dangerous = ["rm -rf", "del /f", "format", "mkfs"]
            for d in dangerous:
                if d in command:
                    return f"Error: 危险命令被拒绝: {command}"

            result = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    result.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                result.kill()
                return f"Error: 命令超时 ({timeout}s)"

            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""

            if error:
                return f"Error: {error}"
            return output[:5000] if output else "命令执行完成 (无输出)"
        except Exception as e:
            return f"Error: 执行失败: {e}"

    async def execute_python(self, code: str) -> str:
        """执行 Python 代码"""
        try:
            # 使用 exec (注意安全!)
            local_vars = {}
            exec(code, {}, local_vars)
            result = local_vars.get("result", "代码执行完成")
            return str(result)
        except Exception as e:
            return f"Error: {e}"

    async def get_file_info(self, path: str) -> str:
        """获取文件信息"""
        file_path = self.workspace / path
        if not self._is_safe_path(file_path):
            return f"Error: 路径不在允许范围内: {path}"

        try:
            stat = file_path.stat()
            lines = [
                f"路径: {path}",
                f"类型: {'目录' if file_path.is_dir() else '文件'}",
                f"大小: {stat.st_size} bytes",
                f"创建时间: {stat.st_ctime}",
                f"修改时间: {stat.st_mtime}",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Error: 获取失败: {e}"


# 全局实例
_computer_tools: Optional[ComputerTools] = None


def get_computer_tools() -> ComputerTools:
    """获取全局实例"""
    global _computer_tools
    if _computer_tools is None:
        _computer_tools = ComputerTools()
    return _computer_tools


__all__ = [
    "ComputerTools",
    "get_computer_tools",
]
