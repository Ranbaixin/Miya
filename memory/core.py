"""
================================================================
        弥娅统一记忆系统 (Miya Unified Memory System) V3.1
================================================================

这是弥娅的**唯一**记忆系统核心，所有记忆操作都必须通过此类。

设计原则：
1. 单一入口 - 100%统一
2. 分层存储 - 对话/短期/长期/向量/图谱
3. 数据一致 - 单一数据结构
4. 自动生命周期管理
5. 企业级可靠性

架构：
┌─────────────────────────────────────────────────────────────┐
│                      MiyaMemoryCore                          │
│                   (唯一记忆系统核心)                           │
├─────────────────────────────────────────────────────────────┤
│  MemoryLevel.DIALOGUE     - 对话历史 (会话级)                │
│  MemoryLevel.SHORT_TERM   - 短期记忆 (TTL自动过期)           │
│  MemoryLevel.LONG_TERM    - 长期记忆 (持久化)                │
│  MemoryLevel.SEMANTIC     - 语义记忆 (向量搜索)              │
│  MemoryLevel.KNOWLEDGE    - 知识图谱 (实体关系)              │
├─────────────────────────────────────────────────────────────┤
│  存储后端：JSON文件 + SQLite (FTS5 全文搜索 + 向量搜索)    │
└─────────────────────────────────────────────────────────────┘

作者: 编程大师
日期: 2026
================================================================
"""

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import aiofiles


# 直接定义编码常量，避免循环导入
class Encoding:
    UTF8 = "utf-8"


logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================


class MemoryLevel(Enum):
    """记忆层级"""

    DIALOGUE = "dialogue"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    SEMANTIC = "semantic"
    KNOWLEDGE = "knowledge"
    PINNED = "pinned"


class MemoryPriority(Enum):
    """记忆优先级"""

    LOW = 0.3
    NORMAL = 0.5
    HIGH = 0.7
    CRITICAL = 0.9


class MemorySource(Enum):
    """记忆来源"""

    DIALOGUE = "dialogue"  # 对话中自动存储
    AUTO_EXTRACT = "auto_extract"  # 自动提取
    MANUAL = "manual"  # 手动添加
    SYSTEM = "system"  # 系统生成
    IMPORTED = "imported"  # 导入
    ASSISTANT_SELF = "assistant_self"  # 弥娅自记忆（承诺、观点、建议等）


# ==================== 核心数据结构 ====================


