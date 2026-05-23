#!/usr/bin/env python3
"""
OpenClaw Gateway 运行时管理

启动模式（按优先级）:
  1. OPENCLAW_VENDOR_PATH 环境变量 → 直接用娜迦 vendor 源码（node + tsx）
  2. 全局 openclaw 命令: `openclaw gateway`
  3. npx 命令: `npx openclaw gateway`
"""

import asyncio
import logging
import os
import platform
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Optional

from .config_bridge import (
    DEFAULT_GATEWAY_PORT,
    OPENCLAW_CONFIG_FILE,
    OPENCLAW_STATE_DIR,
    ensure_openclaw_config,
    inject_miya_llm_config,
)

logger = logging.getLogger("openclaw.runtime")

IS_WINDOWS = platform.system() == "Windows"
_MIYA_SERVICE_DIR = Path(__file__).resolve().parent


def _find_tsx_loader() -> Optional[str]:
    """查找 tsx ESM loader 路径"""
    # 1. 全局 npm root
    for root_cmd in ["npm root -g", "npm root"]:
        try:
            result = subprocess.run(
                root_cmd.split(), capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                npm_root = result.stdout.strip()
                loader = Path(npm_root) / "tsx" / "dist" / "loader.mjs"
                if loader.exists():
                    return str(loader)
        except Exception:
            pass

    # 2. Windows 常见路径
    for base in [
        Path.home() / "AppData" / "Roaming" / "npm" / "node_modules",
        Path.home() / ".npm-global" / "node_modules",
    ]:
        loader = base / "tsx" / "dist" / "loader.mjs"
        if loader.exists():
            return str(loader)

    # 3. 如果在 PATH 里找到 tsx 命令，推断 loader 路径
    tsx_bin = shutil.which("tsx")
    if tsx_bin:
        bin_dir = Path(tsx_bin).parent
        # tsx 的 bin 通常在 npm/node_modules/.bin/tsx
        npm_root = bin_dir.parent / "node_modules"
        loader = npm_root / "tsx" / "dist" / "loader.mjs"
        if loader.exists():
            return str(loader)

    return None


def _find_vendor_root() -> Optional[Path]:
    """查找 vendor/openclaw 目录"""
    # 1. 环境变量覆盖
    env_path = os.getenv("OPENCLAW_VENDOR_PATH", "").strip()
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    # 2. 弥娅自带的 vendor
    miya_vendor = _MIYA_SERVICE_DIR.parent.parent / "vendor" / "openclaw"
    if miya_vendor.exists():
        return miya_vendor

    # 3. 娜迦（兼容旧环境）
    naga_vendor = Path("D:/AI_MIYA_Facyory/NagaAgent/vendor/openclaw")
    if naga_vendor.exists():
        return naga_vendor

    return None


def _find_openclaw_command() -> Optional[str]:
    """
    查找可用的 openclaw 启动方式。

    优先用 vendor（无需安装任何东西），其次全局命令。

    Returns:
        命令标识: "vendor" | "openclaw" | "npx openclaw" | None
    """
    # vendor 优先
    if _find_vendor_root():
        return "vendor"

    # 全局 openclaw
    cmd = shutil.which("openclaw")
    if cmd:
        return "openclaw"

    if IS_WINDOWS:
        for p in [
            Path.home() / "AppData" / "Roaming" / "npm" / "openclaw.cmd",
            Path.home() / "AppData" / "Roaming" / "npm" / "openclaw",
        ]:
            if p.exists():
                return "openclaw"

    if shutil.which("npx"):
        return "npx openclaw"

    return None


def _check_port_available(port: int) -> bool:
    """检查端口是否可用"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.close()
        return True
    except OSError:
        return False


class OpenClawRuntime:
    """OpenClaw Gateway 运行时管理器"""

    def __init__(self, port: int = DEFAULT_GATEWAY_PORT):
        self._port = port
        self._process: Optional[asyncio.subprocess.Process] = None
        self._mode: Optional[str] = None
        self._ready = False
        self._startup_logs: list[str] = []

    # ===== 属性 =====

    @property
    def port(self) -> int:
        return self._port

    @property
    def is_running(self) -> bool:
        if self._process is None:
            return False
        return self._process.returncode is None

    @property
    def is_available(self) -> bool:
        return _find_openclaw_command() is not None

    @property
    def gateway_url(self) -> str:
        return f"http://127.0.0.1:{self._port}"

    # ===== Gateway 操作 =====

    async def start(self) -> bool:
        if self.is_running:
            logger.warning("[OpenClaw] Gateway 已在运行中")
            return True

        self._mode = _find_openclaw_command()
        if not self._mode:
            logger.error(
                "[OpenClaw] 未找到 openclaw。可用方案:\n"
                "  1. set OPENCLAW_VENDOR_PATH=D:\\...\\NagaAgent\\vendor\\openclaw (推荐)\n"
                "  2. npm install -g openclaw tsx"
            )
            return False

        if not _check_port_available(self._port):
            logger.error(f"[OpenClaw] 端口 {self._port} 已被占用")
            return False

        if not ensure_openclaw_config(self._port):
            return False
        if not inject_miya_llm_config():
            logger.warning("[OpenClaw] 模型配置注入失败")

        try:
            await self._launch_gateway()
            logger.info(
                f"[OpenClaw] Gateway 已启动 (mode={self._mode}, port={self._port})"
            )
            return True
        except Exception as e:
            logger.error(f"[OpenClaw] 启动失败: {e}")
            return False

    async def stop(self, timeout: float = 10.0) -> bool:
        if not self._process or self._process.returncode is not None:
            self._process = None
            self._ready = False
            return True

        try:
            proc = self._process
            self._process = None
            self._ready = False
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            logger.info("[OpenClaw] Gateway 已停止")
            return True
        except Exception as e:
            logger.error(f"[OpenClaw] 停止失败: {e}")
            return False

    async def restart(self) -> bool:
        await self.stop()
        await asyncio.sleep(1)
        return await self.start()

    async def get_status(self) -> dict:
        return {
            "running": self.is_running,
            "command_available": self.is_available,
            "mode": self._mode,
            "port": self._port,
            "gateway_url": self.gateway_url,
            "config_ready": OPENCLAW_CONFIG_FILE.exists(),
            "data_dir": str(OPENCLAW_STATE_DIR),
            "port_available": _check_port_available(self._port)
            if not self.is_running
            else None,
        }

    # ===== 内部方法 =====

    async def _launch_gateway(self) -> None:
        self._startup_logs.clear()

        env = os.environ.copy()
        env["OPENCLAW_STATE_DIR"] = str(OPENCLAW_STATE_DIR)
        env["OPENCLAW_CONFIG_PATH"] = str(OPENCLAW_CONFIG_FILE)
        env["OPENCLAW_GATEWAY_PORT"] = str(self._port)
        env["NO_PROXY"] = env.get("NO_PROXY", "") + ",127.0.0.1,localhost"

        if self._mode == "vendor":
            await self._launch_vendor(env)
        else:
            await self._launch_cli(env)

        # 异步读日志
        if self._process:
            asyncio.create_task(self._read_stream(self._process.stdout))
            asyncio.create_task(self._read_stream(self._process.stderr))

        await self._wait_ready()

    async def _launch_vendor(self, env: dict) -> None:
        """vendor 模式: node gateway_start.mjs"""
        vendor_root = _find_vendor_root()
        if not vendor_root:
            raise FileNotFoundError("未找到 vendor/openclaw 目录")

        gateway_mjs = _MIYA_SERVICE_DIR / "gateway_start.mjs"
        source_reg = _MIYA_SERVICE_DIR / "source_register.mjs"

        if not gateway_mjs.exists():
            raise FileNotFoundError(f"gateway_start.mjs 不存在: {gateway_mjs}")
        if not source_reg.exists():
            raise FileNotFoundError(f"source_register.mjs 不存在: {source_reg}")

        env["OPENCLAW_GATEWAY_VENDOR_ROOT"] = str(vendor_root)

        # Windows: --import 需要 file:// URL，但主脚本参数用普通路径
        reg_url = source_reg.as_uri() if IS_WINDOWS else str(source_reg)
        tsx_loader = _find_tsx_loader()
        if tsx_loader:
            tsx_url = Path(tsx_loader).as_uri() if IS_WINDOWS else tsx_loader
            cmd_parts = [
                "node",
                "--import",
                reg_url,
                "--import",
                tsx_url,
                str(gateway_mjs),
            ]
        else:
            logger.warning("[OpenClaw] tsx 未找到，使用 --experimental-strip-types")
            cmd_parts = [
                "node",
                "--experimental-strip-types",
                "--import",
                reg_url,
                str(gateway_mjs),
            ]
        # OPENCLAW_GATEWAY_VENDOR_ROOT 已在上方设为纯路径，不再覆盖

        self._process = await asyncio.create_subprocess_exec(
            *cmd_parts,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def _launch_cli(self, env: dict) -> None:
        """CLI 模式: openclaw gateway 或 npx openclaw gateway"""
        if self._mode == "npx openclaw":
            self._process = await asyncio.create_subprocess_exec(
                "npx",
                "openclaw",
                "gateway",
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            self._process = await asyncio.create_subprocess_exec(
                "openclaw",
                "gateway",
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

    async def _read_stream(self, stream):
        try:
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    self._startup_logs.append(text)
                    logger.debug(f"[OpenClaw GW] {text}")
        except Exception:
            pass

    async def _wait_ready(self, max_retries: int = 30, interval: float = 1.0):
        for _i in range(max_retries):
            if self._process and self._process.returncode is not None:
                stderr_text = ""
                try:
                    stderr_data = await self._process.stderr.read()
                    stderr_text = stderr_data.decode("utf-8", errors="replace")
                except Exception:
                    pass
                raise RuntimeError(
                    f"Gateway 进程意外退出 (code={self._process.returncode})\n"
                    f"日志:\n{chr(10).join(self._startup_logs[-20:])}\n"
                    f"错误:\n{stderr_text}"
                )

            if not _check_port_available(self._port):
                self._ready = True
                logger.info(f"[OpenClaw] Gateway 就绪 (端口 {self._port} 已监听)")
                return

            await asyncio.sleep(interval)

        raise TimeoutError(
            f"Gateway 启动超时 ({max_retries * interval}s)\n"
            f"日志:\n{chr(10).join(self._startup_logs[-30:])}"
        )


# 全局单例
_runtime_instance: Optional[OpenClawRuntime] = None


def get_runtime(port: int = DEFAULT_GATEWAY_PORT) -> OpenClawRuntime:
    global _runtime_instance
    if _runtime_instance is None:
        _runtime_instance = OpenClawRuntime(port=port)
    return _runtime_instance
