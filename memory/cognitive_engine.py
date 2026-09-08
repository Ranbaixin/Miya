"""
弥娅认知检索引擎 (CognitiveEngine)

实现智能记忆检索：
- 根据当前对话动态检索相关记忆
- 多策略融合：关键词 + 向量 + 时间衰减
- 只返回最相关的记忆，减少干扰
"""

import hashlib
import json
import logging
import math
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from memory.core import MemoryItem, MemoryLevel, MemoryQuery, get_memory_core
from memory.temporal_parser import extract_temporal_keywords, parse_temporal

logger = logging.getLogger("Miya.CognitiveEngine")


def _load_cognitive_config() -> Dict[str, Any]:
    """从 text_config.json 加载 CognitiveEngine 配置（统一缓存）"""
    from memory.memory_config import get_memory_section

    return get_memory_section("cognitive_engine")


_config = _load_cognitive_config()

# 话题关键词映射（从配置加载）
TOPIC_KEYWORDS = _config.get("topic_keywords", {})

# 记忆提取触发词（从配置加载）
MEMORY_TRIGGERS = _config.get("memory_triggers", {})

# 需要忽略的无意义内容（从配置加载）
IGNORE_PATTERNS = _config.get("ignore_patterns", [])

# 记忆锚点配置（从配置加载）
MEMORY_ANCHOR_CONFIG = _config.get("memory_anchor", {})
ANCHOR_KEYWORDS = MEMORY_ANCHOR_CONFIG.get("anchor_keywords", [])
ANCHOR_TAGS = MEMORY_ANCHOR_CONFIG.get("anchor_tags", [])
PERSONAL_PATTERNS = MEMORY_ANCHOR_CONFIG.get("personal_patterns", [])
PERSONAL_QUERY_KEYWORDS = MEMORY_ANCHOR_CONFIG.get("personal_query_keywords", [])
KEYWORD_EXTRACTION_PATTERNS = MEMORY_ANCHOR_CONFIG.get("keyword_extraction_patterns", {})

# 回忆打分权重（2026-09：情绪显著性加权 + 艾宾浩斯衰减参数）
RECALL_WEIGHTS = _config.get("recall_weights", {})
EMOTIONAL_TONE_BONUS = float(RECALL_WEIGHTS.get("emotional_tone_bonus", 0.10))
HIGH_SIGNIFICANCE_BONUS = float(RECALL_WEIGHTS.get("high_significance_bonus", 0.15))
SIGNIFICANCE_THRESHOLD = float(RECALL_WEIGHTS.get("significance_threshold", 0.7))
DECAY_RATE_PER_DAY = float(RECALL_WEIGHTS.get("decay_rate_per_day", 0.05))
TIME_WEIGHT = float(RECALL_WEIGHTS.get("time_weight", 0.15))
ASSOCIATION_PER_SOURCE = int(RECALL_WEIGHTS.get("association_per_source", 2))
ASSOCIATION_TOP_N = int(RECALL_WEIGHTS.get("association_top_n", 3))