@dataclass
class MemoryItem:
    """
    统一记忆数据项 - 整个系统的唯一数据结构

    所有记忆都是这个格式，没有任何例外！
    """

    # 唯一标识
    id: str = ""

    # 内容
    content: str = ""

    # 层级
    level: MemoryLevel = MemoryLevel.SHORT_TERM

    # 优先级
    priority: float = 0.5

    # 标签
    tags: List[str] = field(default_factory=list)

    # 用户关联
    user_id: str = "global"
    session_id: str = ""
    group_id: str = ""
    platform: str = "unknown"

    # 来源
    source: MemorySource = MemorySource.SYSTEM
    role: str = ""  # user/assistant

    # 对话详情
    event_type: str = ""  # 对话事件类型 (如"工作会议", "日常聊天", "学习讨论")
    location: str = ""  # 对话地点 (如"办公室", "咖啡馆", "线上")
    conversation_partner: str = ""  # 明确的对话对象
    emotional_tone: str = ""  # 情感基调 (如"愉快", "焦虑", "中性", "兴奋")
    significance: float = 0.5  # 主观重要性评分 (0-1)

    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None

    # 向量 (语义层)
    vector: Optional[List[float]] = None

    # 知识图谱 (图谱层)
    subject: str = ""
    predicate: str = ""
    obj: str = ""

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 访问统计
    access_count: int = 0
    last_accessed: Optional[str] = None

    # 状态
    is_pinned: bool = False  # 置顶
    is_archived: bool = False  # 归档

    def __post_init__(self):
        """初始化后处理"""
        # 自动生成ID
        if not self.id:
            self.id = self._generate_id()

        # 初始化时间
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def _generate_id(self) -> str:
        """生成唯一ID"""
        unique_str = f"{self.content}{self.user_id}{datetime.now().isoformat()}{uuid.uuid4().hex[:8]}"
        return hashlib.md5(unique_str.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        # 处理枚举
        data["level"] = self.level.value if isinstance(self.level, MemoryLevel) else self.level
        data["source"] = self.source.value if isinstance(self.source, MemorySource) else self.source
        # 处理 metadata 中可能存在的枚举
        if "metadata" in data and isinstance(data["metadata"], dict):
            data["metadata"] = self._serialize_dict(data["metadata"])
        return data

    def _serialize_dict(self, d: Dict) -> Dict:
        """递归序列化字典中的枚举"""
        result = {}
        for k, v in d.items():
            if isinstance(v, Enum):
                result[k] = v.value
            elif isinstance(v, dict):
                result[k] = self._serialize_dict(v)
            elif isinstance(v, list):
                result[k] = [self._serialize_value(item) for item in v]
            else:
                result[k] = v
        return result

    def _serialize_value(self, v):
        """序列化单个值"""
        if isinstance(v, Enum):
            return v.value
        elif isinstance(v, dict):
            return self._serialize_dict(v)
        elif isinstance(v, list):
            return [self._serialize_value(item) for item in v]
        return v

    @classmethod
    def from_dict(cls, data: Dict) -> Optional["MemoryItem"]:
        """从字典创建"""
        if not data:
            return None

        data = data.copy()

        # 处理枚举
        if isinstance(data.get("level"), str):
            data["level"] = MemoryLevel(data["level"])
        if isinstance(data.get("source"), str):
            data["source"] = MemorySource(data["source"])

        # 移除None值
        data = {k: v for k, v in data.items() if v is not None}

        # 过滤未知字段，避免 __init__() got an unexpected keyword argument
        valid_fields = {f.name for f in fields(cls)}
        data = {k: v for k, v in data.items() if k in valid_fields}

        return cls(**data)

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.level != MemoryLevel.SHORT_TERM:
            return False
        if not self.expires_at:
            return False
        try:
            return datetime.now() > datetime.fromisoformat(self.expires_at)
        except (ValueError, TypeError):
            return False

    def is_valid(self) -> bool:
        """检查是否有效"""
        # 过期检查
        if self.is_expired():
            return False
        # 归档检查
        if self.is_archived:
            return False
        # 内容检查
        return not (not self.content or len(self.content.strip()) < 1)

    def update_access(self):
        """更新访问统计"""
        if self.access_count is None:
            self.access_count = 0
        self.access_count += 1
        self.last_accessed = datetime.now().isoformat()

    def clone(self) -> "MemoryItem":
        """克隆记忆"""
        cloned = MemoryItem.from_dict(self.to_dict())
        if cloned is None:
            # This should never happen with a valid MemoryItem, but handle just in case
            raise RuntimeError("Failed to clone memory item")
        return cloned


@dataclass
class MemoryQuery:
    """记忆查询条件"""

    # 文本搜索
    query: str = ""

    # 用户过滤
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    group_id: Optional[str] = None
    platform: Optional[str] = None

    # 层级过滤
    level: Optional[MemoryLevel] = None
    levels: Optional[List[MemoryLevel]] = None

    # 标签过滤
    tags: Optional[List[str]] = None
    any_tag: bool = False  # True: 任一匹配, False: 全部匹配

    # 优先级过滤
    priority: Optional[float] = None
    min_priority: float = 0.0
    max_priority: float = 1.0

    # 来源过滤
    source: Optional[MemorySource] = None

    # 时间过滤
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # 状态过滤
    include_archived: bool = False
    include_expired: bool = False
    is_pinned: Optional[bool] = None

    # 对话详情过滤
    event_type: Optional[str] = None
    location: Optional[str] = None
    conversation_partner: Optional[str] = None
    emotional_tone: Optional[str] = None
    min_significance: float = 0.0
    max_significance: float = 1.0

    # 分页
    limit: int = 20
    offset: int = 0

    # 排序
    sort_by: str = "priority"  # priority, created_at, updated_at, access_count
    sort_order: str = "desc"  # asc, desc


# ==================== 存储后端接口 ====================


class MemoryBackend:
    """记忆存储后端基类"""

    async def save(self, memory: MemoryItem) -> bool:
        raise NotImplementedError

    async def load(self, memory_id: str) -> Optional[MemoryItem]:
        raise NotImplementedError

    async def delete(self, memory_id: str) -> bool:
        raise NotImplementedError

    async def query(self, query: MemoryQuery) -> List[MemoryItem]:
        raise NotImplementedError

    async def close(self):
        pass


class JsonBackend(MemoryBackend):
    """JSON文件后端 - 优化版"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.dialogue_dir = base_dir / "dialogue"
        self.short_term_dir = base_dir / "short_term"
        self.long_term_dir = base_dir / "long_term"
        self.semantic_dir = base_dir / "semantic"
        self.knowledge_dir = base_dir / "knowledge"

        for d in [
            self.dialogue_dir,
            self.short_term_dir,
            self.long_term_dir,
            self.semantic_dir,
            self.knowledge_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

        self.index_file = base_dir / "index.json"
        self.tag_index_file = base_dir / "tag_index.json"  # 倒排索引
        self._index: Dict[str, Dict] = {}
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)  # 倒排索引 (权威版本)
        self._query_cache: Dict[str, List[MemoryItem]] = {}  # 查询缓存
        self._cache_max_size = 100

        # 文件锁保护索引读写 (懒初始化，避免 event loop 绑定问题)
        self._index_lock: Optional[asyncio.Lock] = None

        self._load_index()
        self._load_tag_index()
        self._cleanup_stale_entries()

    async def _get_lock(self) -> asyncio.Lock:
        if self._index_lock is None:
            self._index_lock = asyncio.Lock()
        return self._index_lock

    def _load_index(self):
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
            except Exception as e:
                logger.warning(f"加载索引失败: {e}")
                self._index = {}

    def _save_index(self):
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存索引失败: {e}")

    def _load_tag_index(self):
        if self.tag_index_file.exists():
            try:
                with open(self.tag_index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for tag, ids in data.items():
                        self._tag_index[tag] = set(ids)
            except Exception as e:
                logger.warning(f"加载倒排索引失败: {e}")

    def _save_tag_index(self):
        try:
            data = {tag: list(ids) for tag, ids in self._tag_index.items()}
            with open(self.tag_index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存倒排索引失败: {e}")

    def _cleanup_stale_entries(self):
        """清理索引中指向不存在文件的失效条目"""
        stale_ids = []
        for memory_id, info in self._index.items():
            file_path = Path(info.get("file_path", ""))
            if not file_path.exists():
                stale_ids.append(memory_id)

        if stale_ids:
            logger.warning(f"[JsonBackend] 发现 {len(stale_ids)} 条失效索引条目，正在清理...")
            for memory_id in stale_ids:
                info = self._index[memory_id]
                tags = info.get("tags", [])
                for tag in tags:
                    self._tag_index[tag].discard(memory_id)
                del self._index[memory_id]
            self._save_index()
            self._save_tag_index()
            logger.info(f"[JsonBackend] 已清理 {len(stale_ids)} 条失效索引")

    def _get_dir(self, level: Union[MemoryLevel, List[MemoryLevel]]) -> Path:
        """获取层级目录"""
        if isinstance(level, list):
            level = level[0] if level else MemoryLevel.LONG_TERM

        dirs = {
            MemoryLevel.DIALOGUE: self.dialogue_dir,
            MemoryLevel.SHORT_TERM: self.short_term_dir,
            MemoryLevel.LONG_TERM: self.long_term_dir,
            MemoryLevel.SEMANTIC: self.semantic_dir,
            MemoryLevel.KNOWLEDGE: self.knowledge_dir,
        }
        return dirs.get(level, self.long_term_dir)

    def _get_file_path(self, memory: MemoryItem) -> Path:
        """获取文件路径"""
        level_dir = self._get_dir(memory.level)

        # 按用户分组
        if memory.user_id and memory.user_id != "global":
            user_dir = level_dir / memory.user_id
            user_dir.mkdir(parents=True, exist_ok=True)
            return user_dir / f"{memory.id}.json"

        return level_dir / f"{memory.id}.json"

    async def save(self, memory: MemoryItem) -> bool:
        """保存记忆"""
        async with (await self._get_lock()):
            try:
                file_path = self._get_file_path(memory)

                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(memory.to_dict(), ensure_ascii=False, indent=2))

                self._index[memory.id] = {
                    "level": memory.level.value,
                    "user_id": memory.user_id,
                    "session_id": memory.session_id,
                    "group_id": memory.group_id,
                    "tags": memory.tags,
                    "created_at": memory.created_at,
                    "file_path": str(file_path),
                    "priority": memory.priority,
                }
                self._save_index()

                for tag in memory.tags:
                    self._tag_index[tag].add(memory.id)
                self._save_tag_index()

                self._invalidate_cache()

                return True
            except Exception as e:
                logger.error(f"保存记忆失败: {e}")
                return False

    def _invalidate_cache(self):
        """使查询缓存失效"""
        self._query_cache.clear()

    def _get_cache_key(self, query: MemoryQuery) -> str:
        """生成缓存键"""
        return f"{query.user_id or ''}:{query.level}:{query.query}:{query.limit}"

    def get_from_cache(self, query: MemoryQuery) -> Optional[List[MemoryItem]]:
        """从缓存获取"""
        key = self._get_cache_key(query)
        return self._query_cache.get(key)

    def put_to_cache(self, query: MemoryQuery, results: List[MemoryItem]):
        """放入缓存"""
        if len(self._query_cache) >= self._cache_max_size:
            first_key = next(iter(self._query_cache))
            del self._query_cache[first_key]
        key = self._get_cache_key(query)
        self._query_cache[key] = results

    async def load(self, memory_id: str) -> Optional[MemoryItem]:
        """加载记忆"""
        if memory_id not in self._index:
            return None

        try:
            file_path = Path(self._index[memory_id]["file_path"])
            if not file_path.exists():
                return None

            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                # 检查文件是否为空
                if not content or not content.strip():
                    logger.warning(f"记忆文件为空: {file_path}")
                    return None
                data = json.loads(content)
                return MemoryItem.from_dict(data)
        except Exception as e:
            logger.error(f"加载记忆失败: {e}")
            return None

    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        async with (await self._get_lock()):
            if memory_id not in self._index:
                return False

            try:
                file_path = Path(self._index[memory_id].get("file_path", ""))
                if file_path.exists():
                    file_path.unlink()

                tags = self._index[memory_id].get("tags", [])
                for tag in tags:
                    self._tag_index[tag].discard(memory_id)

                del self._index[memory_id]
                self._save_index()
                self._save_tag_index()
                self._invalidate_cache()
                return True
            except Exception as e:
                logger.error(f"删除记忆失败: {e}")
                return False

    async def query(self, query: MemoryQuery) -> List[MemoryItem]:
        """查询记忆 - 使用内存索引直读文件路径，避免全量文件系统扫描"""
        cached = self.get_from_cache(query)
        if cached is not None:
            return cached

        results = []
        candidate_ids: Optional[Set[str]] = None

        if query.tags:
            candidate_ids = self._get_candidates_by_tags(query.tags, query.any_tag)

        if query.user_id:
            user_candidates = self._get_candidates_by_user(query.user_id)
            candidate_ids = user_candidates if candidate_ids is None else candidate_ids & user_candidates

        if query.group_id:
            group_candidates = self._get_candidates_by_group(query.group_id)
            candidate_ids = group_candidates if candidate_ids is None else candidate_ids & group_candidates

        if candidate_ids is None:
            candidate_ids = set(self._index.keys())

        search_levels = (
            query.levels if query.levels
            else [query.level] if query.level
            else list(MemoryLevel)
        )
        search_level_names = {lvl.value for lvl in search_levels}

        for memory_id in candidate_ids:
            index_info = self._index.get(memory_id)
            if not index_info:
                continue

            if index_info.get("level") not in search_level_names:
                continue

            file_path_str = index_info.get("file_path", "")
            if not file_path_str:
                continue

            file_path = Path(file_path_str)
            if not file_path.exists():
                continue

            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                    data = json.loads(content)
                    memory = MemoryItem.from_dict(data)

                    if self._match_query(memory, query):
                        results.append(memory)
            except (json.JSONDecodeError, OSError):
                continue

        results = self._sort_results(results, query.sort_by, query.sort_order)
        paginated = results[query.offset : query.offset + query.limit]

        self.put_to_cache(query, paginated)
        return paginated

    def _get_candidates_by_tags(self, tags: List[str], any_tag: bool) -> Set[str]:
        """通过标签获取候选ID"""
        if any_tag:
            result = set()
            for tag in tags:
                result.update(self._tag_index.get(tag, set()))
            return result
        else:
            sets = [self._tag_index.get(tag, set()) for tag in tags]
            if not sets:
                return set()
            result = sets[0]
            for s in sets[1:]:
                result = result & s
            return result

    def _get_candidates_by_user(self, user_id: str) -> Set[str]:
        """通过用户获取候选ID"""
        return {mid for mid, info in self._index.items() if info.get("user_id") == user_id}

    def _get_candidates_by_group(self, group_id: str) -> Set[str]:
        """通过群组获取候选ID"""
        return {mid for mid, info in self._index.items() if info.get("group_id") == group_id}

    def _match_query(self, memory: Optional[MemoryItem], query: MemoryQuery) -> bool:
        """检查是否匹配查询"""
        if memory is None:
            return False

        # 用户过滤
        if query.user_id and memory.user_id != query.user_id:
            return False

        # 会话过滤
        if query.session_id and memory.session_id != query.session_id:
            return False

        # 群组过滤
        if query.group_id and memory.group_id != query.group_id:
            return False

        # 标签过滤
        if query.tags:
            if query.any_tag:
                if not any(tag in memory.tags for tag in query.tags):
                    return False
            else:
                if not all(tag in memory.tags for tag in query.tags):
                    return False

        # 优先级过滤
        if memory.priority < query.min_priority or memory.priority > query.max_priority:
            return False

        # 时间过滤
        if query.start_time or query.end_time:
            try:
                mem_time = datetime.fromisoformat(memory.created_at)
                if query.start_time and mem_time < query.start_time:
                    return False
                if query.end_time and mem_time > query.end_time:
                    return False
            except (ValueError, TypeError):
                pass

        # 归档过滤
        if not query.include_archived and memory.is_archived:
            return False

        # 过期过滤
        if not query.include_expired and memory.is_expired():
            return False

        # 置顶过滤
        if query.is_pinned is not None and memory.is_pinned != query.is_pinned:
            return False

        # 文本搜索
        if query.query and query.query.lower() not in memory.content.lower():
            # 检查标签
            if not any(query.query.lower() in tag.lower() for tag in memory.tags):
                return False

        # 对话详情过滤
        if query.event_type and memory.event_type != query.event_type:
            return False
        if query.location and memory.location != query.location:
            return False
        if query.conversation_partner and memory.conversation_partner != query.conversation_partner:
            return False
        if query.emotional_tone and memory.emotional_tone != query.emotional_tone:
            return False
        return not (memory.significance < query.min_significance or memory.significance > query.max_significance)

    def _sort_results(self, results: List[MemoryItem], sort_by: str, order: str) -> List[MemoryItem]:
        """排序结果"""
        reverse = order == "desc"

        if sort_by == "priority":
            results.sort(key=lambda x: x.priority, reverse=reverse)
        elif sort_by == "created_at":
            results.sort(key=lambda x: x.created_at, reverse=reverse)
        elif sort_by == "updated_at":
            results.sort(key=lambda x: x.updated_at, reverse=reverse)
        elif sort_by == "access_count":
            results.sort(key=lambda x: x.access_count, reverse=reverse)

        return results

    async def get_all_ids(self, level: Optional[MemoryLevel] = None) -> List[str]:
        """获取所有记忆ID"""
        if level:
            return [mid for mid, info in self._index.items() if info.get("level") == level.value]
        return list(self._index.keys())

    async def count(self, level: Optional[MemoryLevel] = None) -> int:
        """统计数量"""
        if level:
            return sum(1 for info in self._index.values() if info.get("level") == level.value)
        return len(self._index)


# ==================== 核心系统 ====================


class MiyaMemoryCore:
    """
    弥娅统一记忆系统核心

    这是唯一入口，所有代码都必须使用此类！
    """

    @property
    def _tag_index(self):
        """代理到 backend._tag_index，保持向后兼容"""
        return self.backend._tag_index

    @_tag_index.setter
    def _tag_index(self, value):
        self.backend._tag_index = value

    def __init__(
        self,
        data_dir: Union[str, Path] = "data/memory",
        short_term_ttl: int = 3600,
        enable_backup: bool = True,
        embedding_client=None,
    ):
        self.data_dir = Path(data_dir)
        self.short_term_ttl = short_term_ttl
        self.enable_backup = enable_backup
        self.embedding_client = embedding_client

        self.backend: JsonBackend = JsonBackend(self.data_dir)
        self.sqlite_backend = None

        self._cache: Dict[str, MemoryItem] = {}
        self._user_index: Dict[str, Set[str]] = defaultdict(set)

        self._stats = {
            "total_stored": 0,
            "total_retrieved": 0,
            "total_deleted": 0,
            "total_updated": 0,
        }

        self._loaded = False
        self._config = None
        self._load_config()

        # 批量索引写入优化
        self._index_dirty = False
        self._store_count_since_save = 0
        self._batch_save_threshold = 50  # 每50次store批量写一次index

        # 备份批量写入优化
        self._backup_buffer: List[Dict] = []
        self._backup_batch_threshold = 50  # 每50条批量flush备份

        # MemoryEnhancer（延迟加载）
        self._enhancer = None

        logger.info(f"[MiyaMemoryCore] 初始化完成, 数据目录: {self.data_dir}")

    def _load_config(self):
        """从配置文件加载记忆系统配置 - 优先 memory_config.json"""
        try:
            config_path = (Path(__file__).parent.parent / "config" / "memory_config.json")
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    mem_config = json.load(f)
                classify_config = mem_config.get("classification", {})
                if classify_config and classify_config.get("auto_classify"):
                    self._config = classify_config
                    return
        except Exception:
            pass

        try:
            from core.text_loader import get_text

            config = get_text("memory_system")
            if config and "auto_classify" in config:
                self._config = config["auto_classify"]
                return
        except Exception:
            pass

        self._config = self._get_default_classify_config()

    def _get_default_classify_config(self):
        """获取默认分类配置"""
        return {
            "strong_emotions": [
                "愤怒",
                "恐惧",
                "惊讶",
                "悲伤",
                "极度兴奋",
                "创伤",
                "崩溃",
                "绝望",
            ],
            "long_term_events": [
                "生日",
                "纪念日",
                "毕业",
                "结婚",
                "工作面试",
                "重要决定",
                "医疗诊断",
                "法律事务",
                "分手",
                "离婚",
            ],
            "important_keywords": {
                "birthday": 0.9,
                "生日": 0.9,
                "电话": 0.85,
                "手机": 0.85,
                "邮箱": 0.85,
                "email": 0.85,
                "地址": 0.8,
                "住址": 0.8,
                "微信号": 0.9,
                "QQ号": 0.85,
                "名字": 0.8,
                "我叫": 0.8,
                "过敏": 0.9,
                "病史": 0.9,
                "病情": 0.9,
                "疾病": 0.85,
            },
            "priority_tags": [
                "重要",
                "必须记住",
                "关键信息",
                "personal",
                "contact",
                "health",
            ],
            "dialogue_strong_emotions": ["极度愉快", "深度悲伤", "强烈焦虑", "崩溃"],
            "significance_threshold_for_long_term": 0.8,
            "dialogue_significance_threshold": 0.6,
            "manual_significance_threshold": 0.4,
        }

    def reload_config(self):
        """重新加载配置"""
        self._load_config()

    def _get_enhancer(self):
        """延迟加载 MemoryEnhancer"""
        if self._enhancer is None:
            try:
                from memory.memory_enhancer import MemoryEnhancer

                self._enhancer = MemoryEnhancer()
                logger.info("[MiyaMemoryCore] MemoryEnhancer 已启用")
            except Exception as e:
                logger.debug(f"[MiyaMemoryCore] MemoryEnhancer 不可用: {e}")
                self._enhancer = None
        return self._enhancer

    async def initialize(self, lazy_load: bool = True):
        """初始化 - 支持延迟加载

        Args:
            lazy_load: True=延迟加载(按需), False=启动时全量加载
        """
        if self._loaded:
            return

        logger.info("[MiyaMemoryCore] 初始化索引...")

        # 始终初始化 SQLite 后端（嵌入式，零配置）
        try:
            from memory.sqlite_backend import SQLiteBackend

            self.sqlite_backend = SQLiteBackend(str(self.data_dir / "miya_memory.db"))
            if self.sqlite_backend.enabled:
                logger.info("[MiyaMemoryCore] SQLite 后端已启用")
            else:
                logger.warning("[MiyaMemoryCore] SQLite 后端未启用，检查 text_config.json")
        except Exception as e:
            logger.debug(f"[MiyaMemoryCore] SQLite 后端初始化失败（不影响运行）: {e}")

        # 初始化真实 Embedding 客户端（绕过配置，直接使用模型池）
        await self._init_embedding_client_from_model_config()

    async def _init_embedding_client_from_model_config(self) -> None:
        """从 multi_model_config.json 初始化 Embedding 客户端

        提取为独立方法，消除 primary/fallback 路径的重复代码。
        """
        try:
            import json

            from core.embedding_client import EmbeddingClient, EmbeddingProvider

            model_config_path = Path(__file__).parent.parent / "config" / "multi_model_config.json"
            if not model_config_path.exists():
                return

            with open(model_config_path, "r", encoding="utf-8") as f:
                model_config = json.load(f)
            emb_config = model_config.get("embedding_config", {})
            models = model_config.get("models", {})

            provider_map = {
                "openai": EmbeddingProvider.OPENAI,
                "siliconflow": EmbeddingProvider.SILICONFLOW,
                "deepseek": EmbeddingProvider.DEEPSEEK,
            }

            async def _try_init(name: str, log_prefix: str) -> bool:
                if name not in models:
                    return False
                info = models[name]
                provider = provider_map.get(info.get("provider", "openai"), EmbeddingProvider.OPENAI)
                api_key = info.get("api_key", "")
                if not api_key and info.get("env_key"):
                    api_key = os.getenv(info["env_key"], "")

                self.embedding_client = EmbeddingClient(
                    provider=provider,
                    model=info["name"],
                    api_key=api_key,
                    base_url=info.get("base_url", ""),
                )
                await self.embedding_client.initialize()
                logger.info("%s%s", log_prefix, name)
                return True

            primary_name = emb_config.get("primary", "siliconflow_bge_large")
            fallback_name = emb_config.get("fallback", "")

            if await _try_init(primary_name, "[MiyaMemoryCore] 真实 Embedding 客户端已启用: "):
                return
            if fallback_name and await _try_init(fallback_name, "[MiyaMemoryCore] Embedding 使用 fallback: "):
                return
        except Exception as e:
            logger.warning("[MiyaMemoryCore] Embedding 客户端初始化失败，使用伪向量回退: %s", e)

        if lazy_load:
            self._loaded = True
            # 加载记忆锚点（核心身份和用户信息）
            await self._load_memory_anchors()
            logger.info("[MiyaMemoryCore] 延迟加载模式初始化完成")
            return

        all_ids = await self.backend.get_all_ids()

        for memory_id in all_ids:
            memory = await self.backend.load(memory_id)
            if memory:
                self._cache[memory_id] = memory
                self._user_index[memory.user_id].add(memory_id)
                for tag in memory.tags:
                    self._tag_index[tag].add(memory_id)

        self._loaded = True
        # 加载记忆锚点
        await self._load_memory_anchors()
        logger.info(f"[MiyaMemoryCore] 全量加载完成, 缓存: {len(self._cache)} 条")

    async def _load_memory_anchors(self):
        """加载记忆锚点到 MiyaMemoryCore"""
        try:
            import json
            from pathlib import Path

            project_root = Path(__file__).parent.parent
            anchor_files = [
                (
                    project_root / "data" / "memory_anchors_identity.json",
                    "弥娅",
                    "identity",
                ),
                (
                    project_root / "data" / "memory_anchors_user.json",
                    "1523878699",
                    "user",
                ),
            ]

            loaded_count = 0
            for anchor_path, user_id, anchor_type in anchor_files:
                if not anchor_path.exists():
                    continue

                with open(anchor_path, "r", encoding="utf-8") as f:
                    anchors = json.load(f)

                for anchor in anchors:
                    fact = anchor.get("fact", "")
                    tags = anchor.get("tags", [])
                    priority = anchor.get("priority", 0.95)

                    if not fact:
                        continue

                    # 检查是否已存在（避免重复加载）
                    existing = await self.retrieve(query=fact[:20], user_id=user_id, limit=1)
                    if existing and any(fact[:30] in e.content for e in existing):
                        continue

                    await self.store(
                        content=fact,
                        level=MemoryLevel.LONG_TERM,
                        priority=priority,
                        tags=tags,
                        user_id=user_id,
                        source=MemorySource.SYSTEM,
                        metadata={
                            "source": "init_anchor",
                            "anchor_type": anchor_type,
                            "importance": "high",
                        },
                    )
                    loaded_count += 1

            if loaded_count > 0:
                logger.info(f"[MiyaMemoryCore] 记忆锚点加载完成: {loaded_count} 条")
            else:
                logger.info("[MiyaMemoryCore] 记忆锚点已存在，跳过")

        except Exception as e:
            logger.warning(f"[MiyaMemoryCore] 记忆锚点加载失败: {e}")

    # ==================== 核心存储方法 ====================

    async def store(
        self,
        content: str,
        level: Optional[MemoryLevel] = None,
        priority: float = 0.5,
        tags: Optional[List[str]] = None,
        user_id: str = "global",
        session_id: str = "",
        group_id: str = "",
        platform: str = "unknown",
        source: MemorySource = MemorySource.SYSTEM,
        role: str = "",
        # 对话详情
        event_type: str = "",
        location: str = "",
        conversation_partner: str = "",
        emotional_tone: str = "",
        significance: float = 0.5,
        ttl: Optional[int] = None,
        metadata: Optional[Dict] = None,
        # 知识图谱字段
        subject: str = "",
        predicate: str = "",
        obj: str = "",
    ) -> str:
        """
        存储记忆 - 统一入口

        Args:
            content: 记忆内容
            level: 存储层级 (自动判断)
            priority: 优先级 0-1
            tags: 标签列表
            user_id: 用户ID
            session_id: 会话ID
            group_id: 群组ID
            platform: 平台
            source: 来源
            role: 角色
            event_type: 对话事件类型
            location: 对话地点
            conversation_partner: 明确的对话对象
            emotional_tone: 情感基调
            significance: 主观重要性评分 (0-1)
            ttl: 短期记忆TTL(秒)
            metadata: 元数据
            subject: 知识图谱-主体
            predicate: 知识图谱-关系
            obj: 知识图谱-客体

        Returns:
            记忆ID
        """
        # 转换层级
        if isinstance(level, str):
            try:
                level = MemoryLevel(level)
            except (ValueError, KeyError):
                level = MemoryLevel.SHORT_TERM
        elif level is None:
            level = MemoryLevel.SHORT_TERM

        # 转换来源
        if isinstance(source, str):
            try:
                source = MemorySource(source)
            except (ValueError, KeyError):
                source = MemorySource.SYSTEM

        # 自动分类
        if level is None:
            level = self._auto_classify(content, tags, source, significance, emotional_tone, event_type)

        # 计算过期时间
        expires_at = None
        if level is not None and level == MemoryLevel.SHORT_TERM:
            ttl = ttl or self.short_term_ttl
            expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()

        # 确保 user_id 和 group_id 是字符串
        user_id = str(user_id) if user_id is not None else ""
        group_id = str(group_id) if group_id is not None else ""

        # 创建记忆
        memory = MemoryItem(
            content=content,
            level=level,
            priority=priority,
            tags=tags or [],
            user_id=user_id,
            session_id=session_id,
            group_id=group_id,
            platform=platform,
            source=source,
            role=role,
            event_type=event_type,
            location=location,
            conversation_partner=conversation_partner,
            emotional_tone=emotional_tone,
            significance=significance,
            expires_at=expires_at,
            metadata=metadata or {},
            subject=subject,
            predicate=predicate,
            obj=obj,
        )

        # 保存到后端（JSON + SQLite 双写）
        await self.backend.save(memory)
        if self.sqlite_backend:
            try:
                await self.sqlite_backend.save(memory)
            except Exception as e:
                logger.debug(f"[MiyaMemoryCore] SQLite 写入失败（不影响运行）: {e}")

        # 更新缓存和索引
        self._cache[memory.id] = memory
        self._user_index[user_id].add(memory.id)
        for tag in memory.tags:
            self._tag_index[tag].add(memory.id)

        # 标记索引脏、增量计数
        self._index_dirty = True
        self._store_count_since_save += 1

        # 生成向量并同步到 SQLite（优先使用真实 embedding API）
        if level in [
            MemoryLevel.SEMANTIC,
            MemoryLevel.LONG_TERM,
            MemoryLevel.KNOWLEDGE,
        ]:
            await self._generate_and_sync_vector(memory)

        # 备份
        if self.enable_backup:
            await self._backup_memory(memory)

        # MemoryEnhancer 自动链接挖掘
        enhancer = self._get_enhancer()
        if enhancer and level in [MemoryLevel.LONG_TERM, MemoryLevel.SEMANTIC]:
            try:
                recent = list(self._cache.values())[-20:]  # 最近20条
                await enhancer.analyze_and_link(memory, recent)
            except Exception as e:
                logger.debug(f"[MiyaMemoryCore] MemoryEnhancer 链接失败: {e}")

        # 批量写入索引（每50次store或超时批量flush）
        if self._store_count_since_save >= self._batch_save_threshold:
            self._flush_index()

        self._stats["total_stored"] += 1

        logger.debug(f"[MiyaMemoryCore] 存储: {memory.id}, level={level.value}, user={user_id}")
        return memory.id

    def _flush_index(self):
        """批量刷新索引和备份到磁盘"""
        if self._index_dirty:
            self.backend._save_index()
            self._index_dirty = False
            self._store_count_since_save = 0
            logger.debug("[MiyaMemoryCore] 批量索引已刷新")
        self._flush_backup()

    async def get_daily_dialogues(self, date_key: str, user_id: Optional[str] = None) -> List[MemoryItem]:
        """获取某天的所有对话记忆（情节记忆检索）

        Args:
            date_key: 日期字符串 YYYY-MM-DD
            user_id: 可选，限制为特定用户

        Returns:
            按时间排序的对话记忆列表
        """
        from datetime import datetime as dt

        try:
            day_start = dt.strptime(date_key, "%Y-%m-%d")
            day_end = day_start.replace(hour=23, minute=59, second=59)
        except ValueError:
            return []

        query = MemoryQuery(
            levels=[MemoryLevel.DIALOGUE],
            start_time=day_start,
            end_time=day_end,
            limit=200,
            sort_by="created_at",
            sort_order="asc",
        )
        if user_id:
            query.user_id = user_id

        results = await self.retrieve(query)
        return results

    async def store_daily_summary(
        self,
        date_key: str,
        summary: str,
        user_id: str = "global",
        dialogue_count: int = 0,
    ) -> str:
        """存储每日情节摘要

        Args:
            date_key: 日期 YYYY-MM-DD
            summary: 摘要内容
            user_id: 用户ID
            dialogue_count: 对话条数

        Returns:
            记忆ID
        """
        tags = ["daily_summary", f"date:{date_key}"]
        content = f"[{date_key} 对话摘要] (共{dialogue_count}条对话)\n{summary}"

        return await self.store(
            content=content,
            level=MemoryLevel.LONG_TERM,
            priority=0.85,
            tags=tags,
            user_id=user_id,
            source=MemorySource.SYSTEM,
            metadata={
                "type": "daily_summary",
                "date": date_key,
                "dialogue_count": dialogue_count,
            },
        )

    def _auto_classify(
        self,
        content: str,
        tags: Optional[List[str]],
        source: MemorySource,
        significance: float = 0.5,
        emotional_tone: str = "",
        event_type: str = "",
    ) -> MemoryLevel:
        """自动分类 - 配置化版本"""
        cfg = self._config
        content_lower = content.lower()

        threshold = cfg.get("significance_threshold_for_long_term", 0.8)
        if significance >= threshold:
            return MemoryLevel.LONG_TERM

        for emotion in cfg.get("strong_emotions", []):
            if emotion in emotional_tone and significance >= 0.5:
                return MemoryLevel.LONG_TERM

        for event in cfg.get("long_term_events", []):
            if event in event_type:
                return MemoryLevel.LONG_TERM

        for keyword, keyword_importance in cfg.get("important_keywords", {}).items():
            if keyword in content_lower and significance >= keyword_importance - 0.2:
                return MemoryLevel.LONG_TERM

        priority_tags = set(cfg.get("priority_tags", []))
        if tags and any(t in priority_tags for t in tags):
            return MemoryLevel.LONG_TERM

        if source == MemorySource.DIALOGUE:
            if significance >= cfg.get("dialogue_significance_threshold", 0.6):
                return MemoryLevel.LONG_TERM
            for e in cfg.get("dialogue_strong_emotions", []):
                if e in emotional_tone:
                    return MemoryLevel.LONG_TERM
            return MemoryLevel.DIALOGUE

        if source == MemorySource.AUTO_EXTRACT:
            return MemoryLevel.SHORT_TERM

        if source == MemorySource.MANUAL:
            threshold = cfg.get("manual_significance_threshold", 0.4)
            return MemoryLevel.LONG_TERM if significance >= threshold else MemoryLevel.SHORT_TERM

        return MemoryLevel.SHORT_TERM

    # ==================== 检索方法 ====================

    async def retrieve(
        self,
        query: Union[str, MemoryQuery],
        level: Optional[MemoryLevel] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        group_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        # 对话详情过滤
        event_type: Optional[str] = None,
        location: Optional[str] = None,
        conversation_partner: Optional[str] = None,
        emotional_tone: Optional[str] = None,
        min_significance: float = 0.0,
        max_significance: float = 1.0,
    ) -> List[MemoryItem]:
        """
        检索记忆 - 全局检索 + 上下文加权

        弥娅的记忆是全局的，不按群/用户隔离。
        group_id 和 user_id 用于加权排序；若明确传入则同时用作过滤条件。
        """
        if isinstance(query, str):
            q = MemoryQuery(
                query=query,
                level=level,
                user_id=user_id,
                session_id=session_id,
                group_id=group_id,
                tags=tags,
                limit=limit * 3,
                event_type=event_type,
                location=location,
                conversation_partner=conversation_partner,
                emotional_tone=emotional_tone,
                min_significance=min_significance,
                max_significance=max_significance,
            )
        else:
            q = query
            # 确保后端拉取足够数据用于加权排序
            if q.limit < limit:
                q.limit = limit * 3
            if level is not None:
                q.level = level
            if user_id is not None:
                q.user_id = user_id
            if session_id is not None:
                q.session_id = session_id
            if group_id is not None:
                q.group_id = group_id
            if tags is not None:
                q.tags = tags
            if event_type is not None:
                q.event_type = event_type
            if location is not None:
                q.location = location
            if conversation_partner is not None:
                q.conversation_partner = conversation_partner
            if emotional_tone is not None:
                q.emotional_tone = emotional_tone
            if min_significance != 0.0:
                q.min_significance = min_significance
            if max_significance != 1.0:
                q.max_significance = max_significance

        # 先从缓存搜索
        results = self._search_from_cache(q)

        # 从后端搜索（优先 SQLite，回退 JSON）
        if len(results) < q.limit:
            backend_results = []
            if self.sqlite_backend:
                try:
                    backend_results = await self.sqlite_backend.query(q)
                except Exception as e:
                    logger.debug(f"[MiyaMemoryCore] SQLite 查询失败，回退 JSON: {e}")
                    backend_results = await self.backend.query(q)
            else:
                backend_results = await self.backend.query(q)

            # 合并去重
            existing_ids = {r.id for r in results if r}
            for r in backend_results:
                if r and r.id not in existing_ids:
                    results.append(r)

        # 【全局记忆加权排序】
        # 不隔离记忆，但根据上下文加权
        scored = []
        for r in results:
            score = r.priority
            # 当前群记忆加权
            if group_id and r.group_id == group_id:
                score *= 1.5
            # 当前用户记忆加权
            if user_id and r.user_id == user_id:
                score *= 1.3
            # 相关标签加权
            if tags:
                for t in tags:
                    if t in r.tags:
                        score *= 1.2
            scored.append((r, score))

        # 按加权分数排序
        scored.sort(key=lambda x: x[1], reverse=True)
        results = [r for r, _ in scored[:limit]]

        # 更新访问
        for r in results:
            r.update_access()

        self._stats["total_retrieved"] += len(results)

        return results[:limit]

    async def get_statistics(self) -> Dict:
        """获取统计"""
        sqlite_count = 0
        by_level_db = {}
        if self.sqlite_backend:
            try:
                sqlite_count = await self.sqlite_backend.count()
                by_level_db = await self.sqlite_backend.count_by_level()
            except Exception:
                pass

        return {
            "total_cached": len(self._cache),
            "total_indexed": await self.backend.count(),
            "total_sqlite": sqlite_count,
            "by_level": {
                "dialogue": len([m for m in self._cache.values() if m.level == MemoryLevel.DIALOGUE]),
                "short_term": len([m for m in self._cache.values() if m.level == MemoryLevel.SHORT_TERM]),
                "long_term": len([m for m in self._cache.values() if m.level == MemoryLevel.LONG_TERM]),
                "semantic": len([m for m in self._cache.values() if m.level == MemoryLevel.SEMANTIC]),
                "knowledge": len([m for m in self._cache.values() if m.level == MemoryLevel.KNOWLEDGE]),
            },
            "by_level_db": by_level_db,
            "by_user": len(self._user_index),
            "by_tag": len(self._tag_index),
            "stats": self._stats,
        }

    def _search_from_cache(self, query: MemoryQuery) -> List[MemoryItem]:
        """从缓存搜索 - 利用索引缩小候选集"""
        results = []

        def _candidate_ids() -> Optional[Set[str]]:
            if query.tags:
                if query.any_tag:
                    ids = set()
                    for tag in query.tags:
                        ids.update(self._tag_index.get(tag, set()))
                    return ids
                else:
                    sets = [self._tag_index.get(tag, set()) for tag in query.tags]
                    if not sets:
                        return None
                    result = sets[0]
                    for s in sets[1:]:
                        result = result & s
                    return result
            if query.user_id:
                return self._user_index.get(query.user_id, set())
            return None

        candidate_ids = _candidate_ids()

        for memory_id, memory in self._cache.items():
            if not memory.is_valid():
                continue

            if candidate_ids is not None and memory_id not in candidate_ids:
                continue

            if self._match_query(memory, query):
                results.append(memory)

        results = self._sort_results(results, query.sort_by, query.sort_order)

        return results[query.offset : query.offset + query.limit]

    def _match_query(self, memory: MemoryItem, query: MemoryQuery) -> bool:
        """匹配查询"""
        if query.user_id and memory.user_id != query.user_id:
            return False
        if query.session_id and memory.session_id != query.session_id:
            return False
        if query.group_id and memory.group_id != query.group_id:
            return False
        if query.level and memory.level != query.level:
            return False
        if query.levels and memory.level not in query.levels:
            return False
        if query.tags:
            if query.any_tag:
                if not any(tag in memory.tags for tag in query.tags):
                    return False
            else:
                if not all(tag in memory.tags for tag in query.tags):
                    return False
        if memory.priority < query.min_priority:
            return False
        if memory.priority > query.max_priority:
            return False
        if query.is_pinned is not None and memory.is_pinned != query.is_pinned:
            return False
        if not query.include_archived and memory.is_archived:
            return False
        if not query.include_expired and memory.is_expired():
            return False
        if query.query:
            q = query.query.lower()
            if q not in memory.content.lower() and not any(q in tag.lower() for tag in memory.tags):
                return False
        # 对话详情过滤
        if query.event_type and memory.event_type != query.event_type:
            return False
        if query.location and memory.location != query.location:
            return False
        if query.conversation_partner and memory.conversation_partner != query.conversation_partner:
            return False
        if query.emotional_tone and memory.emotional_tone != query.emotional_tone:
            return False
        if memory.significance < query.min_significance or memory.significance > query.max_significance:
            return False
        # 时间过滤
        if query.start_time or query.end_time:
            try:
                mem_time = datetime.fromisoformat(memory.created_at)
                if query.start_time and mem_time < query.start_time:
                    return False
                if query.end_time and mem_time > query.end_time:
                    return False
            except Exception:
                pass
        return True

    def _sort_results(self, results: List[MemoryItem], sort_by: str, order: str) -> List[MemoryItem]:
        """排序"""
        reverse = order == "desc"
        if sort_by == "priority":
            results.sort(key=lambda x: x.priority, reverse=reverse)
        elif sort_by == "created_at":
            results.sort(key=lambda x: x.created_at, reverse=reverse)
        return results

    # ==================== 便捷方法 ====================

    async def get_by_id(self, memory_id: str) -> Optional[MemoryItem]:
        """按ID获取"""
        # 先从缓存
        if memory_id in self._cache:
            return self._cache[memory_id]

        # 从后端加载
        memory = await self.backend.load(memory_id)
        if memory:
            self._cache[memory_id] = memory
        return memory

    async def get_recent(
        self,
        user_id: Optional[str] = None,
        level: Optional[MemoryLevel] = None,
        limit: int = 20,
    ) -> List[MemoryItem]:
        """获取最近的记忆"""
        q = MemoryQuery(
            user_id=user_id,
            level=level,
            limit=limit,
            sort_by="created_at",
            sort_order="desc",
        )
        return await self.retrieve(q)

    async def search_by_tag(
        self,
        tag: str,
        user_id: Optional[str] = None,
        limit: int = 20,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[MemoryItem]:
        """按标签搜索"""
        q = MemoryQuery(
            tags=[tag],
            user_id=user_id,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )
        return await self.retrieve(q)

    async def search_by_user(
        self,
        user_id: str,
        level: Optional[MemoryLevel] = None,
        limit: int = 20,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[MemoryItem]:
        """按用户搜索"""
        q = MemoryQuery(
            user_id=user_id,
            level=level,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )
        return await self.retrieve(q)

    async def get_dialogue(
        self,
        session_id: str,
        platform: Optional[str] = None,
        limit: int = 50,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        cross_platform: bool = False,
    ) -> List[MemoryItem]:
        """获取对话历史

        Args:
            session_id: 会话ID
            platform: 平台过滤（None=不过滤，跨平台检索）
            limit: 返回数量限制
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            cross_platform: 是否跨平台检索（忽略 platform 参数，全局查询）
        """
        session_pattern = session_id
        if cross_platform and session_id:
            user_suffix = session_id.split("_", 1)[-1] if "_" in session_id else session_id
            session_pattern = user_suffix

        q = MemoryQuery(
            session_id=session_id if not cross_platform else None,
            level=MemoryLevel.DIALOGUE,
            limit=limit * (3 if cross_platform else 1),
            sort_by="created_at",
            sort_order="asc",
            start_time=start_time,
            end_time=end_time,
        )
        results = await self.retrieve(q)

        if cross_platform:
            if session_pattern:
                results = [
                    r for r in results
                    if r.session_id.endswith(session_pattern) or r.user_id == session_pattern
                ]
        elif platform:
            results = [r for r in results if r.platform == platform]

        return results[:limit]

    # ==================== 更新删除 ====================

    async def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: Optional[float] = None,
        is_pinned: Optional[bool] = None,
        is_archived: Optional[bool] = None,
    ) -> bool:
        """更新记忆"""
        memory = await self.get_by_id(memory_id)
        if not memory:
            return False

        # 更新字段
        if content is not None:
            memory.content = content
        if tags is not None:
            # 更新标签索引
            for old_tag in memory.tags:
                self._tag_index[old_tag].discard(memory_id)
            memory.tags = tags
            for new_tag in memory.tags:
                self._tag_index[new_tag].add(memory_id)
        if priority is not None:
            memory.priority = priority
        if is_pinned is not None:
            memory.is_pinned = is_pinned
        if is_archived is not None:
            memory.is_archived = is_archived

        memory.updated_at = datetime.now().isoformat()

        # 保存
        await self.backend.save(memory)
        self._cache[memory_id] = memory

        self._stats["total_updated"] += 1
        return True

    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        memory = await self.get_by_id(memory_id)
        if not memory:
            return False

        if memory_id in self._cache:
            del self._cache[memory_id]

        self._user_index[memory.user_id].discard(memory_id)
        for tag in memory.tags:
            self._tag_index[tag].discard(memory_id)

        await self.backend.delete(memory_id)

        if self.sqlite_backend:
            with contextlib.suppress(Exception):
                await self.sqlite_backend.delete(memory_id)

        self._stats["total_deleted"] += 1
        return True

    # ==================== 批量操作 ====================

    async def delete_expired(self) -> int:
        """删除过期记忆 - 同时清理缓存和磁盘文件"""
        count = 0
        expired_ids = []

        # 1. 清理缓存中的过期记忆
        for memory_id, memory in list(self._cache.items()):
            if memory.is_expired():
                expired_ids.append(memory_id)

        for memory_id in expired_ids:
            await self.delete(memory_id)
            count += 1

        # 2. 扫描磁盘文件，清理过期的短期记忆
        short_term_dir = self.backend.short_term_dir
        if short_term_dir.exists():
            datetime.now()
            for file_path in short_term_dir.rglob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    memory = MemoryItem.from_dict(data)
                    if memory and memory.is_expired():
                        file_path.unlink()
                        # 从索引中移除
                        if memory.id in self.backend._index:
                            del self.backend._index[memory.id]
                        for tag in memory.tags:
                            self.backend._tag_index[tag].discard(memory.id)
                        if memory.id in self._cache:
                            del self._cache[memory.id]
                        self._user_index[memory.user_id].discard(memory.id)
                        for tag in memory.tags:
                            self._tag_index[tag].discard(memory.id)
                        count += 1
                except Exception:
                    continue

        # 保存更新后的索引
        self.backend._save_index()
        self.backend._save_tag_index()

        if count > 0:
            logger.info(f"[MiyaMemoryCore] 清理了 {count} 条过期记忆 (含磁盘)")

        return count

    async def archive_old(self, days: int = 90) -> int:
        """归档旧记忆"""
        count = 0
        cutoff = datetime.now() - timedelta(days=days)

        for memory in self._cache.values():
            if memory.level != MemoryLevel.DIALOGUE:
                continue

            try:
                created = datetime.fromisoformat(memory.created_at)
                if created < cutoff:
                    memory.is_archived = True
                    await self.backend.save(memory)
                    count += 1
            except (ValueError, TypeError):
                pass

        logger.info(f"[MiyaMemoryCore] 归档了 {count} 条旧对话")
        return count

    async def store_batch(self, memories: List[MemoryItem]) -> List[str]:
        """
        批量存储记忆

        Args:
            memories: MemoryItem列表

        Returns:
            记忆ID列表
        """
        memory_ids = []
        for memory in memories:
            try:
                memory_id = await self.store(
                    content=memory.content,
                    level=memory.level,
                    priority=memory.priority,
                    tags=memory.tags,
                    user_id=memory.user_id,
                    session_id=memory.session_id,
                    platform=memory.platform,
                    source=memory.source,
                    role=memory.role,
                    metadata=memory.metadata,
                )
                memory_ids.append(memory_id)
            except Exception as e:
                logger.warning(f"[MiyaMemoryCore] 批量存储失败: {e}")
                memory_ids.append("")
        return memory_ids

    async def delete_batch(self, memory_ids: List[str]) -> int:
        """
        批量删除记忆

        Args:
            memory_ids: 记忆ID列表

        Returns:
            成功删除的数量
        """
        count = 0
        for memory_id in memory_ids:
            try:
                if await self.delete(memory_id):
                    count += 1
            except Exception as e:
                logger.warning(f"[MiyaMemoryCore] 批量删除失败: {e}")
        return count

    async def start_cleanup_task(self, interval: int = 3600):
        """启动定时清理任务"""
        import asyncio

        async def cleanup_loop():
            while True:
                try:
                    await self.delete_expired()
                    await self.decay_low_priority_memories(days=90, threshold=0.3)
                except Exception as e:
                    logger.warning(f"[MiyaMemoryCore] 清理任务异常: {e}")
                await asyncio.sleep(interval)

        asyncio.create_task(cleanup_loop())
        logger.info(f"[MiyaMemoryCore] 定时清理任务已启动, 间隔: {interval}秒")

    async def decay_low_priority_memories(self, days: int = 90, threshold: float = 0.3) -> int:
        """
        优先级衰减 - 长时间未访问的低优先级记忆降低优先级

        Args:
            days: 天数阈值
            threshold: 优先级阈值

        Returns:
            衰减的记录数
        """
        count = 0
        cut_date = datetime.now() - timedelta(days=days)

        all_ids = await self.backend.get_all_ids()

        for memory_id in all_ids[:1000]:  # 每次处理最多1000条
            try:
                memory = await self.get_by_id(memory_id)
                if not memory:
                    continue

                # 只处理低优先级的长期记忆
                if memory.level != MemoryLevel.LONG_TERM:
                    continue
                if memory.priority >= threshold:
                    continue

                # 检查最后访问时间
                last_access = getattr(memory, "last_accessed", None)
                if not last_access:
                    continue

                try:
                    last_time = datetime.fromisoformat(last_access)
                    if last_time < cut_date:
                        # 降低优先级
                        memory.priority = max(0.1, memory.priority - 0.1)
                        await self.backend.save(memory)
                        count += 1
                except (ValueError, TypeError):
                    pass
            except (ValueError, TypeError):
                pass

        if count > 0:
            logger.info(f"[MiyaMemoryCore] 优先级衰减了 {count} 条记忆")

        return count

    # ==================== 用户画像 ====================

    async def get_user_profile(self, user_id: str) -> Dict:
        """获取用户画像"""
        memories = await self.search_by_user(user_id, limit=500)

        profile = {
            "user_id": user_id,
            "total_memories": len(memories),
            "by_level": defaultdict(int),
            "by_tag": defaultdict(int),
            "preferences": [],
            "birthdays": [],
            "contacts": [],
            "sessions": set(),
            "platforms": set(),
        }

        for mem in memories:
            profile["by_level"][mem.level.value] += 1

            for tag in mem.tags:
                profile["by_tag"][tag] += 1

            if "偏好" in mem.tags or "喜欢" in mem.tags:
                profile["preferences"].append(mem.content)
            if "生日" in mem.tags:
                profile["birthdays"].append(mem.content)
            if "联系" in mem.tags:
                profile["contacts"].append(mem.content)

            if mem.session_id:
                profile["sessions"].add(mem.session_id)
            if mem.platform:
                profile["platforms"].add(mem.platform)

        profile["by_level"] = dict(profile["by_level"])
        profile["by_tag"] = dict(profile["by_tag"])
        profile["sessions"] = list(profile["sessions"])
        profile["platforms"] = list(profile["platforms"])

        return profile

    # ==================== 同步方法 ====================

    async def _generate_and_sync_vector(self, memory: MemoryItem):
        """生成向量并同步到 SQLite"""
        try:
            vector = await self.get_embedding(memory.content)
            if vector:
                memory.vector = vector
                await self.backend.save(memory)

                if self.sqlite_backend:
                    try:
                        await self.sqlite_backend.save(memory)
                    except Exception as e:
                        logger.debug(f"[MiyaMemoryCore] SQLite 向量同步失败: {e}")

                logger.debug(f"[MiyaMemoryCore] 向量生成并同步成功: {memory.id}")
        except Exception as e:
            logger.warning(f"[MiyaMemoryCore] 向量生成失败: {e}")

    async def _backup_memory(self, memory: MemoryItem):
        """备份记忆 - 批量延迟写入，按周归档"""
        self._backup_buffer.append(memory.to_dict())

        if len(self._backup_buffer) >= self._backup_batch_threshold:
            self._flush_backup()

    def _flush_backup(self):
        """批量刷新备份到磁盘"""
        import json

        if not self._backup_buffer:
            return

        backup_dir = self.data_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        iso_year, iso_week, _ = datetime.now().isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"
        backup_file = backup_dir / f"{week_key}.json"

        try:
            existing = []
            if backup_file.exists():
                with open(backup_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)

            existing.extend(self._backup_buffer)
            self._backup_buffer.clear()

            if len(existing) > 10000:
                archive_dir = backup_dir / "archive"
                archive_dir.mkdir(parents=True, exist_ok=True)
                overflow = existing[:5000]
                existing = existing[5000:]
                archive_file = archive_dir / f"{week_key}_overflow_{len(overflow)}.json"
                with open(archive_file, "w", encoding="utf-8") as f:
                    json.dump(overflow, f, ensure_ascii=False, indent=2)
                logger.info(f"[MiyaMemoryCore] 备份溢出已归档: {archive_file}")

            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            self._cleanup_old_backups(backup_dir)
        except Exception as e:
            logger.warning(f"[MiyaMemoryCore] 备份失败: {e}")

    def _cleanup_old_backups(self, backup_dir: Path):
        """清理超过8周的备份文件"""
        try:
            from datetime import timedelta

            cutoff = datetime.now() - timedelta(weeks=8)
            for f in backup_dir.glob("*.json"):
                if f.name == "tag_index.json" or f.name == "index.json":
                    continue
                # 从文件名提取日期 (20260403.json 或 2026-W14.json)
                stem = f.stem
                try:
                    if "W" in stem:
                        # ISO周格式: 2026-W14
                        year, week = stem.split("-W")
                        # 取该周的第一天作为参考
                        from datetime import date

                        ref_date = date.fromisocalendar(int(year), int(week), 1)
                        if ref_date < cutoff.date():
                            f.unlink()
                    else:
                        # 旧格式: 20260403
                        file_date = datetime.strptime(stem, "%Y%m%d")
                        if file_date < cutoff:
                            f.unlink()
                except (ValueError, IndexError):
                    pass
        except Exception as e:
            logger.warning(f"[MiyaMemoryCore] 备份清理失败: {e}")

    def _simple_embed(self, text: str) -> List[float]:
        """生成伪向量（回退用，比纯哈希更合理）"""
        import math
        from hashlib import sha256

        dimension = 1536
        vector = [0.0] * dimension

        # 使用n-gram哈希，让相似文本产生相似向量
        words = list(text.lower())
        for i in range(len(words)):
            for n in range(1, 4):  # unigram, bigram, trigram
                if i + n <= len(words):
                    ngram = "".join(words[i : i + n])
                    digest = sha256(ngram.encode("utf-8")).digest()
                    hash_val = int.from_bytes(digest[:4], "big", signed=False)
                    # 映射到向量维度
                    idx = hash_val % dimension
                    weight = 1.0 / n  # 短n-gram权重更高
                    vector[idx] += weight

        # 归一化
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]

        return vector

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本的语义向量 - 优先使用真实 Embedding API"""
        if self.embedding_client:
            try:
                # 支持 EmbeddingClient 的 embed() 方法
                if hasattr(self.embedding_client, "embed"):
                    return await self.embedding_client.embed(text)
                # 支持 encode() 方法
                elif hasattr(self.embedding_client, "encode"):
                    return await self.embedding_client.encode(text)
                # 支持 get_embedding() 方法
                elif hasattr(self.embedding_client, "get_embedding"):
                    return await self.embedding_client.get_embedding(text)
                # 支持 OpenAI 风格的 embeddings.create()
                elif hasattr(self.embedding_client, "embeddings") and hasattr(
                    self.embedding_client.embeddings, "create"
                ):
                    resp = await self.embedding_client.embeddings.create(
                        model=self.embedding_client.model
                        if hasattr(self.embedding_client, "model")
                        else "text-embedding-3-small",
                        input=text,
                    )
                    return resp.data[0].embedding
            except Exception as e:
                logger.warning(f"[MiyaMemoryCore] Embedding API 调用失败，使用回退方案: {e}")

        # 回退：使用伪向量
        return self._simple_embed(text)

    async def semantic_search(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> List[MemoryItem]:
        """语义搜索 - 基于 SQLite 向量相似度"""
        if self.sqlite_backend:
            try:
                query_vector = await self.get_embedding(query)
                if query_vector:
                    results = await self.sqlite_backend.vector_search(
                        query_vector=query_vector,
                        user_id=user_id,
                        limit=limit,
                        threshold=threshold,
                    )
                    if results:
                        return results
            except Exception as e:
                logger.debug(f"[MiyaMemoryCore] SQLite 向量搜索失败，回退关键词搜索: {e}")

        return await self.retrieve(
            query=query,
            user_id=user_id,
            limit=limit,
        )


# ==================== 全局单例 ====================

_global_core: Optional[MiyaMemoryCore] = None


async def get_memory_core(
    data_dir: Union[str, Path] = "data/memory",
    embedding_client=None,
) -> MiyaMemoryCore:
    """获取全局核心实例 - 从 multi_model_config.json 自动加载 embedding 配置"""
    global _global_core

    if _global_core is None:
        # 自动加载 embedding 客户端
        if embedding_client is None:
            try:
                import os
                from pathlib import Path

                from core.embedding_client import (
                    EmbeddingProvider,
                    get_embedding_client,
                )

                model_config_path = Path(__file__).parent.parent / "config" / "multi_model_config.json"
                if model_config_path.exists():
                    import json

                    with open(model_config_path, "r", encoding="utf-8") as f:
                        model_config = json.load(f)

                    emb_config = model_config.get("embedding_config", {})
                    if emb_config.get("enabled"):
                        primary_model_id = emb_config.get("primary", "siliconflow_bge_large")
                        models = model_config.get("models", {})
                        model_info = models.get(primary_model_id)

                        if model_info:
                            provider_str = model_info.get("provider", "openai").lower()
                            provider_map = {
                                "openai": EmbeddingProvider.OPENAI,
                                "deepseek": EmbeddingProvider.DEEPSEEK,
                                "siliconflow": EmbeddingProvider.SILICONFLOW,
                                "sentence_transformers": EmbeddingProvider.SENTENCE_TRANSFORMERS,
                            }
                            provider = provider_map.get(provider_str, EmbeddingProvider.OPENAI)
                            model_name = model_info.get("name")
                            api_key = model_info.get("api_key", "")
                            if not api_key and model_info.get("env_key"):
                                api_key = os.getenv(model_info["env_key"], "")
                            base_url = model_info.get("base_url")

                            embedding_client = await get_embedding_client(
                                provider=provider, model=model_name, api_key=api_key
                            )
                            # 设置自定义 base_url
                            if base_url:
                                embedding_client.base_url = base_url
                            logger.info(
                                f"[MiyaMemoryCore] 自动加载 Embedding 客户端: {primary_model_id} ({model_name})"
                            )
                        else:
                            logger.warning(f"[MiyaMemoryCore] Embedding 模型 {primary_model_id} 未在模型池中找到")
                    else:
                        logger.info("[MiyaMemoryCore] Embedding 未启用，使用伪向量回退")
                else:
                    logger.warning("[MiyaMemoryCore] multi_model_config.json 不存在")
            except Exception as e:
                logger.debug(f"[MiyaMemoryCore] Embedding 客户端加载失败，使用伪向量: {e}")

        _global_core = MiyaMemoryCore(
            data_dir=data_dir,
            embedding_client=embedding_client,
        )
        await _global_core.initialize()

    return _global_core


def reset_memory_core():
    """重置全局核心"""
    global _global_core
    _global_core = None
