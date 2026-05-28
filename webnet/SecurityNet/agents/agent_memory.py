"""Agent 记忆系统 — Python 原生实现

从 PentAGI 移植的轻量级记忆系统。
使用 JSON 文件 + 简单关键词搜索（不依赖 PostgreSQL/pgvector），
使 Agent 能够：
1. 存储和检索指南、答案、代码
2. 追踪 Agent 对话历史
3. 记录工具执行结果
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_DIR = Path(os.environ.get("MIYA_AGENT_MEMORY_DIR", "data/agent_memory"))


@dataclass
class MemoryEntry:
    """一条记忆记录"""

    id: str
    type: str  # guide, answer, code, tool_exec, agent_response
    question: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    score: float = 0.0


class AgentMemory:
    """Agent 轻量记忆系统

    支持 7 种记忆类型：
    - guide: 方法论/操作指南
    - answer: 问答记录
    - code: 代码片段
    - tool_exec: 工具执行记录
    - agent_response: Agent 响应
    - entity: 发现的实体（IP、服务、漏洞）
    - relationship: 实体间关系
    """

    def __init__(self, memory_dir: Optional[Path] = None):
        self.memory_dir = Path(memory_dir or DEFAULT_MEMORY_DIR)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._guides: List[MemoryEntry] = []
        self._answers: List[MemoryEntry] = []
        self._code: List[MemoryEntry] = []
        self._tool_execs: List[MemoryEntry] = []
        self._agent_responses: List[MemoryEntry] = []
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._relationships: List[Dict[str, Any]] = []
        self._load()

    # ─── Load / Save ────────────────────────────

    def _load(self):
        """从 JSON 文件加载记忆"""
        for name, target in [
            ("guides.json", self._guides),
            ("answers.json", self._answers),
            ("code.json", self._code),
            ("tool_execs.json", self._tool_execs),
            ("agent_responses.json", self._agent_responses),
        ]:
            fp = self.memory_dir / name
            if fp.exists():
                try:
                    data = json.loads(fp.read_text(encoding="utf-8"))
                    for item in data:
                        target.append(MemoryEntry(**item))
                except Exception as e:
                    logger.warning(f"加载 {name} 失败: {e}")

        kg_path = self.memory_dir / "knowledge_graph.json"
        if kg_path.exists():
            try:
                kg = json.loads(kg_path.read_text(encoding="utf-8"))
                self._entities = kg.get("entities", {})
                self._relationships = kg.get("relationships", [])
            except Exception:
                pass

    def _save(self):
        """保存记忆到 JSON 文件"""
        save_map = {
            "guides.json": [vars(e) for e in self._guides],
            "answers.json": [vars(e) for e in self._answers],
            "code.json": [vars(e) for e in self._code],
            "tool_execs.json": [vars(e) for e in self._tool_execs],
            "agent_responses.json": [vars(e) for e in self._agent_responses],
        }
        for name, data in save_map.items():
            fp = self.memory_dir / name
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        kg_path = self.memory_dir / "knowledge_graph.json"
        kg = {"entities": self._entities, "relationships": self._relationships}
        kg_path.write_text(json.dumps(kg, ensure_ascii=False, indent=2), encoding="utf-8")

    # ─── Store ──────────────────────────────────

    def store_guide(self, question: str, guide: str, guide_type: str = "pentest") -> str:
        entry = MemoryEntry(
            id=f"guide-{int(time.time() * 1000)}",
            type="guide",
            question=question,
            content=guide,
            metadata={"guide_type": guide_type},
        )
        self._guides.append(entry)
        self._save()
        return entry.id

    def store_answer(self, question: str, answer: str, answer_type: str = "other") -> str:
        entry = MemoryEntry(
            id=f"answer-{int(time.time() * 1000)}",
            type="answer",
            question=question,
            content=answer,
            metadata={"answer_type": answer_type},
        )
        self._answers.append(entry)
        self._save()
        return entry.id

    def store_code(self, question: str, code: str, lang: str, explanation: str = "", description: str = "") -> str:
        entry = MemoryEntry(
            id=f"code-{int(time.time() * 1000)}",
            type="code",
            question=question,
            content=code,
            metadata={"lang": lang, "explanation": explanation, "description": description},
        )
        self._code.append(entry)
        self._save()
        return entry.id

    def store_tool_exec(self, tool_name: str, result: str, task_id: Optional[int] = None) -> str:
        entry = MemoryEntry(
            id=f"exec-{int(time.time() * 1000)}",
            type="tool_exec",
            question=f"Tool execution: {tool_name}",
            content=result,
            metadata={"tool": tool_name, "task_id": task_id},
        )
        self._tool_execs.append(entry)
        self._save()
        return entry.id

    def store_agent_response(self, agent_type: str, task: str, result: str) -> str:
        entry = MemoryEntry(
            id=f"response-{int(time.time() * 1000)}",
            type="agent_response",
            question=task,
            content=result,
            metadata={"agent_type": agent_type},
        )
        self._agent_responses.append(entry)
        self._save()
        return entry.id

    # ─── Search ─────────────────────────────────

    def _score(self, query: str, entry: MemoryEntry) -> float:
        """简单关键词评分"""
        query_lower = query.lower()
        score = 0.0
        # 问题匹配
        for word in query_lower.split():
            if word in entry.question.lower():
                score += 1.0
            if word in entry.content.lower():
                score += 0.5
        # 完全匹配加分
        if query_lower in entry.question.lower():
            score += 3.0
        if query_lower in entry.content.lower():
            score += 2.0
        return score

    def search_in_memory(
        self, questions: List[str], task_id: Optional[int] = None, max_results: int = 10
    ) -> List[MemoryEntry]:
        """跨所有类型搜索记忆"""
        all_entries = self._guides + self._answers + self._code + self._tool_execs + self._agent_responses
        results = []
        for q in questions:
            for entry in all_entries:
                score = self._score(q, entry)
                if score > 0:
                    entry.score = score
                    results.append(entry)

        if task_id is not None:
            results = [r for r in results if r.metadata.get("task_id") == task_id]

        # 去重并排序
        seen = set()
        unique = []
        for r in sorted(results, key=lambda x: x.score, reverse=True):
            if r.id not in seen:
                seen.add(r.id)
                unique.append(r)
        return unique[:max_results]

    def search_guides(
        self, questions: List[str], guide_type: Optional[str] = None, max_results: int = 5
    ) -> List[MemoryEntry]:
        """搜索指南"""
        results = []
        for q in questions:
            for entry in self._guides:
                if guide_type and entry.metadata.get("guide_type") != guide_type:
                    continue
                score = self._score(q, entry)
                if score > 0:
                    entry.score = score
                    results.append(entry)
        return sorted(results, key=lambda x: x.score, reverse=True)[:max_results]

    def search_answers(
        self, questions: List[str], answer_type: Optional[str] = None, max_results: int = 5
    ) -> List[MemoryEntry]:
        """搜索答案"""
        results = []
        for q in questions:
            for entry in self._answers:
                if answer_type and entry.metadata.get("answer_type") != answer_type:
                    continue
                score = self._score(q, entry)
                if score > 0:
                    entry.score = score
                    results.append(entry)
        return sorted(results, key=lambda x: x.score, reverse=True)[:max_results]

    def search_code(self, questions: List[str], lang: Optional[str] = None, max_results: int = 5) -> List[MemoryEntry]:
        """搜索代码"""
        results = []
        for q in questions:
            for entry in self._code:
                if lang and entry.metadata.get("lang", "").lower() != lang.lower():
                    continue
                score = self._score(q, entry)
                if score > 0:
                    entry.score = score
                    results.append(entry)
        return sorted(results, key=lambda x: x.score, reverse=True)[:max_results]

    # ─── Knowledge Graph ────────────────────────

    def add_entity(self, entity_id: str, entity_type: str, properties: Dict[str, Any]):
        """添加实体到知识图谱"""
        self._entities[entity_id] = {
            "type": entity_type,
            "properties": properties,
            "created_at": datetime.now().isoformat(),
        }
        self._save()

    def add_relationship(self, source: str, target: str, rel_type: str, properties: Optional[Dict] = None):
        """添加关系到知识图谱"""
        self._relationships.append(
            {
                "source": source,
                "target": target,
                "type": rel_type,
                "properties": properties or {},
                "created_at": datetime.now().isoformat(),
            }
        )
        self._save()

    def graphiti_search(
        self,
        search_type: str,
        query: str,
        max_results: int = 5,
        max_depth: int = 2,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """知识图谱搜索（7 种搜索类型）"""
        results = []

        if search_type == "recent_context":
            # 返回最近的 agent 响应和工具执行
            all_agents = sorted(self._agent_responses, key=lambda x: x.created_at, reverse=True)
            all_tools = sorted(self._tool_execs, key=lambda x: x.created_at, reverse=True)
            for e in (all_agents + all_tools)[:max_results]:
                results.append({"type": e.type, "content": e.content[:1000], "created_at": e.created_at})

        elif search_type == "successful_tools":
            # 返回成功的工具执行
            for e in reversed(self._tool_execs):
                if "success" in e.content.lower() or "error" not in e.content.lower()[:200]:
                    results.append({"type": e.type, "tool": e.metadata.get("tool"), "content": e.content[:500]})
                    if len(results) >= max_results:
                        break

        elif search_type == "episode_context":
            # 返回匹配的 agent 响应
            for e in self._agent_responses:
                if self._score(query, e) > 0:
                    results.append({"type": e.type, "agent": e.metadata.get("agent_type"), "content": e.content[:2000]})
                    if len(results) >= max_results:
                        break

        elif search_type == "entity_relationships":
            center = kwargs.get("center_node_uuid")
            if center and center in self._entities:
                for rel in self._relationships:
                    if rel["source"] == center or rel["target"] == center:
                        results.append(rel)
                        if len(results) >= max_results:
                            break

        elif search_type == "entity_by_label":
            label = kwargs.get("node_labels", [])
            for eid, entity in self._entities.items():
                if not label or entity["type"] in label:
                    results.append({"id": eid, **entity})
                    if len(results) >= max_results:
                        break

        elif search_type == "diverse_results":
            # 随机采样不同的记忆类型
            import random

            pool = self._guides + self._answers + self._code
            if pool:
                sampled = random.sample(pool, min(max_results, len(pool)))
                for e in sampled:
                    results.append({"type": e.type, "content": e.content[:500]})

        elif search_type == "temporal_window":
            # 时间窗口搜索
            from datetime import timedelta

            window = kwargs.get("recency_window", "24h")
            hours = 24
            if "h" in window:
                hours = float(window.replace("h", ""))
            elif "d" in window:
                hours = float(window.replace("d", "")) * 24
            cutoff = datetime.now() - timedelta(hours=hours)
            cutoff_str = cutoff.isoformat()
            for e in self._tool_execs + self._agent_responses:
                if e.created_at >= cutoff_str and self._score(query, e) > 0:
                    results.append({"type": e.type, "content": e.content[:500], "created_at": e.created_at})
                    if len(results) >= max_results:
                        break

        return results

    # ─── Stats ──────────────────────────────────

    def get_stats(self) -> Dict[str, int]:
        return {
            "guides": len(self._guides),
            "answers": len(self._answers),
            "code": len(self._code),
            "tool_execs": len(self._tool_execs),
            "agent_responses": len(self._agent_responses),
            "entities": len(self._entities),
            "relationships": len(self._relationships),
        }

    def clear(self):
        """清空所有记忆"""
        self._guides.clear()
        self._answers.clear()
        self._code.clear()
        self._tool_execs.clear()
        self._agent_responses.clear()
        self._entities.clear()
        self._relationships.clear()
        self._save()


# 全局单例
_global_memory: Optional[AgentMemory] = None


def get_agent_memory() -> AgentMemory:
    global _global_memory
    if _global_memory is None:
        _global_memory = AgentMemory()
    return _global_memory
