"""Kali Docker 沙箱连接模块

当弥娅运行在没有安全工具的平台上时，
自动通过 Docker 容器中的 Kali 来执行工具命令。

配置：
    MIYA_KALI_CONTAINER = "miya-kali"  (容器名)
    MIYA_KALI_WORKDIR  = "/workspace"  (容器内工作目录)
"""

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

KALI_CONTAINER = os.environ.get("MIYA_KALI_CONTAINER", "miya-kali")
KALI_WORKDIR = os.environ.get("MIYA_KALI_WORKDIR", "/workspace")
FALLBACK_TIMEOUT = int(os.environ.get("KALI_CMD_TIMEOUT", "300"))

# 当工具不可用时直接使用 Docker 执行
DOCKER_MODE = os.environ.get("MIYA_USE_KALI_DOCKER", "auto")  # auto / always / never


def is_docker_available() -> bool:
    """检查 Docker 是否可用"""
    return shutil.which("docker") is not None


def is_container_running(name: str = KALI_CONTAINER) -> bool:
    """检查 Kali 容器是否在运行"""
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name], capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == "true"
    except Exception:
        return False


def docker_exec_sync(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = FALLBACK_TIMEOUT,
) -> Dict[str, Any]:
    """在 Kali Docker 容器中同步执行命令

    Returns:
        {success, stdout, stderr, command, error}
    """
    if not is_docker_available():
        return {"success": False, "error": "Docker 不可用", "command": command}

    if not is_container_running():
        return {"success": False, "error": f"Kali 容器未运行: {KALI_CONTAINER}", "command": command}

    # 处理特殊字符
    safe_cmd = command.replace("\\", "\\\\").replace('"', '\\"')

    docker_cmd = [
        "docker",
        "exec",
        "-w",
        cwd or KALI_WORKDIR,
        KALI_CONTAINER,
        "bash",
        "-c",
        safe_cmd,
    ]

    try:
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0 or bool(result.stdout.strip()),
            "stdout": result.stdout[:50000],
            "stderr": result.stderr[:10000],
            "returncode": result.returncode,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"命令超时 ({timeout}s)", "command": command}
    except Exception as e:
        return {"success": False, "error": str(e), "command": command}


async def docker_exec_async(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = FALLBACK_TIMEOUT,
) -> Dict[str, Any]:
    """在 Kali Docker 容器中异步执行命令"""
    if not is_docker_available():
        return {"success": False, "error": "Docker 不可用", "command": command}

    if not is_container_running():
        return {"success": False, "error": f"Kali 容器未运行: {KALI_CONTAINER}", "command": command}

    safe_cmd = command.replace("\\", "\\\\").replace('"', '\\"')
    docker_cmd = [
        "docker",
        "exec",
        "-w",
        cwd or KALI_WORKDIR,
        KALI_CONTAINER,
        "bash",
        "-c",
        safe_cmd,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            "success": proc.returncode == 0 or bool(stdout.decode(errors="replace").strip()),
            "stdout": stdout.decode("utf-8", errors="replace")[:50000],
            "stderr": stderr.decode("utf-8", errors="replace")[:10000],
            "returncode": proc.returncode,
            "command": command,
        }
    except asyncio.TimeoutError:
        return {"success": False, "error": f"命令超时 ({timeout}s)", "command": command}
    except Exception as e:
        return {"success": False, "error": str(e), "command": command}


def ensure_kali_container() -> Dict[str, Any]:
    """确保 Kali 容器在运行，如未启动则尝试启动或构建"""
    if not is_docker_available():
        return {"success": False, "error": "Docker 未安装"}

    if is_container_running():
        return {"success": True, "message": f"Kali 容器已在运行: {KALI_CONTAINER}"}

    # 检查容器是否存在（可能只是停止了）
    try:
        result = subprocess.run(["docker", "inspect", KALI_CONTAINER], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # 容器存在，启动它
            subprocess.run(["docker", "start", KALI_CONTAINER], capture_output=True, timeout=10)
            return {"success": True, "message": f"Kali 容器已启动: {KALI_CONTAINER}"}
    except Exception as __e:
        logger.debug(f"[kali_sandbox] Docker检查失败: {__e}")

    # 容器不存在，需要构建
    return {
        "success": False,
        "error": f"Kali 容器不存在。请先构建:\n  docker build -t miya-kali -f Dockerfile.kali .\n  docker run -d --name {KALI_CONTAINER} miya-kali tail -f /dev/null",
    }
