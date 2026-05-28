"""
CTF Skill 知识库管理器 — 从 BUUCTF_Agent 移植

负责扫描、解析 skills/ 目录下的 SKILL.md 文件，
提取 YAML frontmatter 和正文，提供 prompt 注入格式化输出。
兼容 agentskills.io 开放标准。
"""

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_SKILL_DIR = Path(__file__).parent / "skills"


@dataclass
class SkillInfo:
    name: str
    description: str
    content: str
    location: str


class SkillManager:
    def __init__(self, extra_paths: Optional[List[str]] = None):
        self._skills: Dict[str, SkillInfo] = {}
        self._dirs: List[str] = [str(_DEFAULT_SKILL_DIR)]
        self._loaded = False

        if extra_paths:
            for p in extra_paths:
                ap = os.path.abspath(p)
                if ap not in self._dirs:
                    self._dirs.append(ap)

    def load(self) -> None:
        if self._loaded:
            return
        for directory in self._dirs:
            if not os.path.isdir(directory):
                logger.debug("skill 目录跳过: %s", directory)
                continue
            self._scan_directory(directory)
        self._loaded = True
        logger.info("已加载 %d 个 CTF skill", len(self._skills))

    def _scan_directory(self, directory: str) -> None:
        for root, _dirs, files in os.walk(directory):
            for file_name in files:
                if file_name.lower() == "skill.md":
                    self._load_skill_file(os.path.join(root, file_name))

    def _load_skill_file(self, file_path: str) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception as e:
            logger.warning("读取 skill 失败 %s: %s", file_path, e)
            return

        frontmatter, body = self._parse_frontmatter(raw)
        if frontmatter is None:
            logger.warning("skill 缺 frontmatter: %s", file_path)
            return

        name = frontmatter.get("name", "").strip()
        description = frontmatter.get("description", "").strip()
        if not name or not description:
            logger.warning("skill 缺 name/description: %s", file_path)
            return

        skill = SkillInfo(name=name, description=description, content=body.strip(), location=file_path)
        if name in self._skills:
            logger.warning("skill 名称冲突 '%s'，后者覆盖: %s", name, file_path)
        self._skills[name] = skill

    @staticmethod
    def _parse_frontmatter(raw: str) -> tuple:
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
        if not match:
            return None, raw
        yaml_str = match.group(1)
        body = raw[match.end() :]
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            logger.warning("YAML 解析失败: %s", e)
            return None, raw
        if not isinstance(data, dict):
            return None, raw
        return data, body

    def get_all(self) -> List[SkillInfo]:
        self.load()
        return sorted(self._skills.values(), key=lambda s: s.name)

    def get(self, name: str) -> Optional[SkillInfo]:
        self.load()
        return self._skills.get(name)

    def get_names(self) -> List[str]:
        self.load()
        return sorted(self._skills.keys())

    def format_for_prompt(self, selected: Optional[List[str]] = None) -> str:
        """将 skill 内容格式化为 XML 格式，可注入 Agent prompt。"""
        self.load()
        skills = self.get_all()
        if selected:
            skills = [s for s in skills if s.name in selected]
        if not skills:
            return ""

        parts: List[str] = ["以下是你可调用的 CTF 领域专业能力："]
        for s in skills:
            part = f'<skill name="{s.name}">'
            part += f"\n  <description>{s.description}</description>"
            if s.content:
                part += f"\n  <instructions>\n{s.content}\n  </instructions>"
            part += "\n</skill>"
            parts.append(part)
        return "\n\n".join(parts)


_global_skill_manager: Optional[SkillManager] = None


def get_skill_manager() -> SkillManager:
    global _global_skill_manager
    if _global_skill_manager is None:
        _global_skill_manager = SkillManager()
    return _global_skill_manager
