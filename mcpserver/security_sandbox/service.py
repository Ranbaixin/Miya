"""
Security Sandbox MCP Service

提供隔离的 Docker 容器执行环境，用于安全工具运行。
支持 Kali Linux 专用渗透测试镜像和通用 Debian 镜像。
"""

import asyncio
import hashlib
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_PENTEST_IMAGE = "kalilinux/kali-rolling"
DEFAULT_SAFE_IMAGE = "debian:latest"
MAX_TIMEOUT = 300


class SecuritySandboxService:
    """安全沙箱服务"""

    def __init__(self):
        self.name = "security_sandbox"
        self.description = "安全工具 Docker 沙箱执行环境"
        self.version = "1.0.0"
        self._docker_available: Optional[bool] = None
        self._active_containers: Dict[str, Dict[str, Any]] = {}
        self._execution_logs: Dict[str, List[str]] = {}

    async def _check_docker(self) -> bool:
        """检查 Docker 是否可用"""
        if self._docker_available is not None:
            return self._docker_available
        try:
            import aiodocker

            docker = aiodocker.Docker()
            await docker.ping()
            await docker.close()
            self._docker_available = True
            logger.info("Docker 可用")
        except Exception as e:
            self._docker_available = False
            logger.warning(f"Docker 不可用: {e}")
        return self._docker_available

    async def handle_handoff(self, tool_call: Dict[str, Any]) -> str:
        """处理工具调用"""
        tool_name = tool_call.get("tool_name", "")
        args = tool_call.get("arguments", {})

        if tool_name == "security_sandbox_exec":
            return await self._exec_command(args)
        elif tool_name == "security_sandbox_get_logs":
            return await self._get_logs(args)
        elif tool_name == "security_sandbox_list_containers":
            return await self._list_containers(args)
        elif tool_name == "security_sandbox_stop_container":
            return await self._stop_container(args)
        else:
            import json

            return json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)

    async def _exec_command(self, args: Dict[str, Any]) -> str:
        """在 Docker 容器中执行命令"""
        command = args.get("command", "")
        image = args.get("image", DEFAULT_PENTEST_IMAGE)
        timeout = min(args.get("timeout", 120), MAX_TIMEOUT)

        if not command:
            return "请提供要执行的命令"

        if not await self._check_docker():
            return self._fallback_local_exec(command, timeout)

        import aiodocker

        container_id = None
        try:
            docker = aiodocker.Docker()

            # 拉取镜像（如果本地没有）
            try:
                await docker.images.inspect(image)
            except Exception:
                logger.info(f"正在拉取镜像: {image}")
                container_id = f"pull-{datetime.now().timestamp()}"
                self._log(container_id, f"正在拉取 Docker 镜像: {image}...")
                try:
                    await docker.images.pull(image)
                    self._log(container_id, "镜像拉取完成")
                except Exception as e:
                    return (
                        f"拉取 Docker 镜像失败: {str(e)[:200]}\n\n请确保 Docker 已启动，或手动执行: docker pull {image}"
                    )

            # 创建容器
            container = await docker.containers.create(
                config={
                    "Image": image,
                    "Cmd": ["/bin/bash", "-c", command],
                    "HostConfig": {
                        "AutoRemove": True,
                        "Memory": 512 * 1024 * 1024,  # 512MB 限制
                        "NetworkMode": "bridge",
                        "CapDrop": ["ALL"],
                        "CapAdd": ["NET_RAW", "NET_BIND_SERVICE"],
                        "ReadonlyRootfs": False,
                    },
                    "OpenStdin": False,
                }
            )
            container_id = container.id
            self._active_containers[container_id] = {
                "command": command[:100],
                "image": image,
                "started_at": datetime.now().isoformat(),
            }

            # 启动容器
            self._log(container_id, f"执行命令: {command[:200]}")
            await container.start()

            # 等待执行完成
            try:
                result = await container.wait(timeout=timeout)
            except asyncio.TimeoutError:
                self._log(container_id, f"命令超时 ({timeout}s)，正在停止容器")
                try:
                    await container.kill()
                except Exception:
                    pass

            # 获取输出
            logs = await container.log(stdout=True, stderr=True)
            output = "".join(logs)

            # 限制输出长度
            if len(output) > 8000:
                output = output[:4000] + "\n... [输出被截断] ...\n" + output[-4000:]

            self._log(container_id, "命令执行完成")

            await docker.close()

            return (
                f"沙箱执行完成\n"
                f"镜像: {image}\n"
                f"状态码: {result.get('StatusCode', 'N/A')}\n"
                f"{'─' * 40}\n"
                f"{output if output else '(无输出)'}"
            )

        except ImportError:
            return self._fallback_local_exec(command, timeout)
        except Exception as e:
            self._log(container_id or "unknown", f"执行失败: {str(e)[:200]}")
            return f"沙箱执行失败: {str(e)[:300]}"

    def _fallback_local_exec(self, command: str, timeout: int) -> str:
        """Docker 不可用时的回退 — 仅返回提示，不直接执行命令"""
        import platform

        if platform.system() == "Windows":
            return (
                "Docker 未安装或不可用。\n"
                "请安装 Docker Desktop 后重试。\n"
                "下载: https://www.docker.com/products/docker-desktop"
            )

        return (
            "Docker 服务不可用，无法提供沙箱执行环境。\n"
            "请确保 Docker 已安装并运行:\n"
            "  1. 安装 Docker: https://docs.docker.com/get-docker/\n"
            "  2. 启动 Docker 服务: sudo systemctl start docker\n"
            "  3. 验证: docker ps"
        )

    def _log(self, container_id: str, message: str):
        """记录执行日志"""
        if container_id not in self._execution_logs:
            self._execution_logs[container_id] = []
        self._execution_logs[container_id].append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    async def _get_logs(self, args: Dict[str, Any]) -> str:
        """获取容器执行日志"""
        container_id = args.get("container_id", "")
        logs = self._execution_logs.get(container_id, [])
        if not logs:
            return f"未找到容器日志: {container_id}"
        return "\n".join(logs)

    async def _list_containers(self, args: Dict[str, Any]) -> str:
        """列出活跃容器"""
        if not self._active_containers:
            return "当前无活跃容器"
        import json

        return json.dumps(self._active_containers, ensure_ascii=False, indent=2)

    async def _stop_container(self, args: Dict[str, Any]) -> str:
        """停止容器"""
        container_id = args.get("container_id", "")
        if not container_id:
            return "请提供容器ID"

        self._active_containers.pop(container_id, None)
        self._execution_logs.pop(container_id, None)

        if await self._check_docker():
            try:
                import aiodocker

                docker = aiodocker.Docker()
                container = await docker.containers.get(container_id)
                await container.kill()
                await docker.close()
            except Exception:
                pass

        return f"容器已停止: {container_id}"


service = SecuritySandboxService()
