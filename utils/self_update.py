"""Git 自更新机制

借鉴 Undefined 的 utils/self_update.py 设计：
- 策略驱动: 验证 origin、分支、clean worktree
- 保守更新: 只允许 fast-forward merge
- uv sync 自动触发
- 文件锁防并发
- os.execv 进程重启
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.file_lock import FileLock

logger = logging.getLogger(__name__)


@dataclass
class GitUpdatePolicy:
    """Git 更新策略"""

    repo_dir: Path  # 仓库根目录
    allowed_origin_base: str = ""  # 允许的 origin URL 前缀，空=不限制
    allowed_branch: str = ""  # 允许的分支，空=当前分支
    require_clean_worktree: bool = True
    lock_path: Path | None = None  # 文件锁路径
    timeout_seconds: float = 60.0
    uv_sync_enabled: bool = True  # 是否自动 uv sync
    module_for_restart: str = ""  # 重启目标模块 (python -m xxx)


@dataclass
class GitUpdateResult:
    """更新结果"""

    success: bool
    updated: bool  # 是否有实际的更新
    from_commit: str = ""
    to_commit: str = ""
    error: str = ""
    files_changed: list[str] | None = None


class SelfUpdater:
    """Git 自更新管理器

    用法:
        updater = SelfUpdater(GitUpdatePolicy(
            repo_dir=Path("."),
            allowed_origin_base="https://github.com/myuser",
            allowed_branch="main",
            module_for_restart="miya",
        ))
        result = await updater.check_and_update()
        if result.updated:
            updater.restart()
    """

    def __init__(self, policy: GitUpdatePolicy) -> None:
        self.policy = policy
        self._repo_dir = policy.repo_dir.resolve()

    async def check_and_update(self) -> GitUpdateResult:
        """检查更新并执行"""
        lock_path = self.policy.lock_path or (
            self._repo_dir / ".miya" / "self_update.lock"
        )

        return await asyncio.to_thread(self._check_and_update_sync, lock_path)

    def _check_and_update_sync(self, lock_path: Path) -> GitUpdateResult:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(lock_path, shared=False):
            return self._do_update()

    def _do_update(self) -> GitUpdateResult:
        # 1. 验证 origin URL
        try:
            origin_url = self._git("config", "--get", "remote.origin.url").strip()
        except subprocess.CalledProcessError as e:
            return GitUpdateResult(success=False, error=f"获取 origin URL 失败: {e}")

        origin_url = _normalize_url(origin_url)
        if self.policy.allowed_origin_base:
            allowed = _normalize_url(self.policy.allowed_origin_base)
            if not origin_url.startswith(allowed):
                return GitUpdateResult(
                    success=False,
                    error=f"origin URL 不匹配: {origin_url} 不在 {allowed} 范围内",
                )

        # 2. 获取当前分支
        try:
            branch = self._git("rev-parse", "--abbrev-ref", "HEAD").strip()
        except subprocess.CalledProcessError as e:
            return GitUpdateResult(success=False, error=f"获取分支失败: {e}")

        if self.policy.allowed_branch and branch != self.policy.allowed_branch:
            return GitUpdateResult(
                success=False,
                error=f"分支不匹配: {branch} != {self.policy.allowed_branch}",
            )

        # 3. 检查 worktree 是否干净
        if self.policy.require_clean_worktree:
            try:
                status = self._git("status", "--porcelain")
                if status.strip():
                    return GitUpdateResult(
                        success=False,
                        updated=False,
                        error="worktree 不干净，有未提交的更改",
                    )
            except subprocess.CalledProcessError as e:
                return GitUpdateResult(success=False, error=f"git status 失败: {e}")

        # 4. 获取当前 HEAD
        try:
            from_commit = self._git("rev-parse", "HEAD").strip()
        except subprocess.CalledProcessError as e:
            return GitUpdateResult(success=False, error=f"获取 HEAD 失败: {e}")

        # 5. Fetch
        try:
            self._git("fetch", "origin", branch, timeout=30)
        except subprocess.CalledProcessError as e:
            return GitUpdateResult(success=False, error=f"git fetch 失败: {e}")

        # 6. 检查是否有更新
        try:
            remote_head = self._git("rev-parse", f"origin/{branch}").strip()
        except subprocess.CalledProcessError as e:
            return GitUpdateResult(success=False, error=f"获取远程 HEAD 失败: {e}")

        if from_commit == remote_head:
            return GitUpdateResult(success=True, updated=False, from_commit=from_commit)

        # 7. Fast-forward only merge
        try:
            self._git("merge", "--ff-only", f"origin/{branch}", timeout=30)
        except subprocess.CalledProcessError as e:
            return GitUpdateResult(
                success=False,
                error=f"fast-forward merge 失败: {e}",
            )

        # 8. 获取变更文件
        try:
            changed = (
                self._git("diff", "--name-only", from_commit, remote_head)
                .strip()
                .split("\n")
            )
        except subprocess.CalledProcessError:
            changed = []

        # 9. uv sync (如果有依赖变更)
        if self.policy.uv_sync_enabled:
            needs_sync = any(name in ("uv.lock", "pyproject.toml") for name in changed)
            if needs_sync:
                try:
                    subprocess.run(
                        ["uv", "sync"],
                        cwd=self._repo_dir,
                        check=True,
                        timeout=120,
                    )
                    logger.info("[SelfUpdate] uv sync 完成")
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    logger.warning("[SelfUpdate] uv sync 失败: %s", e)

        logger.info(
            "[SelfUpdate] 更新成功: %s → %s (%s 个文件)",
            from_commit[:8],
            remote_head[:8],
            len(changed),
        )

        return GitUpdateResult(
            success=True,
            updated=True,
            from_commit=from_commit[:8],
            to_commit=remote_head[:8],
            files_changed=changed,
        )

    def _git(self, *args: str, timeout: int = 15) -> str:
        """执行 git 命令"""
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self._repo_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
        return result.stdout

    def restart(self) -> None:
        """重启当前进程"""
        module = self.policy.module_for_restart
        if not module:
            logger.warning("[SelfUpdate] 未配置模块名，跳过重启")
            return

        logger.info("[SelfUpdate] 正在重启进程...")
        python = sys.executable
        args = [python, "-m", module] + sys.argv[1:]

        if sys.platform == "win32":
            os.execv(python, args)
        else:
            os.execv(python, args)

    async def auto_check_loop(self, interval: float = 3600.0) -> None:
        """定期自动检查更新"""
        while True:
            await asyncio.sleep(interval)
            try:
                result = await self.check_and_update()
                if result.updated:
                    logger.info(
                        "[SelfUpdate] 已更新到 %s，等待重启",
                        result.to_commit,
                    )
            except Exception as e:
                logger.debug("[SelfUpdate] 检查失败: %s", e)


def _normalize_url(url: str) -> str:
    """规范化 Git URL"""
    url = url.strip().rstrip("/").rstrip(".git")
    url = url.replace("git@github.com:", "https://github.com/")
    return url