class CognitiveEngine:
    """认知检索引擎

    职责：
    - 分析当前对话主题
    - 智能检索相关记忆
    - 融合多种检索策略
    - 生成记忆上下文
    - 记忆关联度学习
    """

    def __init__(self, memory_core=None, embedding_client=None):
        """初始化认知引擎

        Args:
            memory_core: 记忆核心实例
            embedding_client: 向量嵌入客户端（用于语义相似度计算）
        """

        self.memory_core = memory_core
        self._memory_core_initialized = False
        self.embedding_client = embedding_client

        # MemoryEnhancer（记忆关联/衰减权重；惰性获取，失败降级）
        self._enhancer = None
        self._enhancer_unavailable = False

        # 记忆关联度学习
        self._co_occurrence: Dict[str, Dict[str, int]] = {}  # memory_id -> {related_id: count}
        self._access_frequency: Dict[str, int] = {}  # memory_id -> access count
        self._last_retrieved_ids: List[str] = []  # 上次检索到的记忆ID列表

        # 语义相似度缓存（避免重复计算embedding）
        self._embedding_cache: Dict[str, List[float]] = {}  # md5 hex → embedding

    def _record_co_occurrence(self, memory_ids: List[str]):
        """记录记忆共现关系，用于关联度学习"""
        for i, mid1 in enumerate(memory_ids):
            self._access_frequency[mid1] = self._access_frequency.get(mid1, 0) + 1
            for j, mid2 in enumerate(memory_ids):
                if i != j:
                    if mid1 not in self._co_occurrence:
                        self._co_occurrence[mid1] = {}
                    self._co_occurrence[mid1][mid2] = self._co_occurrence[mid1].get(mid2, 0) + 1

        # 限制共现关系表大小
        if len(self._co_occurrence) > 500:
            # 移除访问频率最低的条目
            sorted_items = sorted(
                self._co_occurrence.items(),
                key=lambda x: self._access_frequency.get(x[0], 0),
            )
            to_remove = sorted_items[:100]
            for key, _ in to_remove:
                del self._co_occurrence[key]

    def _get_relevance_boost(self, memory_id: str, current_ids: List[str]) -> float:
        """获取关联度提升分数"""
        boost = 0.0

        # 1. 共现提升：与当前检索到的记忆共现频率
        for related_id in current_ids:
            if memory_id in self._co_occurrence.get(related_id, {}):
                boost += self._co_occurrence[related_id][memory_id] * 0.05

        # 2. 频率提升：高频访问的记忆权重更高
        freq = self._access_frequency.get(memory_id, 0)
        if freq > 0:
            boost += min(0.2, freq * 0.02)

        return min(0.5, boost)  # 最多提升0.5

    async def _ensure_memory_core_initialized(self):
        """确保内存核心已初始化"""
        if not self._memory_core_initialized:
            if self.memory_core is None:
                self.memory_core = await get_memory_core()
            await self.memory_core.initialize()
            self._memory_core_initialized = True

    async def _ensure_enhancer(self):
        """惰性获取 MemoryEnhancer（记忆关联/衰减权重）

        优先复用 memory core 已初始化的实例（同一进程同一份
        memory_links.json / memory_weights.json，避免双实例互相覆盖）。
        """
        if self._enhancer is not None or self._enhancer_unavailable:
            return self._enhancer
        try:
            core_enhancer = getattr(self.memory_core, "_enhancer", None)
            if core_enhancer is not None:
                self._enhancer = core_enhancer
            else:
                from memory.memory_enhancer import get_memory_enhancer

                self._enhancer = await get_memory_enhancer()
        except Exception as e:  # noqa: BLE001 — 增强器不可用时打分走回退公式
            logger.debug(f"[认知引擎] MemoryEnhancer 不可用: {e}")
            self._enhancer_unavailable = True
        return self._enhancer

    async def _reinforce_access(self, memories: List[MemoryItem]) -> None:
        """回忆强化：检索命中的记忆更新访问计数与衰减权重（间隔重复效应）"""
        if self._enhancer is None or not memories:
            return
        try:
            await self._enhancer.on_memories_accessed([m.id for m in memories])
        except Exception as e:  # noqa: BLE001 — 强化失败不影响检索结果
            logger.debug(f"[认知引擎] 回忆强化失败: {e}")

    def _is_fuzzy_candidate(self, memory: MemoryItem) -> bool:
        """模糊片段候选：30~50 天前的旧记忆才可能以碎片形式浮现"""
        try:
            days = (datetime.now() - datetime.fromisoformat(memory.created_at)).days
        except (ValueError, TypeError):
            return False
        return 30 <= days <= 50

    async def _fetch_associations(
        self,
        sources: List[MemoryItem],
        current_topics: List[str],
        keywords: List[str],
        exclude_ids: set,
    ) -> List[tuple]:
        """联想式召回：对来源记忆查一跳关联（memory_links.json）

        每条来源记忆最多带 ASSOCIATION_PER_SOURCE 条关联；
        无链接数据时返回空列表，对检索结果零影响。
        """
        if not sources or self._enhancer is None or self.memory_core is None:
            return []

        seen = set(exclude_ids)
        associated: List[tuple] = []
        for src in sources:
            try:
                links = self._enhancer.get_related_memories(src.id)
            except Exception as e:  # noqa: BLE001 — 单条关联查询失败跳过
                logger.debug(f"[认知引擎] 关联查询失败 {src.id}: {e}")
                continue

            for link in links[:ASSOCIATION_PER_SOURCE]:
                target_id = link.get("memory_id")
                if not target_id or target_id in seen:
                    continue
                seen.add(target_id)

                try:
                    mem = await self.memory_core.get_by_id(target_id)
                except Exception:  # noqa: S112, BLE001 — 关联目标加载失败跳过该条
                    continue
                if mem is None or not mem.is_valid():
                    continue

                # 标注联想来源，build_context 渲染"（由……想起）"
                mem.metadata["recalled_via"] = (src.content or "").replace("\n", " ")[:30]
                strength = float(link.get("strength", 0.5))
                relevance = await self._calculate_relevance(mem, current_topics, keywords, "")
                # 间联想记忆按链接强度折价
                associated.append((mem, relevance * (0.6 + 0.4 * min(1.0, strength))))

        if associated:
            logger.info(f"[认知引擎] 联想召回带出 {len(associated)} 条关联记忆")
        return associated

    def _extract_topics(self, text: str) -> List[str]:
        """提取对话主题

        Args:
            text: 用户输入

        Returns:
            匹配的主题列表
        """
        text = text.lower()
        topics = []

        for topic, keywords in TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    topics.append(topic)
                    break

        return topics

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词

        Args:
            text: 用户输入

        Returns:
            关键词列表
        """
        # 简单分词
        keywords = []

        # 提取长度大于2的词
        for _topic, topic_keywords in TOPIC_KEYWORDS.items():
            for keyword in topic_keywords:
                if keyword in text:
                    keywords.append(keyword)

        # 添加触发词
        for _category, triggers in MEMORY_TRIGGERS.items():
            for trigger in triggers:
                if trigger in text:
                    keywords.append(trigger)

        # 【新增】从配置文件加载的记忆锚点关键词
        for keyword in ANCHOR_KEYWORDS:
            if keyword in text:
                keywords.append(keyword)

        # 【新增】从配置文件加载的关键词提取模式
        my_pattern = KEYWORD_EXTRACTION_PATTERNS.get("my_patterns", r"我的(\w{2,})")
        what_pattern = KEYWORD_EXTRACTION_PATTERNS.get("what_patterns", r"(\w{2,})是什么")
        when_pattern = KEYWORD_EXTRACTION_PATTERNS.get("when_patterns", r"(\w{2,})的时候")

        # 提取 "我的XXX" 模式
        my_patterns = re.findall(my_pattern, text)
        keywords.extend(my_patterns)

        # 提取 "XXX是什么" 模式
        what_patterns = re.findall(what_pattern, text)
        keywords.extend(what_patterns)

        # 提取 "XXX的时候" 模式
        when_patterns = re.findall(when_pattern, text)
        keywords.extend(when_patterns)

        return list(set(keywords))

    def _is_meaningful(self, text: str) -> bool:
        """判断内容是否有意义（值得记忆）

        Args:
            text: 对话内容

        Returns:
            是否有意义
        """
        text = text.strip()

        # 检查忽略模式
        for pattern in IGNORE_PATTERNS:
            if re.match(pattern, text):
                return False

        # 太短的内容忽略
        return not len(text) < 4

    async def _get_embedding_similarity(self, text: str, memory_content: str) -> float:
        """计算语义相似度（使用embedding）

        Args:
            text: 当前输入文本
            memory_content: 记忆内容

        Returns:
            相似度分数 0-1
        """
        if not self.embedding_client:
            return 0.0

        try:
            # 检查缓存（使用 md5 而非 Python hash()，跨进程稳定）
            text_hash = hashlib.md5(text.encode()).hexdigest()
            memory_hash = hashlib.md5(memory_content.encode()).hexdigest()

            # 获取或计算text的embedding
            if text_hash not in self._embedding_cache:
                embedding = await self.embedding_client.get_embedding(text)
                if embedding:
                    self._embedding_cache[text_hash] = embedding
            text_emb = self._embedding_cache.get(text_hash)
            if not text_emb:
                return 0.0

            # 获取或计算memory的embedding
            if memory_hash not in self._embedding_cache:
                embedding = await self.embedding_client.get_embedding(memory_content)
                if embedding:
                    self._embedding_cache[memory_hash] = embedding
            memory_emb = self._embedding_cache.get(memory_hash)
            if not memory_emb:
                return 0.0

            # 计算余弦相似度
            return self._cosine_similarity(text_emb, memory_emb)

        except Exception as e:  # noqa: BLE001 — 相似度计算失败时降级返回0分
            logger.debug(f"[认知引擎] 语义相似度计算失败: {e}")
            return 0.0

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def _calculate_relevance(
        self,
        memory: MemoryItem,
        current_topics: List[str],
        keywords: List[str],
        current_input: str = "",
    ) -> float:
        """计算记忆与当前对话的相关度

        Args:
            memory: 记忆
            current_topics: 当前话题
            keywords: 关键词
            current_input: 当前用户输入（用于语义相似度）

        Returns:
            相关度分数 0-1
        """
        score = 0.0

        # 1. 重要性权重
        score += memory.priority * 0.3

        # 2. 关键词匹配
        for keyword in keywords:
            if keyword.lower() in memory.content.lower():
                score += 0.2
                break

        # 3. 话题匹配
        for topic in current_topics:
            if topic in memory.tags:
                score += 0.3
                break

        # 4. 时间衰减（2026-09：艾宾浩斯指数衰减 + 访问强化，替换原 30 天线性衰减）
        try:
            memory_time = datetime.fromisoformat(memory.created_at)
            enhancer = self._enhancer
            if enhancer is not None:
                time_weight = enhancer.calculate_decay_weight(
                    memory.id, memory.created_at, access_count=memory.access_count
                )
            else:
                days_old = (datetime.now() - memory_time).total_seconds() / 86400
                access_relief = 1.0 + min(2.0, memory.access_count * 0.25)
                time_weight = math.exp(-DECAY_RATE_PER_DAY * days_old / access_relief)
            score += time_weight * TIME_WEIGHT
        except (ValueError, TypeError):
            score += 0.1

        # 5. 语义相似度（使用embedding）
        if current_input and self.embedding_client:
            semantic_score = await self._get_embedding_similarity(current_input, memory.content)
            score += semantic_score * 0.35  # 35%权重给语义相似度

        # 6. 情绪显著性（2026-09：带情绪/高重要性的记忆更容易被想起）
        if memory.emotional_tone:
            score += EMOTIONAL_TONE_BONUS
        if memory.significance >= SIGNIFICANCE_THRESHOLD:
            score += HIGH_SIGNIFICANCE_BONUS

        return min(1.0, score)

    async def retrieve(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        limit: int = 5,
        user_id: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> List[MemoryItem]:
        """检索相关记忆

        Args:
            user_input: 用户当前输入
            conversation_history: 对话历史（最近几条）
            limit: 返回数量限制
            user_id: 用户ID（用于过滤特定用户的记忆）
            group_id: 群ID（用于过滤特定群聊的记忆）

        Returns:
            相关记忆列表
        """
        if not user_input:
            return []

        # 确保内存核心已初始化
        await self._ensure_memory_core_initialized()

        # 惰性获取记忆增强器（艾宾浩斯衰减权重 + 联想链接）
        await self._ensure_enhancer()

        # 1. 提取当前话题和关键词
        current_topics = self._extract_topics(user_input)
        keywords = self._extract_keywords(user_input)

        # 1.5 【新增】检测时间表达式，设置时间范围过滤
        temporal_range = parse_temporal(user_input)
        temporal_keywords = extract_temporal_keywords(user_input)
        if temporal_range:
            logger.info(
                f"[认知引擎] 检测到时间表达式: {temporal_range.label} "
                f"({temporal_range.start.strftime('%Y-%m-%d')} ~ {temporal_range.end.strftime('%Y-%m-%d')})"
            )
            # 将时间关键词加入搜索词
            for tk in temporal_keywords:
                if tk not in keywords:
                    keywords.append(tk)

        logger.info(f"[认知引擎] 当前话题: {current_topics}, 关键词: {keywords[:5]}")

        # 2. 查询记忆（支持用户/群聊过滤 + 时间范围过滤）
        # 当有时间范围时，搜索所有级别（包括对话记录），不然只搜索长期/语义记忆
        if temporal_range:
            query = MemoryQuery(
                query="",
                tags=current_topics + keywords,
                levels=[
                    MemoryLevel.DIALOGUE,
                    MemoryLevel.SHORT_TERM,
                    MemoryLevel.LONG_TERM,
                    MemoryLevel.SEMANTIC,
                ],
                limit=limit * 3,
                user_id=user_id,
                group_id=group_id,
                start_time=temporal_range.start,
                end_time=temporal_range.end,
            )
        else:
            query = MemoryQuery(
                query="",
                tags=current_topics + keywords,
                limit=limit * 3,
                user_id=user_id,
                group_id=group_id,
            )

        all_memories = await self.memory_core.retrieve(query)

        # 【修复】当 group_id 过滤返回空结果时，回退到不按群过滤再查一次
        if not all_memories and group_id:
            fallback_query = MemoryQuery(
                query="",
                tags=current_topics + keywords,
                limit=limit * 3,
                user_id=user_id,
                group_id=None,
            )
            all_memories = await self.memory_core.retrieve(fallback_query)
            if all_memories:
                logger.info(f"[认知引擎] group_id({group_id})无匹配，回退到全局检索: {len(all_memories)} 条")

        # 2.5 【新增】专门搜索记忆锚点（优先级最高）
        # 如果用户输入包含个人信息相关的关键词，优先搜索记忆锚点
        user_input_lower = user_input.lower()

        # 从配置文件加载的关键词
        anchor_keywords = PERSONAL_QUERY_KEYWORDS

        # 检查是否需要搜索记忆锚点
        need_anchor_search = any(kw in user_input_lower for kw in anchor_keywords)

        # 检查是否是询问个人信息的模式（从配置文件加载）
        is_personal_query = any(pattern in user_input_lower for pattern in PERSONAL_PATTERNS)

        if need_anchor_search or is_personal_query:
            logger.info("[认知引擎] 检测到个人信息查询，优先搜索记忆锚点")

            # 搜索记忆锚点（从配置文件加载的标签）
            for tag in ANCHOR_TAGS:
                if tag in user_input_lower or tag in str(keywords):
                    anchor_query = MemoryQuery(
                        query="",
                        tags=[tag],
                        limit=limit * 2,
                        user_id=user_id,
                    )
                    anchor_results = await self.memory_core.retrieve(anchor_query)
                    if anchor_results:
                        # 记忆锚点优先级最高，直接返回
                        logger.info(f"[认知引擎] 找到 {len(anchor_results)} 条记忆锚点 (标签: {tag})")
                        await self._reinforce_access(anchor_results[:limit])
                        return anchor_results[:limit]

            # 如果标签搜索没有找到，尝试内容搜索
            for keyword in keywords:
                if len(keyword) >= 2:  # 至少2个字符
                    content_query = MemoryQuery(
                        query=keyword,
                        limit=limit * 2,
                        user_id=user_id,
                    )
                    content_results = await self.memory_core.retrieve(content_query)
                    if content_results:
                        # 过滤出包含关键词的记忆
                        filtered_results = [m for m in content_results if keyword in m.content]
                        if filtered_results:
                            logger.info(f"[认知引擎] 找到 {len(filtered_results)} 条记忆 (内容匹配: {keyword})")
                            await self._reinforce_access(filtered_results[:limit])
                            return filtered_results[:limit]

        # 3. 如果标签搜索无结果，尝试内容搜索（关键词直接匹配记忆内容）
        if not all_memories and (current_topics or keywords):
            search_terms = current_topics + keywords
            for term in search_terms:
                fallback_query = MemoryQuery(
                    query=term,
                    user_id=user_id,
                    group_id=group_id,
                    limit=limit * 2,
                    levels=(
                        [
                            MemoryLevel.DIALOGUE,
                            MemoryLevel.SHORT_TERM,
                            MemoryLevel.LONG_TERM,
                            MemoryLevel.SEMANTIC,
                        ]
                        if temporal_range
                        else None
                    ),
                    start_time=temporal_range.start if temporal_range else None,
                    end_time=temporal_range.end if temporal_range else None,
                )
                fallback_results = await self.memory_core.retrieve(fallback_query)
                if fallback_results:
                    all_memories.extend(fallback_results)
                    break  # 找到一个匹配就够了

        if not all_memories:
            return []

        # 3. 计算相关度并排序（加入关联度学习）
        scored_memories = []
        fuzzy_candidates = []  # 2026-09：低相关的 30~50 天旧记忆（模糊片段候选）
        for memory in all_memories:
            relevance = await self._calculate_relevance(memory, current_topics, keywords, user_input)
            # 关联度提升
            boost = self._get_relevance_boost(memory.id, [m.id for m in all_memories])
            relevance += boost
            if relevance > 0.1:  # 过滤低相关度
                scored_memories.append((memory, relevance))
            elif self._is_fuzzy_candidate(memory):
                fuzzy_candidates.append(memory)

        # 按相关度排序
        scored_memories.sort(key=lambda x: x[1], reverse=True)

        # 4. MMR去重（最大边际相关性）- 减少相似记忆的重复
        results = self._mmr_deduplicate(scored_memories, limit)

        # 4.2 联想式召回（2026-09）：对 MMR 后 top-N 逐条带出一跳关联记忆，二次 MMR
        associated = await self._fetch_associations(
            results[:ASSOCIATION_TOP_N],
            current_topics,
            keywords,
            exclude_ids={m.id for m in results},
        )
        if associated:
            score_by_id = {m.id: s for m, s in scored_memories}
            merged = [(m, score_by_id.get(m.id, 0.3)) for m in results] + associated
            merged.sort(key=lambda x: x[1], reverse=True)
            results = self._mmr_deduplicate(merged, limit)

        # 4.3 模糊片段（2026-09）：被阈值滤掉的 30~50 天旧记忆，≤10% 概率浮现 1 条
        if fuzzy_candidates and results and random.random() <= 0.10:
            fragment = random.choice(fuzzy_candidates)
            fragment.metadata["fuzzy_fragment"] = True
            results.append(fragment)

        # 4.5 按创建时间倒序排列（统一群聊与私聊记忆的时间线）
        results.sort(key=lambda m: m.created_at if m.created_at else "", reverse=True)

        # 5. 记录共现关系（用于关联度学习）+ 回忆强化（间隔重复）
        retrieved_ids = [m.id for m in results]
        if retrieved_ids:
            self._record_co_occurrence(retrieved_ids)
            self._last_retrieved_ids = retrieved_ids
        await self._reinforce_access(results)

        logger.info(f"[认知引擎] 检索到 {len(results)} 条相关记忆（MMR去重后）")
        if not results:
            logger.info(
                f"[认知引擎] 未找到相关记忆 (话题={current_topics}, 关键词={keywords[:5]}, 时间范围={'有' if temporal_range else '无'})"
            )

        return results

    def _mmr_deduplicate(
        self,
        scored_memories: List[tuple],
        limit: int,
        mmr_threshold: float = 0.7,
    ) -> List[MemoryItem]:
        """MMR（最大边际相关性）去重

        MMR在相关性和多样性之间取得平衡：
        - 选择相关度最高的项目
        - 同时惩罚与已选项目过于相似的项目

        Args:
            scored_memories: (MemoryItem, relevance_score) 列表
            limit: 返回数量限制
            mmr_threshold: 相似度阈值，超过则视为重复

        Returns:
            去重后的记忆列表
        """
        if len(scored_memories) <= limit:
            return [m for m, _ in scored_memories]

        selected = []
        remaining = list(scored_memories)

        while len(selected) < limit and remaining:
            best_score = -1
            best_idx = 0

            for i, (memory, relevance) in enumerate(remaining):
                # 计算与已选项目的最大相似度
                max_similarity = 0.0
                for selected_mem in selected:
                    similarity = self._calculate_similarity(memory, selected_mem)
                    max_similarity = max(max_similarity, similarity)

                # MMR公式: score = relevance - λ * similarity
                # λ = 0.5 表示在相关性和多样性之间平衡
                mmr_score = relevance - 0.5 * max_similarity

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            selected_item = remaining[best_idx][0]
            selected.append(selected_item)
            remaining.pop(best_idx)

        return selected

    def _calculate_similarity(self, mem1: MemoryItem, mem2: MemoryItem) -> float:
        """计算两条记忆的相似度（0-1之间）

        考虑因素：
        - 内容相似度（文本重叠）
        - 标签重叠度
        - 时间接近度
        - 用户/群组相关性
        """
        similarity = 0.0

        # 1. 内容相似度（简单词重叠）
        words1 = set(mem1.content.lower().split())
        words2 = set(mem2.content.lower().split())
        if words1 and words2:
            overlap = len(words1 & words2) / len(words1 | words2)
            similarity += overlap * 0.4

        # 2. 标签重叠度
        if mem1.tags and mem2.tags:
            tag_overlap = len(set(mem1.tags) & set(mem2.tags)) / max(len(mem1.tags), len(mem2.tags))
            similarity += tag_overlap * 0.3

        # 3. 用户/群组相关性
        if mem1.user_id and mem2.user_id and mem1.user_id == mem2.user_id:
            similarity += 0.2
        if mem1.group_id and mem2.group_id and mem1.group_id == mem2.group_id:
            similarity += 0.1

        return min(1.0, similarity)

    async def build_context(
        self,
        user_input: str,
        conversation_history: List[Dict] = None,
        limit: int = 5,
        user_id: Optional[str] = None,
        group_id: Optional[str] = None,
        memories: Optional[List[MemoryItem]] = None,
    ) -> str:
        """构建记忆上下文文本

        Args:
            user_input: 用户当前输入
            conversation_history: 对话历史
            limit: 记忆数量限制
            user_id: 用户ID（用于过滤特定用户的记忆）
            group_id: 群ID（用于过滤特定群聊的记忆）
            memories: 预取的结构化记忆条目（Step 6 双轨去重用）；
                     传入时跳过内部 retrieve，避免二次检索

        Returns:
            格式化的记忆上下文文本
        """
        # 确保内存核心已初始化
        await self._ensure_memory_core_initialized()

        if memories is None:
            memories = await self.retrieve(user_input, conversation_history, limit, user_id, group_id)

        if not memories:
            return ""

        lines = ["【弥娅记住的事情】"]
        lines.append("")

        # 检测是否为时间范围查询，格式化不同
        from memory.temporal_parser import parse_temporal

        has_temporal = parse_temporal(user_input) is not None

        if has_temporal:
            # 时间范围查询 → 按天分组，显示时间线
            by_date = {}
            for memory in memories:
                date_str = memory.created_at[:10]  # YYYY-MM-DD
                time_str = memory.created_at[11:16] if len(memory.created_at) > 10 else ""
                if date_str not in by_date:
                    by_date[date_str] = []
                entry = f"[{time_str}]" if time_str else ""
                role_tag = ""
                if memory.role == "user":
                    role_tag = f"{getattr(memory, 'sender_name', '') or '用户'}说: "
                elif memory.role == "assistant":
                    role_tag = "弥娅说: "
                by_date[date_str].append(f"    {entry} {role_tag}{memory.content[:120]}")

            for date_str, entries in sorted(by_date.items()):
                lines.append(f"【{date_str}】")
                for entry in entries[:8]:  # 每天最多8条
                    lines.append(entry)
                lines.append("")
        else:
            # 普通查询 → 2026-09 回忆模糊化：按相关度分档措辞
            current_topics = self._extract_topics(user_input)
            keywords = self._extract_keywords(user_input)
            for memory in memories:
                content_preview = memory.content.replace("\n", " ")[:150]
                when = self._humanize_time(memory.created_at)

                relevance = 0.0
                try:
                    relevance = await self._calculate_relevance(memory, current_topics, keywords, "")
                except Exception:  # noqa: BLE001 — 打分失败按最低确定度措辞
                    relevance = 0.0

                via = ""
                if memory.metadata and memory.metadata.get("recalled_via"):
                    via = f"（由「{memory.metadata['recalled_via']}」想起）"

                if memory.metadata and memory.metadata.get("fuzzy_fragment"):
                    lines.append(f"- （很模糊的记忆碎片）好像{when}……{content_preview}，记不太清了{via}")
                elif relevance >= 0.75:
                    lines.append(f"- {when}：{content_preview}{via}")
                elif relevance >= 0.5:
                    lines.append(f"- 印象里{when}的事：{content_preview}{via}")
                else:
                    lines.append(f"- 好像{when}……{content_preview}（不太确定）{via}")

        lines.append("")
        lines.append("（这些都是之前对话中记住的重要事情，与当前对话可能相关）")

        return "\n".join(lines)

    @staticmethod
    def _humanize_time(created_at: str) -> str:
        """时间戳 → 人类口吻的时间措辞（今天/昨天/上周/去年夏天左右……）"""
        try:
            t = datetime.fromisoformat(created_at)
        except (ValueError, TypeError):
            return created_at[:10] if len(created_at) >= 10 else "以前"

        now = datetime.now()
        days = (now - t).days
        if days <= 0:
            return "今天"
        if days == 1:
            return "昨天"
        if days <= 3:
            return "前几天"
        if days <= 10:
            return "上周"
        if days <= 40:
            return "上个月"

        seasons = {
            12: "冬",
            1: "冬",
            2: "冬",
            3: "春",
            4: "春",
            5: "春",
            6: "夏",
            7: "夏",
            8: "夏",
            9: "秋",
            10: "秋",
            11: "秋",
        }
        season = seasons.get(t.month, "")
        if t.year == now.year:
            return f"今年{season}天左右"
        if t.year == now.year - 1:
            return f"去年{season}天左右"
        return f"{t.year}年左右"

    async def should_remember(self, user_input: str, ai_response: str) -> tuple[bool, str, float]:
        """判断是否应该记忆这段对话

        Args:
            user_input: 用户输入
            ai_response: AI回复

        Returns:
            (是否记忆, 记忆内容, 重要程度)
        """
        combined = user_input + " " + ai_response

        # 1. 检查是否有意义
        if not self._is_meaningful(user_input):
            return False, "", 0.0

        # 2. 检查是否包含触发词
        importance = 0.3  # 基础重要性

        for category, triggers in MEMORY_TRIGGERS.items():
            for trigger in triggers:
                if trigger in combined:
                    if category == "important_info":
                        importance = 0.9
                    elif category == "commitment":
                        importance = 0.8
                    elif category == "emotion_change":
                        importance = 0.7
                    elif category == "habit":
                        importance = 0.6
                    break

        # 3. 如果有关键词匹配，提高重要性
        keywords = self._extract_keywords(user_input)
        if len(keywords) >= 2:
            importance = min(1.0, importance + 0.2)

        # 4. 提取需要记忆的内容
        memory_content = self._extract_memory_fact(user_input, ai_response)

        if not memory_content:
            return False, "", 0.0

        return True, memory_content, importance

    def _extract_memory_fact(self, user_input: str, ai_response: str) -> str:
        """提取需要记忆的事实

        Args:
            user_input: 用户输入
            ai_response: AI回复

        Returns:
            记忆内容
        """
        # 提取用户陈述的事实
        for trigger in MEMORY_TRIGGERS["important_info"]:
            if trigger in user_input:
                # 提取触发词后的内容
                idx = user_input.find(trigger)
                fact = user_input[idx:].strip()
                # 截取到句号或问号
                for end in ["。", "？", "！", "\n"]:
                    if end in fact:
                        fact = fact[: fact.find(end)]
                if len(fact) > 3:
                    return fact

        # 提取习惯
        for trigger in MEMORY_TRIGGERS["habit"]:
            if trigger in user_input:
                idx = user_input.find(trigger)
                fact = user_input[idx:].strip()
                for end in ["。", "？", "！", "\n"]:
                    if end in fact:
                        fact = fact[: fact.find(end)]
                if len(fact) > 3:
                    return fact

        # 如果没有匹配，返回用户输入作为潜在记忆内容
        if len(user_input) > 5:
            return user_input[:100]  # 限制长度

        return ""


# 单例实例
_cognitive_engine: Optional[CognitiveEngine] = None


def get_cognitive_engine() -> CognitiveEngine:
    """获取认知引擎单例实例"""
    global _cognitive_engine
    if _cognitive_engine is None:
        _cognitive_engine = CognitiveEngine(embedding_client=None)
    return _cognitive_engine
