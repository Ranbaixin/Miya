"""认知记忆 - 档案存储

借鉴 Undefined 的 profile_storage.py 设计：
- Markdown + YAML Frontmatter 格式
- 原子写入 (tempfile + os.replace)
- 版本快照历史
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ProfileStorage:
    """用户/群侧写档案管理

    文件格式:
        ---
        entity_type: user
        entity_id: "123456"
        display_name: "佳"
        updated_at: 1712345678
        ---
        # 用户侧写

        佳是一个热爱编程的...
    """

    def __init__(
        self,
        profiles_dir: Path | str = "data/cognitive/profiles",
        revision_keep: int = 5,
    ) -> None:
        self.profiles_dir = Path(profiles_dir)
        self.history_dir = self.profiles_dir / "history"
        self.revision_keep = revision_keep
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def _profile_path(self, entity_type: str, entity_id: str | int) -> Path:
        return self.profiles_dir / entity_type / str(entity_id) / "profile.md"

    async def read_profile(
        self, entity_type: str, entity_id: str | int
    ) -> dict[str, Any] | None:
        """读取侧写档案"""
        filepath = self._profile_path(entity_type, entity_id)
        return await asyncio.to_thread(self._read_profile_sync, filepath)

    def _read_profile_sync(self, filepath: Path) -> dict[str, Any] | None:
        if not filepath.exists():
            return None
        content = filepath.read_text(encoding="utf-8")
        return self._parse_markdown_frontmatter(content)

    async def write_profile(
        self,
        entity_type: str,
        entity_id: str | int,
        profile_data: dict[str, Any],
        body: str = "",
    ) -> None:
        """写入侧写档案 (原子写入 + 历史快照)"""
        lock = self._get_lock(f"{entity_type}:{entity_id}")
        async with lock:
            await asyncio.to_thread(
                self._write_profile_sync,
                entity_type,
                str(entity_id),
                profile_data,
                body,
            )

    def _write_profile_sync(
        self,
        entity_type: str,
        entity_id: str,
        profile_data: dict[str, Any],
        body: str,
    ) -> None:
        filepath = self._profile_path(entity_type, entity_id)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # 备份旧版本
        if filepath.exists():
            self._save_revision(filepath, entity_type, entity_id)

        # 写入新版本
        profile_data["updated_at"] = int(time.time())
        frontmatter_yaml = self._serialize_frontmatter(profile_data)
        new_body = self._sanitize_body(body)
        content = f"---\n{frontmatter_yaml}---\n\n{new_body}\n"

        # 原子写入
        fd, tmp_name = tempfile.mkstemp(
            prefix=".profile.", suffix=".tmp", dir=str(filepath.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, str(filepath))
        finally:
            tmp_path = Path(tmp_name)
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def _save_revision(self, filepath: Path, entity_type: str, entity_id: str) -> None:
        """保存历史版本快照"""
        history_dir = self.history_dir / entity_type / entity_id
        history_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time() * 1000)
        dest = history_dir / f"{timestamp}.md"
        try:
            dest.write_text(filepath.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            return

        # 清理旧版本
        revisions = sorted(history_dir.glob("*.md"))
        if len(revisions) > self.revision_keep:
            for old in revisions[: -self.revision_keep]:
                old.unlink(missing_ok=True)

    @staticmethod
    def _parse_markdown_frontmatter(content: str) -> dict[str, Any]:
        """解析 Markdown + YAML Frontmatter"""
        if not content.startswith("---"):
            return {"_body": content}

        try:
            parts = content.split("---", 2)
            if len(parts) < 3:
                return {"_body": content}

            import yaml

            frontmatter = yaml.safe_load(parts[1]) or {}
            frontmatter["_body"] = parts[2].strip()
            return frontmatter
        except Exception:
            return {"_body": content}

    @staticmethod
    def _serialize_frontmatter(data: dict[str, Any]) -> str:
        """序列化 Frontmatter 中的元数据为 YAML"""
        import yaml

        serializable = {k: v for k, v in data.items() if not k.startswith("_")}
        return yaml.dump(serializable, allow_unicode=True, default_flow_style=False)

    @staticmethod
    def _sanitize_body(body: str) -> str:
        """清洗侧写正文"""
        body = body.strip()
        # 移除 code fence 包裹
        if body.startswith("```") and body.endswith("```"):
            lines = body.split("\n")
            body = "\n".join(lines[1:-1])
        return body

    async def delete_profile(self, entity_type: str, entity_id: str | int) -> bool:
        """删除侧写"""
        filepath = self._profile_path(entity_type, entity_id)
        lock = self._get_lock(f"{entity_type}:{entity_id}")
        async with lock:
            return await asyncio.to_thread(self._delete_sync, filepath)

    def _delete_sync(self, filepath: Path) -> bool:
        if filepath.exists():
            filepath.unlink(missing_ok=True)
            # 也清理空目录
            parent = filepath.parent
            if parent.exists() and not list(parent.iterdir()):
                parent.rmdir()
            return True
        return False

    async def sync_display_name(
        self, entity_type: str, entity_id: str | int, display_name: str
    ) -> None:
        """同步展示名称"""
        profile = await self.read_profile(entity_type, entity_id)
        if profile is None:
            return
        if profile.get("display_name") != display_name:
            profile["display_name"] = display_name
            body = profile.pop("_body", "")
            await self.write_profile(entity_type, entity_id, profile, body)
