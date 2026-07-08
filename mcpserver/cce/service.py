#!/usr/bin/env python3
"""
CCE MCP 服务 — 弥娅的「手」/肢体工具

通过 Claude Code Engine 执行文件操作、Bash、代码生成等任务。
CCE 是通过反编译调试获得的 Node.js CLI 工具，拥有 60+ 内置工具。
"""

import json
import logging
import platform
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("mcpserver.cce")

MIYA_ROOT = Path(__file__).parent.parent.parent


class CCEService:
    """CCE 执行引擎 MCP 服务"""

    def __init__(self):
        self.name = "cce"
        self.description = "CCE 执行引擎 — 弥娅的手/肢体工具"
        self.version = "1.0.0"
        self._cli_path: Path | None = None
        self._node_exe: str = "node"
        self._init_executor()

    def _init_executor(self):
        cce_dir = MIYA_ROOT / "claude-code-engine"
        cli_candidates = [
            cce_dir / "dist" / "cli-node.js",
            cce_dir / "cli-node.js",
        ]
        for candidate in cli_candidates:
            if candidate.exists():
                self._cli_path = candidate
                break

        node_candidates: list[str] = []
        if platform.system() == "Windows":
            node_candidates = [
                shutil.which("node") or "",
                str(
                    Path.home() / "AppData" / "Roaming" / "fnm" / "node-versions" / "v22" / "installation" / "node.exe"
                ),
                "C:\\Program Files\\nodejs\\node.exe",
            ]
        else:
            node_candidates = [
                shutil.which("node") or "",
                "/usr/local/bin/node",
                "/usr/bin/node",
            ]

        for candidate in node_candidates:
            if candidate and Path(candidate).exists():
                self._node_exe = candidate
                break

        if self._cli_path:
            logger.info(f"[CCE] 执行器就绪: {self._node_exe} {self._cli_path.name}")
        else:
            logger.warning("[CCE] 未找到 cli-node.js")

    @property
    def is_available(self) -> bool:
        return self._cli_path is not None and self._cli_path.exists()

    def _load_env_vars(self) -> dict[str, str]:
        dotenv_path = MIYA_ROOT / "config" / ".env"
        env_vars: dict[str, str] = {}
        if dotenv_path.exists():
            for line in dotenv_path.read_text(encoding="utf-8").split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip()
        return env_vars

    def _get_model_env(self) -> dict[str, str]:
        """从 ModelPoolManager 获取活跃模型配置，回退到 system_defaults，再回退 .env"""
        try:
            from core.model_pool_manager import get_model_pool, resolve_api_key_by_provider

            pool = get_model_pool()
            active_model = pool.select_model("simple_chat")
            if active_model and active_model.base_url:
                api_key = resolve_api_key_by_provider(
                    active_model.provider,
                    getattr(active_model, "env_key", ""),
                )
                return {
                    "api_key": api_key,
                    "base_url": active_model.base_url,
                    "model": active_model.name,
                }

            system_defaults = pool._config.get("system_defaults", {})
            default_model_id = system_defaults.get("default_model", "")
            if default_model_id:
                model = pool.get_model(default_model_id)
                if model and model.enabled:
                    api_key = resolve_api_key_by_provider(
                        model.provider,
                        getattr(model, "env_key", ""),
                    )
                    return {
                        "api_key": api_key,
                        "base_url": model.base_url,
                        "model": model.name,
                    }
        except Exception as e:
            logger.debug(f"[CCE] ModelPoolManager 获取模型失败，回退 .env: {e}")

        env_vars = self._load_env_vars()
        return {
            "api_key": env_vars.get("DEEPSEEK_API_KEY", ""),
            "base_url": env_vars.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"),
            "model": env_vars.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        }

    async def handle_handoff(self, tool_call: dict) -> str:
        tool_name = tool_call.get("tool_name", "")

        if tool_name == "execute":
            return await self._execute(tool_call)
        elif tool_name == "get_status":
            return self._get_status()
        else:
            return json.dumps({"success": False, "error": f"未知工具: {tool_name}"})

    async def _execute(self, tool_call: dict) -> str:
        task = tool_call.get("task", "")
        working_dir = tool_call.get("working_dir", str(MIYA_ROOT))
        timeout = int(tool_call.get("timeout", 120))

        if not task:
            return json.dumps({"success": False, "error": "缺少 task 参数"})

        if not self.is_available:
            return json.dumps(
                {"success": False, "error": "CCE CLI 未就绪，请确认 claude-code-engine/dist/cli-node.js 存在"}
            )

        model_env = self._get_model_env()
        env = {
            **{k: v for k, v in os.environ.items()},
            "CLAUDE_CODE_USE_OPENAI": "1",
            "OPENAI_API_KEY": model_env["api_key"],
            "OPENAI_BASE_URL": model_env["base_url"],
            "OPENAI_MODEL": model_env["model"],
        }

        try:
            creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0

            logger.info(f"[CCE] 执行任务: {task[:80]}...")
            proc = subprocess.run(
                [self._node_exe, str(self._cli_path), "-p", "--permission-mode", "bypassPermissions", task],
                cwd=working_dir,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                creationflags=creationflags,
            )

            return json.dumps(
                {
                    "success": proc.returncode == 0,
                    "output": proc.stdout,
                    "error": proc.stderr,
                    "exit_code": proc.returncode,
                }
            )
        except subprocess.TimeoutExpired:
            return json.dumps({"success": False, "error": f"CCE 执行超时 ({timeout}s)"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _get_status(self) -> str:
        return json.dumps(
            {
                "name": self.name,
                "version": self.version,
                "description": self.description,
                "available": self.is_available,
                "cli_path": str(self._cli_path) if self._cli_path else None,
                "node_exe": self._node_exe,
            }
        )


service = CCEService()


if __name__ == "__main__":
    import asyncio

    async def test():
        print(f"CCE 服务状态: {service._get_status()}")
        if service.is_available:
            result = await service._execute(
                {
                    "task": "在当前目录用 ls 列出前5个文件",
                    "working_dir": str(MIYA_ROOT),
                    "timeout": 30,
                }
            )
            print(f"测试执行结果: {result[:200]}")

    asyncio.run(test())
