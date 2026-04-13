"""
工作记忆管理器 (WorkingMemoryManager)

职责：
- 工作记忆 (Working Memory)：给 AI 看的 Prompt，只保留当前正在聊的 3-5 条消息
- 话题折叠：旧话题折叠成一句话总结，不删除但降权
- 话题趋势检测 (Topic Drift Detection)：自动判断话题是否切换
- 低信息量输入检测：识别"不是"、"对的对的"等短消息
"""

import logging
import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


def _load_working_memory_config() -> dict:
    """从 text_config.json 加载工作记忆配置"""
    try:
        from pathlib import Path
        import json

        config_path = Path(__file__).parent.parent / "config" / "text_config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("working_memory", {})
    except Exception as e:
        logger.warning(f"[工作记忆] 配置加载失败: {e}")
    return {}


@dataclass
class TopicSegment:
    """话题片段"""

    topic_id: str
    keywords: List[str]
    messages: List[str]  # 原始消息列表
    summary: str = ""  # 折叠后的总结
    start_time: float = 0.0
    last_active: float = 0.0
    message_count: int = 0
    is_active: bool = True  # 是否是当前活跃话题
    weight: float = 1.0  # 话题权重 (0.0-1.0)


@dataclass
class WorkingMemoryState:
    """工作记忆状态"""

    current_topic: Optional[TopicSegment] = None
    background_topics: List[TopicSegment] = field(default_factory=list)
    recent_messages: List[str] = field(default_factory=list)
    topic_switch_count: int = 0
    last_update: float = 0.0
    # 专门保存图片/文件分析结果
    media_analysis: List[Dict[str, str]] = field(default_factory=list)


class TopicDriftDetector:
    """话题漂移检测器"""

    def __init__(self, drift_threshold: float = 0.4, window_size: int = 3):
        self.drift_threshold = drift_threshold
        self.window_size = window_size
        self._keyword_history: Dict[str, List[Set[str]]] = defaultdict(list)
        self._stopwords: Set[str] = set()
        self._load_stopwords()

    def _load_stopwords(self):
        """从配置加载停用词"""
        config = _load_working_memory_config()
        self._stopwords = set(config.get("stopwords", []))
        # 默认停用词（配置为空时使用）
        if not self._stopwords:
            self._stopwords = {
                "的",
                "了",
                "是",
                "在",
                "我",
                "你",
                "他",
                "她",
                "它",
                "有",
                "和",
                "与",
                "或",
                "但",
                "而",
                "就",
                "都",
                "也",
                "不",
                "没",
                "很",
                "太",
                "最",
                "更",
                "还",
                "又",
                "这",
                "那",
                "什么",
                "怎么",
                "为什么",
                "呢",
                "啊",
                "吧",
                "（",
                "）",
                "(",
                ")",
                "【",
                "】",
                "[",
                "]",
                "！",
                "!",
                "？",
                "?",
                "。",
                ".",
                "，",
                ",",
                "…",
                "一个",
                "一些",
                "一下",
                "一直",
                "一起",
                "一样",
                "对的对的",
                "不是",
                "是的",
                "嗯嗯",
                "哈哈",
                "呵呵",
            }

    def extract_keywords(self, text: str) -> Set[str]:
        """提取文本关键词（从配置加载停用词）"""
        words = []
        i = 0
        while i < len(text):
            for length in range(4, 1, -1):
                if i + length <= len(text):
                    word = text[i : i + length]
                    if (
                        word not in self._stopwords
                        and not word.isdigit()
                        and len(word.strip()) > 0
                    ):
                        words.append(word)
                        i += length - 1
                        break
            i += 1
        return set(words)

    def calculate_similarity(self, set1: set, set2: set) -> float:
        """计算两个关键词集合的 Jaccard 相似度"""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def detect_drift(self, group_id: str, new_message: str) -> Tuple[bool, float]:
        """
        检测话题是否漂移

        Returns:
            (是否漂移, 相似度分数)
        """
        new_keywords = self.extract_keywords(new_message)
        history = self._keyword_history[group_id]

        if len(history) < self.window_size:
            history.append(new_keywords)
            return False, 1.0

        # 计算新消息与历史窗口的平均相似度
        window = history[-self.window_size :]
        similarities = [self.calculate_similarity(new_keywords, kw) for kw in window]
        avg_similarity = sum(similarities) / len(similarities)

        # 添加新关键词到历史
        history.append(new_keywords)
        if len(history) > self.window_size * 2:
            self._keyword_history[group_id] = history[-self.window_size :]

        is_drift = avg_similarity < self.drift_threshold
        if is_drift:
            logger.info(
                f"[话题漂移] group={group_id}, 相似度={avg_similarity:.2f} < {self.drift_threshold}, "
                f"判定为话题切换"
            )

        return is_drift, avg_similarity

    def get_current_topic_keywords(self, group_id: str) -> set:
        """获取当前话题关键词"""
        history = self._keyword_history.get(group_id, [])
        if not history:
            return set()
        # 合并最近窗口的关键词
        all_keywords = set()
        for kw in history[-self.window_size :]:
            all_keywords.update(kw)
        return all_keywords

    def reset(self, group_id: str):
        """重置某个群的话题历史"""
        self._keyword_history.pop(group_id, None)


