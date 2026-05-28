"""
CTF 存档恢复系统 — 从 BUUCTF_Agent 移植

管理解题流程的断点存档，支持：
- MD5 题目哈希 → 文件映射
- JSON 序列化/反序列化
- 中断恢复
"""

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CheckpointManager:
    def __init__(self, checkpoint_dir: Optional[str] = None):
        self.checkpoint_dir = checkpoint_dir or os.path.join("data", "ctf_checkpoints")
        os.makedirs(self.checkpoint_dir, exist_ok=True)

    def _get_path(self, problem: str) -> str:
        md5_hash = hashlib.md5(problem.encode("utf-8")).hexdigest()
        return os.path.join(self.checkpoint_dir, f"ckpt_{md5_hash}.json")

    def save(
        self, problem: str, step_count: int, memory_data: Dict[str, Any], extra: Optional[Dict[str, Any]] = None
    ) -> None:
        data = {"problem": problem, "step_count": step_count, "memory": memory_data}
        if extra:
            data["extra"] = extra
        path = self._get_path(problem)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("存档保存: step %s → %s", step_count, path)

    def load(self, problem: str) -> Optional[Dict[str, Any]]:
        path = self._get_path(problem)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("problem") != problem:
                logger.warning("存档题目不匹配")
                return None
            return data
        except (json.JSONDecodeError, IOError) as e:
            logger.error("读取存档失败: %s", e)
            return None

    def exists(self, problem: str) -> bool:
        return os.path.exists(self._get_path(problem))

    def delete(self, problem: str) -> None:
        path = self._get_path(problem)
        if os.path.exists(path):
            os.remove(path)

    def list_checkpoints(self) -> List[str]:
        if not os.path.exists(self.checkpoint_dir):
            return []
        return [f for f in os.listdir(self.checkpoint_dir) if f.startswith("ckpt_") and f.endswith(".json")]

    def load_any(self) -> Optional[Dict[str, Any]]:
        files = self.list_checkpoints()
        if not files:
            return None
        path = os.path.join(self.checkpoint_dir, files[0])
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error("读取存档失败: %s", e)
            return None


_global_checkpoint: Optional[CheckpointManager] = None


def get_checkpoint() -> CheckpointManager:
    global _global_checkpoint
    if _global_checkpoint is None:
        _global_checkpoint = CheckpointManager()
    return _global_checkpoint
