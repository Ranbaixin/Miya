"""Agent 自介绍自动生成器

借鉴 Undefined 的 intro_generator.py 设计：
- 检测 Agent 代码/配置 hash 变更
- 自动生成 first-person 介绍文档
- 原子文件写入
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class AgentIntroGenerator:
    """Agent 自介绍生成器

    用法:
        gen = AgentIntroGenerator(
            agents_dir=Path("skills/agents"),
            cache_path=Path(".cache/agent_intro_hashes.json"),
            call_llm=lambda prompt: "...告诉我你能做什么...",
        )
        await gen.generate("info_agent")
    """

    def __init__(
        self,
        agents_dir: Path | str = Path("skills/agents"),
        cache_path: Path | str = Path(".cache/agent_intro_hashes.json"),
        call_llm: Callable[[str], str] | None = None,
        max_tokens: int = 4096,
    ):
        self.agents_dir = Path(agents_dir)
        self.cache_path = Path(cache_path)
        self._call_llm = call_llm
        self.max_tokens = max_tokens
        self._cache: dict[str, str] = {}
        self._lock = asyncio.Lock()

    def load_cache(self) -> None:
        """加载 hash 缓存"""
        if self.cache_path.exists():
            try:
                self._cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._cache = {}

    def save_cache(self) -> None:
        """保存 hash 缓存"""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(str(tmp), str(self.cache_path))

    def compute_hash(self, agent_dir: Path) -> str:
        """计算 Agent 目录的内容 Hash (SHA256)"""
        hasher = hashlib.sha256()
        for fpath in sorted(agent_dir.rglob("*")):
            if fpath.is_file():
                name = fpath.name.lower()
                if name.startswith("intro") or name == "__pycache__":
                    continue
                rel = str(fpath.relative_to(agent_dir))
                hasher.update(rel.encode())
                hasher.update(fpath.read_bytes())
        return hasher.hexdigest()

    def needs_generation(self, agent_name: str) -> bool:
        """检查 Agent 是否需要重新生成介绍"""
        agent_dir = self.agents_dir / agent_name
        if not agent_dir.exists():
            return False
        current_hash = self.compute_hash(agent_dir)
        cached_hash = self._cache.get(agent_name, "")
        return current_hash != cached_hash

    async def generate(self, agent_name: str) -> str | None:
        """为单个 Agent 生成自介绍"""
        agent_dir = self.agents_dir / agent_name
        if not agent_dir.exists():
            logger.warning("[IntroGen] Agent 目录不存在: %s", agent_dir)
            return None

        current_hash = self.compute_hash(agent_dir)

        async with self._lock:
            if self._cache.get(agent_name) == current_hash:
                logger.debug("[IntroGen] %s 无变更，跳过", agent_name)
                return None

            # 收集 Agent 信息
            config = self._read_config(agent_dir)
            code_files = self._read_code_files(agent_dir)

            # 调用 LLM 生成介绍
            if self._call_llm:
                intro = await self._generate_intro(agent_name, config, code_files)
            else:
                intro = self._fallback_intro(agent_name, config)

            # 原子写入
            intro_path = agent_dir / "intro.generated.md"
            await asyncio.to_thread(self._atomic_write, intro_path, intro)

            # 更新缓存
            self._cache[agent_name] = current_hash
            logger.info("[IntroGen] %s 介绍已更新", agent_name)

            return intro

    async def generate_all(self) -> list[str]:
        """扫描并生成所有 Agent 自介绍"""
        generated: list[str] = []
        if not self.agents_dir.exists():
            return generated

        for agent_dir in sorted(self.agents_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            if agent_dir.name.startswith("_") or agent_dir.name.startswith("."):
                continue

            name = agent_dir.name
            if self.needs_generation(name):
                try:
                    intro = await self.generate(name)
                    if intro:
                        generated.append(name)
                except Exception as e:
                    logger.warning("[IntroGen] %s 生成失败: %s", name, e)

        return generated

    def _read_config(self, agent_dir: Path) -> dict[str, Any]:
        """读取 Agent 配置"""
        for config_name in ("config.json", "agent.json", "agent.yaml"):
            config_path = agent_dir / config_name
            if config_path.exists():
                try:
                    content = config_path.read_text(encoding="utf-8")
                    if config_name.endswith(".json"):
                        return json.loads(content)
                    elif config_name.endswith(".yaml"):
                        import yaml

                        return yaml.safe_load(content) or {}
                except Exception:
                    pass
        return {}

    def _read_code_files(self, agent_dir: Path) -> list[str]:
        """读取 Agent 代码文件摘要"""
        code_summaries = []
        for fpath in sorted(agent_dir.glob("*.py")):
            if fpath.name == "__init__.py":
                continue
            try:
                content = fpath.read_text(encoding="utf-8")
                # 只取前 100 行作为摘要
                lines = content.split("\n")[:100]
                code_summaries.append(f"# {fpath.name}\n" + "\n".join(lines))
            except Exception:
                pass
        return code_summaries

    async def _generate_intro(
        self,
        name: str,
        config: dict[str, Any],
        code_files: list[str],
    ) -> str:
        """使用 LLM 生成自我介绍"""
        tools_desc = json.dumps(
            config.get("tools", config.get("callable", {})),
            ensure_ascii=False,
            indent=2,
        )
        code_preview = "\n---\n".join(code_files[:2]) if code_files else "(无代码)"

        prompt = (
            f"你是一个名为 '{name}' 的 AI Agent。\n"
            f"请基于以下信息，用中文写一段简洁的第一人称自我介绍（200字左右）。\n"
            f"介绍你的能力、擅长什么、在什么场景下可以帮到用户。\n\n"
            f"---\n"
            f"配置:\n{tools_desc}\n\n"
            f"代码片段:\n{code_preview[:3000]}\n\n"
            f"直接输出介绍文本，不要添加额外说明。"
        )

        try:
            result = self._call_llm(prompt) if self._call_llm else ""
            return result.strip() if result else self._fallback_intro(name, config)
        except Exception:
            return self._fallback_intro(name, config)

    def _fallback_intro(self, name: str, config: dict[str, Any]) -> str:
        """回退的简单介绍"""
        desc = config.get("description", config.get("name", name))
        return (
            f"我是 {desc}，弥娅系统的 {name} Agent。\n"
            f"我被设计来处理特定类型的任务，为弥娅提供专业能力支持。"
        )

    @staticmethod
    def _atomic_write(filepath: Path, content: str) -> None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        tmp = filepath.with_suffix(".tmp")
        tmp.write_text(content, encoding="utf-8")
        os.replace(str(tmp), str(filepath))
