"""Skills 热重载系统

借鉴 Undefined 的 skills/registry.py 设计：
- 目录监控 (mtime + size 快照对比)
- debounce 防抖
- 动态模块导入/重载
- 支持 start/stop 生命周期
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import sys
import time
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class HotReloadWatcher:
    """通用热重载目录监控器

    监控指定目录的文件变化，触发 reload 回调。

    用法:
        watcher = HotReloadWatcher(
            watch_dirs=["skills/tools", "skills/agents"],
            on_reload=my_reload_func,
        )
        watcher.start()
        await watcher.stop()
    """

    def __init__(
        self,
        watch_dirs: list[str | Path],
        on_reload: Callable[[], Any],
        interval: float = 2.0,
        debounce: float = 0.5,
        patterns: list[str] | None = None,
    ):
        self.watch_dirs = [Path(d) for d in watch_dirs]
        self._on_reload = on_reload
        self.interval = interval
        self.debounce = debounce
        self.patterns = patterns or ["*.py", "*.json", "*.yaml", "*.yml"]

        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._last_snapshot: dict[str, tuple[int, int]] = {}

    @classmethod
    def from_config(
        cls,
        watch_dirs: list[str | Path],
        on_reload,
    ) -> "HotReloadWatcher":
        from config.config_utils import get_hot_reload_config

        cfg = get_hot_reload_config()

        return cls(
            watch_dirs=watch_dirs,
            on_reload=on_reload,
            interval=cfg.get("interval_seconds", 2.0),
            debounce=cfg.get("debounce_seconds", 0.5),
            patterns=cfg.get("watch_patterns", ["*.py", "*.json", "*.yaml", "*.yml"]),
        )

    def start(self) -> None:
        """启动热重载监控"""
        if self._task:
            return
        self._stop_event.clear()
        self._last_snapshot = self._compute_snapshot()
        self._task = asyncio.create_task(self._watch_loop())
        logger.info(
            "[HotReload] 已启动: dirs=%s interval=%.2fs debounce=%.2fs",
            [str(d) for d in self.watch_dirs],
            self.interval,
            self.debounce,
        )

    async def stop(self, timeout: float | None = 2.0) -> None:
        """停止热重载"""
        if not self._task:
            return
        self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=timeout)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("[HotReload] 已停止")

    def _compute_snapshot(self) -> dict[str, tuple[int, int]]:
        """计算所有监控文件的快照 (路径 → (mtime_ns, size))"""
        snapshot: dict[str, tuple[int, int]] = {}
        for watch_dir in self.watch_dirs:
            if not watch_dir.exists():
                continue
            for pattern in self.patterns:
                for fpath in watch_dir.rglob(pattern):
                    try:
                        stat = fpath.stat()
                        snapshot[str(fpath)] = (
                            int(stat.st_mtime_ns),
                            int(stat.st_size),
                        )
                    except OSError:
                        continue
        return snapshot

    async def _watch_loop(self) -> None:
        last_change = 0.0
        pending = False
        while not self._stop_event.is_set():
            await asyncio.sleep(self.interval)
            snapshot = self._compute_snapshot()
            if snapshot != self._last_snapshot:
                self._last_snapshot = snapshot
                last_change = time.monotonic()
                pending = True
            if pending and (time.monotonic() - last_change) >= self.debounce:
                pending = False
                try:
                    if asyncio.iscoroutinefunction(self._on_reload):
                        await self._on_reload()
                    else:
                        self._on_reload()
                    logger.info("[HotReload] 检测到变更，已重新加载")
                except Exception as e:
                    logger.warning("[HotReload] 重新加载失败: %s", e)


def load_module_from_file(
    module_name: str, file_path: Path, reload: bool = False
) -> Any:
    """从文件动态加载 Python 模块

    Args:
        module_name: 模块名
        file_path: .py 文件路径
        reload: 是否强制重新加载 (清除缓存)

    Returns:
        加载的模块对象
    """
    if reload and module_name in sys.modules:
        del sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def discover_modules(
    base_dir: Path | str,
    pattern: str = "*.py",
    exclude: list[str] | None = None,
) -> list[tuple[str, Path]]:
    """发现目录下的模块文件

    Returns:
        [(module_name, file_path), ...]
    """
    base = Path(base_dir)
    if not base.exists():
        return []

    exclude = exclude or ["__init__.py", "__pycache__"]
    modules: list[tuple[str, Path]] = []

    for fpath in base.glob(pattern):
        if fpath.name in exclude:
            continue
        if fpath.parent != base:
            # 子包: skills.tools.time
            rel = fpath.relative_to(base)
            module_name = f"{base.name}."
            for part in rel.with_suffix("").parts:
                module_name += part + "."
            module_name = module_name.rstrip(".")
        else:
            module_name = fpath.stem
        modules.append((module_name, fpath))

    return modules