class WorkingMemoryManager:
    """
    工作记忆管理器

    架构：
    ┌─────────────────────────────────────────────────────────────┐
    │                    工作记忆管理器                            │
    ├─────────────────────────────────────────────────────────────┤
    │                                                              │
    │  ┌─────────────────────┐  ┌─────────────────────┐          │
    │  │   工作记忆           │  │   背景记忆           │          │
    │  │   (Working Memory)  │  │   (Background Memory)│          │
    │  │                     │  │                     │          │
    │  │ - 当前 3-5 条消息    │  │ - 折叠的旧话题       │          │
    │  │ - 当前活跃话题       │  │ - 话题摘要           │          │
    │  │ - 高权重            │  │ - 低权重            │          │
    │  └─────────────────────┘  └─────────────────────┘          │
    │           │                          │                      │
    │           ▼                          ▼                      │
    │  ┌─────────────────────────────────────────────┐          │
    │  │              Prompt 注入                     │          │
    │  │  [当前对话] + [背景摘要] + [话题切换提示]    │          │
    │  └─────────────────────────────────────────────┘          │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        max_recent_messages: int = 15,
        max_background_topics: int = 5,
        topic_decay_rate: float = 0.3,
        topic_switch_threshold: int = 3,
        drift_threshold: float = 0.2,
        min_messages_before_fold: int = 5,
    ):
        self.max_recent = max_recent_messages
        self.max_background = max_background_topics
        self.decay_rate = topic_decay_rate
        self.switch_threshold = topic_switch_threshold
        self.min_messages_before_fold = min_messages_before_fold

        self.drift_detector = TopicDriftDetector(drift_threshold=drift_threshold)
        self._states: Dict[str, WorkingMemoryState] = {}
        self._message_counts: Dict[str, int] = defaultdict(int)

        logger.info("[工作记忆] 管理器初始化完成")

    def _get_state(self, group_id: str) -> WorkingMemoryState:
        if group_id not in self._states:
            self._states[group_id] = WorkingMemoryState()
        return self._states[group_id]

    def add_message(
        self, group_id: str, sender: str, content: str, is_at_bot: bool = False
    ) -> Dict:
        """
        添加消息并更新工作记忆状态

        Returns:
            包含话题状态信息的字典
        """
        state = self._get_state(group_id)
        self._message_counts[group_id] += 1

        # 1. 检测话题漂移
        is_drift, similarity = self.drift_detector.detect_drift(group_id, content)

        # 2. 检测低信息量输入
        is_low_info = self._is_low_info(content)

        # 3. 更新工作记忆
        state.recent_messages.append(f"{sender}: {content}")
        if len(state.recent_messages) > self.max_recent:
            state.recent_messages = state.recent_messages[-self.max_recent :]

        # 4. 如果话题漂移且消息数足够，折叠旧话题
        if (
            is_drift
            and state.current_topic
            and self._message_counts[group_id] >= self.min_messages_before_fold
        ):
            self._fold_current_topic(state)
            state.topic_switch_count += 1

        # 5. 更新或创建当前话题
        if is_drift or state.current_topic is None:
            state.current_topic = self._create_new_topic(group_id, sender, content)
        else:
            state.current_topic.messages.append(f"{sender}: {content}")
            state.current_topic.last_active = time.time()
            state.current_topic.message_count += 1
            # 更新关键词
            state.current_topic.keywords = list(
                self.drift_detector.get_current_topic_keywords(group_id)
            )

        state.last_update = time.time()

        return {
            "is_drift": is_drift,
            "similarity": similarity,
            "is_low_info": is_low_info,
            "current_topic": state.current_topic.summary if state.current_topic else "",
            "recent_messages": state.recent_messages.copy(),
            "background_topics": [
                {"summary": t.summary, "weight": t.weight}
                for t in state.background_topics[-3:]
            ],
            "media_analysis": state.media_analysis.copy(),
        }

    def add_media_analysis(
        self,
        group_id: str,
        analysis_type: str,
        description: str,
        labels: str = "",
        source: str = "",
    ):
        """添加图片/文件分析结果到专门记忆区块"""
        state = self._get_state(group_id)
        analysis_record = {
            "type": analysis_type,  # image, file, etc
            "description": description[:500],  # 限制长度
            "labels": labels[:200] if labels else "",
            "source": source,
            "timestamp": time.time(),
        }
        state.media_analysis.append(analysis_record)
        # 只保留最近5条分析记录
        if len(state.media_analysis) > 5:
            state.media_analysis = state.media_analysis[-5:]
        # 更新最后活跃时间
        state.last_update = time.time()

    def _is_low_info(self, content: str) -> bool:
        """检测是否为低信息量输入（从配置加载）"""
        content = content.strip()
        # 短消息检测
        if len(content) <= 3:
            return True
        # 低信息量词汇检测（从配置加载）
        config = _load_working_memory_config()
        low_info_words = config.get("low_info_words", [])
        for word in low_info_words:
            if content == word:
                return True
        return False

    def _create_new_topic(
        self, group_id: str, sender: str, content: str
    ) -> TopicSegment:
        """创建新话题"""
        topic_id = hashlib.md5(f"{group_id}_{time.time()}".encode()).hexdigest()[:8]
        keywords = list(self.drift_detector.get_current_topic_keywords(group_id))

        return TopicSegment(
            topic_id=topic_id,
            keywords=keywords,
            messages=[f"{sender}: {content}"],
            summary=f"[新话题] {sender}: {content[:30]}...",
            start_time=time.time(),
            last_active=time.time(),
            message_count=1,
            is_active=True,
            weight=1.0,
        )

    def _fold_current_topic(self, state: WorkingMemoryState):
        """折叠当前话题到背景记忆"""
        if not state.current_topic:
            return

        old_topic = state.current_topic
        old_topic.is_active = False

        # 生成折叠摘要
        if old_topic.message_count > 2:
            first_msg = old_topic.messages[0] if old_topic.messages else ""
            last_msg = old_topic.messages[-1] if old_topic.messages else ""
            old_topic.summary = (
                f"[背景] 之前聊到：{first_msg[:30]}... 最后提到：{last_msg[:30]}..."
            )
        else:
            old_topic.summary = f"[背景] {' | '.join(old_topic.messages[:2])}"

        # 降低权重
        old_topic.weight = max(0.1, old_topic.weight - self.decay_rate)

        # 移入背景记忆
        state.background_topics.append(old_topic)

        # 限制背景记忆数量
        if len(state.background_topics) > self.max_background:
            state.background_topics = state.background_topics[-self.max_background :]

        logger.info(
            f"[话题折叠] 旧话题已折叠: {old_topic.summary[:50]}..., "
            f"权重={old_topic.weight:.2f}"
        )

    def build_prompt_context(self, group_id: str) -> str:
        """
        构建 Prompt 上下文（分层记忆架构）

        分层策略：
        1. 即时层（最近3条）：完整原文，让AI理解当前对话
        2. 摘要层（4-15条）：一句话摘要，保留话题脉络
        3. 话题层（15+条）：话题标签+关键词，提供背景
        """
        state = self._get_state(group_id)
        if not state.recent_messages and not state.background_topics:
            return ""

        lines = []
        total_msgs = len(state.recent_messages)

        # === 第1层：即时层（最近3条完整原文）===
        recent_count = min(3, total_msgs)
        if recent_count > 0:
            lines.append("【当前对话】")
            for msg in state.recent_messages[-recent_count:]:
                lines.append(msg)

        # === 第2层：摘要层（4-15条压缩摘要）===
        if total_msgs > 3:
            older_msgs = state.recent_messages[:-recent_count]
            # 每3条压缩为一条摘要
            summary_msgs = []
            for i in range(0, len(older_msgs), 3):
                chunk = older_msgs[i : i + 3]
                if len(chunk) == 1:
                    summary_msgs.append(chunk[0])
                else:
                    # 提取关键信息
                    senders = []
                    keywords = []
                    for msg in chunk:
                        if ":" in msg:
                            sender, content = msg.split(":", 1)
                            senders.append(sender.strip())
                            # 提取内容中的关键词（去掉语气词）
                            words = [w for w in content.strip().split() if len(w) > 1]
                            keywords.extend(words[:2])
                    unique_senders = list(dict.fromkeys(senders))
                    unique_keywords = list(dict.fromkeys(keywords))[:5]
                    if unique_senders and unique_keywords:
                        summary = f"{'/'.join(unique_senders)} 讨论了 {'/'.join(unique_keywords)}"
                    elif unique_senders:
                        summary = f"{'/'.join(unique_senders)} 聊了几句"
                    else:
                        summary = "几条短消息"
                    summary_msgs.append(f"[摘要] {summary}")

            if summary_msgs:
                lines.append("\n【近期话题】")
                lines.extend(summary_msgs[-5:])  # 最多5条摘要

        # === 第3层：话题层（背景话题）===
        if state.background_topics:
            active_topics = [t for t in state.background_topics[-3:] if t.weight > 0.15]
            if active_topics:
                lines.append("\n【之前聊过的话题】")
                for topic in active_topics:
                    lines.append(f"  - {topic.summary}")

        # === 话题关键词提示 ===
        if state.recent_messages:
            current_keywords = self.drift_detector.get_current_topic_keywords(group_id)
            if current_keywords:
                kw_str = "、".join(list(current_keywords)[:5])
                lines.append(f"\n[当前话题关键词] {kw_str}")

        # === 媒体分析记忆区块（图片/文件分析结果）===
        if state.media_analysis:
            lines.append("\n【已识别内容】")
            for analysis in state.media_analysis[-3:]:  # 最多显示最近3条
                type_emoji = "🖼️" if analysis.get("type") == "image" else "📄"
                desc = analysis.get("description", "")[:100]
                labels = analysis.get("labels", "")
                lines.append(f"  {type_emoji} {desc}")
                if labels:
                    lines.append(f"     标签: {labels}")

        return "\n".join(lines)

    def get_full_context(self, group_id: str) -> Dict:
        """获取完整上下文（用于调试或特殊查询）"""
        state = self._get_state(group_id)
        return {
            "recent_messages": state.recent_messages.copy(),
            "current_topic": {
                "summary": state.current_topic.summary if state.current_topic else "",
                "keywords": state.current_topic.keywords if state.current_topic else [],
                "message_count": state.current_topic.message_count
                if state.current_topic
                else 0,
            }
            if state.current_topic
            else None,
            "background_topics": [
                {
                    "summary": t.summary,
                    "weight": t.weight,
                    "message_count": t.message_count,
                }
                for t in state.background_topics
            ],
            "topic_switch_count": state.topic_switch_count,
        }

    def cleanup_expired(self, max_age_seconds: int = 3600):
        """清理过期的工作记忆"""
        cutoff = time.time() - max_age_seconds
        expired_groups = [
            gid for gid, state in self._states.items() if state.last_update < cutoff
        ]
        for gid in expired_groups:
            del self._states[gid]
            self.drift_detector.reset(gid)
            self._message_counts.pop(gid, None)

        if expired_groups:
            logger.debug(f"[工作记忆] 清理了 {len(expired_groups)} 个过期群记忆")


# 全局单例
_working_memory: Optional[WorkingMemoryManager] = None


def get_working_memory(**kwargs) -> WorkingMemoryManager:
    """获取工作记忆管理器单例"""
    global _working_memory
    if _working_memory is None:
        _working_memory = WorkingMemoryManager(**kwargs)
    return _working_memory
