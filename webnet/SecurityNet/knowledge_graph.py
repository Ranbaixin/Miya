"""
知识图谱 — NetworkX 本地图引擎

替代 PentAGI 的 Neo4j+Graphiti，提供 7 种图搜索类型。
纯 Python 实现，零外部服务依赖。
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    id: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0


class KnowledgeGraph:
    """基于 NetworkX 的安全知识图谱

    7 种搜索类型（兼容 Graphiti naming）:
    - temporal_window: 时间窗口内的相关节点
    - entity_relationships: 实体间路径查找
    - diverse_results: 多样性结果
    - episode_context: Agent 执行记录
    - successful_tools: 成功工具模式
    - recent_context: 最近的上下文
    - entity_by_label: 按标签查找
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self._node_labels: Dict[str, Set[str]] = {}
        self._storage_dir = storage_dir or os.path.join("data", "knowledge_graph")
        os.makedirs(self._storage_dir, exist_ok=True)
        self._load()

    def add_node(self, node_id: str, node_type: str, properties: Optional[Dict] = None, weight: float = 1.0):
        node = GraphNode(id=node_id, type=node_type, properties=properties or {}, weight=weight)
        self.nodes[node_id] = node
        labels = self._node_labels.setdefault(node_type, set())
        labels.add(node_id)

    def add_edge(
        self, source: str, target: str, edge_type: str, properties: Optional[Dict] = None, weight: float = 1.0
    ):
        if source not in self.nodes:
            self.add_node(source, edge_type, {})
        if target not in self.nodes:
            self.add_node(target, edge_type, {})
        edge = GraphEdge(source=source, target=target, type=edge_type, properties=properties or {}, weight=weight)
        self.edges.append(edge)

    def search(self, search_type: str, **kwargs) -> List[Dict[str, Any]]:
        """统一搜索入口"""
        if search_type == "entity_by_label":
            return self._search_by_label(kwargs.get("label", ""))
        elif search_type == "entity_relationships":
            return self._search_relationships(kwargs.get("entity_id", ""))
        elif search_type == "recent_context":
            return self._search_recent(limit=kwargs.get("limit", 10))
        elif search_type == "diverse_results":
            return self._search_diverse(limit=kwargs.get("limit", 5))
        elif search_type == "successful_tools":
            return self._search_successful_tools()
        elif search_type == "episode_context":
            return self._search_episodes(limit=kwargs.get("limit", 5))
        elif search_type == "temporal_window":
            return self._search_temporal(hours=kwargs.get("hours", 24))
        return []

    def _search_by_label(self, label: str) -> List[Dict[str, Any]]:
        labels = self._node_labels
        matching = set()
        for ntype, ids in labels.items():
            if label.lower() in ntype.lower():
                matching.update(ids)
        return [{"id": nid, **vars(self.nodes[nid])} for nid in matching if nid in self.nodes]

    def _search_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        if entity_id not in self.nodes:
            return []

        # BFS 1-hop
        neighbors = []
        for edge in self.edges:
            if edge.source == entity_id and edge.target in self.nodes:
                neighbors.append(
                    {
                        "node": vars(self.nodes[edge.target]),
                        "edge": vars(edge),
                    }
                )
            elif edge.target == entity_id and edge.source in self.nodes:
                neighbors.append(
                    {
                        "node": vars(self.nodes[edge.source]),
                        "edge": vars(edge),
                    }
                )
        return sorted(neighbors, key=lambda x: -x["edge"]["weight"])[:10]

    def _search_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        nodes = sorted(self.nodes.values(), key=lambda n: n.weight, reverse=True)
        return [vars(n) for n in nodes[:limit]]

    def _search_diverse(self, limit: int = 5) -> List[Dict[str, Any]]:
        seen_types = set()
        results = []
        for node in sorted(self.nodes.values(), key=lambda n: -n.weight):
            if node.type not in seen_types:
                seen_types.add(node.type)
                results.append(vars(node))
            if len(results) >= limit:
                break
        return results

    def _search_successful_tools(self) -> List[Dict[str, Any]]:
        return [vars(n) for n in self.nodes.values() if n.properties.get("success") and n.type == "tool_execution"]

    def _search_episodes(self, limit: int = 5) -> List[Dict[str, Any]]:
        episodes = [n for n in self.nodes.values() if n.type == "episode" or "episode" in n.properties]
        return [vars(e) for e in sorted(episodes, key=lambda e: -e.weight)[:limit]]

    def _search_temporal(self, hours: int = 24) -> List[Dict[str, Any]]:
        result = []
        for n in self.nodes.values():
            ts = n.properties.get("timestamp", 0)
            if ts:
                import time

                if time.time() - ts < hours * 3600:
                    result.append(vars(n))
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": {k: vars(v) for k, v in self.nodes.items()},
            "edges": [vars(e) for e in self.edges],
        }

    def restore_from_dict(self, data: Dict[str, Any]):
        self.nodes.clear()
        self.edges.clear()
        self._node_labels.clear()

        for nid, ndata in data.get("nodes", {}).items():
            if isinstance(ndata, str):  # compat
                ndata = json.loads(ndata)
            node = GraphNode(**{k: ndata.get(k) for k in ("id", "type", "properties", "weight")})
            self.nodes[nid] = node
            self._node_labels.setdefault(node.type, set()).add(nid)

        for edata in data.get("edges", []):
            edge = GraphEdge(**{k: edata.get(k) for k in ("source", "target", "type", "properties", "weight")})
            self.edges.append(edge)

    def save(self):
        path = os.path.join(self._storage_dir, "knowledge_graph.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def _load(self):
        path = os.path.join(self._storage_dir, "knowledge_graph.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.restore_from_dict(json.load(f))
            except Exception as e:
                logger.warning(f"知识图谱加载失败: {e}")

    def record_tool_execution(self, tool_name: str, target: str, success: bool, result: str = ""):
        nid = f"tool:{tool_name}:{target[:50]}"
        self.add_node(
            nid, "tool_execution", {"tool": tool_name, "target": target, "success": success, "result": result[:500]}
        )
        if target:
            self.add_edge(nid, f"target:{target}", "used_against")
            self.add_node(f"target:{target}", "target", {"address": target})
        self.save()

    def record_agent_episode(self, agent_type: str, task: str, outcome: str):
        import time as _time

        nid = f"episode:{agent_type}:{_time.time()}"
        self.add_node(
            nid,
            "episode",
            {"agent": agent_type, "task": task[:200], "outcome": outcome[:200], "timestamp": _time.time()},
        )
        self.save()

    def clear(self):
        self.nodes.clear()
        self.edges.clear()
        self._node_labels.clear()


_kg: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _kg
    if _kg is None:
        _kg = KnowledgeGraph()
    return _kg
