"""
弥娅情绪池 v2 — 专业级关键词情绪分析

三层分析：
  Layer 1: 否定处理 — "没有不开心" → 不触发 sadness
  Layer 2: 强度缩放 — "非常累" ×1.5, "有点累" ×0.6
  Layer 3: 43 条情绪规则 + 弥娅天生基调
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("miya_psyarch.emotion_pool")

# ── Layer 1: 否定词 ──
NEGATION_WORDS = {"不", "没", "没有", "不是", "并非", "别", "勿", "莫", "未", "无"}
NEGATION_SCOPE = 6  # 否定词作用范围（字符）


def _detect_negation(text: str) -> set[str]:
    """检测否定词修饰的情绪词"""
    negated = set()
    for m in re.finditer(rf"({'|'.join(NEGATION_WORDS)})\s*(.{{1,{NEGATION_SCOPE}}})", text):
        negated.add(m.group(2))
    return negated


# ── Layer 2: 强度修饰 ──
INTENSITY_AMPLIFIERS = {"非常", "特别", "太", "超级", "极其", "无比", "十分", "好", "真"}
INTENSITY_DIMINISHERS = {"有点", "稍微", "一些", "一点点", "些许", "有几分", "略"}


def _intensity_scale(text: str) -> float:
    """检测程度副词，返回缩放系数"""
    has_amp = any(w in text for w in INTENSITY_AMPLIFIERS)
    has_dim = any(w in text for w in INTENSITY_DIMINISHERS)
    if has_amp:
        return 1.5
    if has_dim:
        return 0.6
    return 1.0


# ── Layer 3: 情绪规则 (43 条) ──
EMOTION_RULES = [
    # ===== 正面 =====
    (
        ["可爱", "喜欢", "爱你", "最爱", "美", "好看", "漂亮", "帅", "迷人", "甜"],
        {"love": 0.65, "joy": 0.55, "heartbeat": 0.50, "sweetness": 0.55, "warmth": 0.50, "adoration": 0.45},
    ),
    (
        ["想你", "念你", "好久不见", "想佳", "好想你"],
        {"missing": 0.70, "longing": 0.60, "attachment": 0.55, "nostalgia": 0.50, "sweetness": 0.40},
    ),
    (
        ["哈哈", "笑死", "有趣", "好玩", "逗", "乐", "开心", "高兴", "愉快"],
        {"joy": 0.65, "playful": 0.55, "amusement": 0.60, "sweetness": 0.35},
    ),
    (
        ["谢谢", "感恩", "感谢", "多亏你", "有你真好", "安心", "踏实", "舒服"],
        {"gratitude": 0.60, "peaceful": 0.55, "happiness": 0.50, "warmth": 0.50, "security": 0.55, "contentment": 0.45},
    ),
    (
        ["加油", "努力", "冲", "拼", "坚持", "相信", "能行"],
        {"pride": 0.45, "active": 0.55, "resilient": 0.50, "caring": 0.35},
    ),
    (["晚安", "早安", "睡了", "起了", "拜拜", "再见"], {"peaceful": 0.50, "closeness": 0.55, "habitual_care": 0.50}),
    (
        ["棒", "厉害", "强", "牛", "优秀", "天才", "服", "赞"],
        {"admiration": 0.55, "pride": 0.50, "joy": 0.40, "adoration": 0.40},
    ),
    (
        ["惊喜", "礼物", "送给你", "给你", "惊喜吧"],
        {"surprise": 0.55, "joy": 0.50, "excitement": 0.50, "anticipation": 0.45},
    ),
    (
        ["温暖", "温柔", "体贴", "细心", "照顾", "感动", "暖心"],
        {"moved": 0.55, "warmth": 0.60, "gratitude": 0.50, "sweetness": 0.40},
    ),
    (["抱", "抱抱", "抱一下", "抱紧", "贴贴"], {"closeness": 0.65, "clingy": 0.50, "warmth": 0.55, "attachment": 0.55}),
    (["亲", "亲亲", "kiss", "吻"], {"love": 0.60, "sweetness": 0.55, "closeness": 0.55, "heartbeat": 0.50}),
    # ===== 负面 =====
    (
        ["累", "疲惫", "困", "没力气", "倦", "没劲", "乏力"],
        {"fatigue": 0.65, "fragile": 0.45, "dependence": 0.50, "caring": 0.55, "protectiveness": 0.40},
    ),
    (
        ["难过", "疼", "哭", "伤心", "不开心", "难受", "心碎", "心痛", "抑郁"],
        {"sadness": 0.60, "heartache": 0.65, "fragile": 0.50, "caring": 0.70, "empathy": 0.55, "comfort": 0.60},
    ),
    (
        ["烦", "讨厌", "别烦我", "走开", "一边去", "聒噪"],
        {"anger": 0.55, "frustration": 0.55, "irritable": 0.50, "defensive": 0.45, "estrangement": 0.40},
    ),
    (["生气", "怒", "火大", "气死", "忍不了", "火", "操"], {"anger": 0.65, "aggression": 0.40, "frustration": 0.55}),
    (
        ["怕", "害怕", "恐怖", "吓人", "不敢", "恐惧", "吓死"],
        {"fear": 0.55, "anxiety": 0.50, "insecurity": 0.45, "protectiveness": 0.55},
    ),
    (
        ["焦虑", "紧张", "不安", "慌", "忐忑", "担心", "压力", "崩溃"],
        {"anxiety": 0.65, "nervous": 0.55, "helpless": 0.45, "dependence": 0.50, "fragile": 0.40},
    ),
    (
        ["寂寞", "孤单", "一个人", "空荡荡", "没人", "孤独"],
        {"loneliness": 0.65, "emptiness": 0.50, "missing": 0.45, "fragile": 0.40},
    ),
    (
        ["失望", "算了", "随便", "无所谓", "不管了", "放弃", "无所谓了"],
        {"disappointment": 0.55, "passive": 0.50, "relief": 0.35, "estrangement": 0.40},
    ),
    (
        ["烦死了", "恶心", "想吐", "受不了", "快疯了"],
        {"disgust": 0.55, "frustration": 0.60, "irritable": 0.55, "aversion": 0.50},
    ),
    (["委屈", "不公平", "冤枉", "欺负"], {"grievance": 0.65, "sadness": 0.45, "helpless": 0.50, "caring": 0.50}),
    # ===== 疑问/困惑 =====
    (
        ["为什么", "怎么办", "不知道", "迷茫", "困惑", "搞不懂", "不懂", "不明白"],
        {"lost": 0.45, "helpless": 0.50, "anxiety": 0.40, "dependence": 0.55, "curiosity": 0.45},
    ),
    (["真的吗", "真的假的", "不会吧", "不是吧", "骗我", "说谎"], {"doubt": 0.55, "surprise": 0.45, "curiosity": 0.40}),
    (["什么意思", "啥意思", "没听懂", "不明白", "说清楚"], {"confusion": 0.50, "curiosity": 0.45}),
    # ===== 社交/关系 =====
    (
        ["吃醋", "你跟别人", "是不是不喜欢我了", "不理我", "冷落"],
        {"jealousy": 0.60, "jealous_playful": 0.55, "insecurity": 0.45, "attachment": 0.50},
    ),
    (
        ["别走", "别离开", "留下", "陪我", "不要丢下我"],
        {"clingy": 0.55, "dependence": 0.60, "fear": 0.40, "attachment": 0.65},
    ),
    (["过来", "靠近", "坐我旁边", "到我这儿", "近一点"], {"closeness": 0.55, "attachment": 0.50, "warmth": 0.45}),
    (["聊聊", "说说话", "谈心", "倾诉", "告诉你"], {"openness": 0.55, "trust": 0.50, "closeness": 0.45}),
    (["你别管", "离我远点", "别理我", "让我一个人"], {"estrangement": 0.55, "defensive": 0.50, "push_away": 0.45}),
    # ===== 日常 =====
    (
        ["吃饭", "饿", "好吃", "晚饭", "午饭", "早餐", "夜宵", "吃"],
        {"satisfaction": 0.40, "caring": 0.45, "warmth": 0.35},
    ),
    (["天气", "下雨", "晴天", "凉快", "热", "冷"], {"peaceful": 0.35, "curiosity": 0.30}),
    (["在吗", "在不在", "在嘛", "在不在呀"], {"anticipation": 0.40, "closeness": 0.45}),
    (["给你看", "你看", "看看这个", "瞧瞧"], {"curiosity": 0.50, "excitement": 0.40, "sharing": 0.45}),
    (["无聊", "没意思", "空虚", "乏味", "闷"], {"boredom": 0.60, "emptiness": 0.45, "passive": 0.40}),
    (["好吧", "行吧", "算了", "嗯", "哦", "啊"], {"passive": 0.35, "relief": 0.25}),  # 默许/无奈
    (["别说了", "不要说了", "不想听", "闭嘴"], {"anger": 0.45, "defensive": 0.55, "push_away": 0.50}),
    # ===== 复合/特殊 =====
    (
        ["对不起", "抱歉", "我错了", "原谅我", "别生气"],
        {"guilt": 0.50, "shame": 0.40, "relief": 0.35, "forgiveness": 0.55, "attachment": 0.40},
    ),
    (["又开心又", "又难过又", "又高兴又", "既...又", "又...又"], {"mixed_feelings": 0.55, "bitter_sweet": 0.50}),
    (["改变", "成长", "进步", "学到", "懂了", "明白了很多"], {"reflection": 0.45, "pride": 0.40, "active": 0.40}),
    (
        ["记得", "回忆", "那时候", "以前", "当年", "过去", "曾经"],
        {"nostalgia": 0.55, "reflection": 0.40, "warmth": 0.35},
    ),
    (
        ["希望", "想要", "期待", "未来", "以后", "下次", "总有一天"],
        {"hope": 0.50, "anticipation": 0.45, "active": 0.40},
    ),
    (["不敢", "怕你", "你会不会", "你不会"], {"insecurity": 0.50, "fear": 0.40, "doubt": 0.40, "dependence": 0.45}),
    # ===== 对弥娅的反馈 =====
    (
        ["弥娅真好", "弥娅好棒", "弥娅厉害", "弥娅聪明", "弥娅可爱"],
        {"pride": 0.55, "joy": 0.55, "moved": 0.50, "happiness": 0.50},
    ),
    (["弥娅傻", "弥娅笨", "弥娅不好"], {"shame": 0.40, "sadness": 0.35, "insecurity": 0.40}),
]

# ── 情绪中文映射 ──
EMOTION_CN_MAP = {
    "joy": "喜悦",
    "sadness": "悲伤",
    "fear": "恐惧",
    "anger": "愤怒",
    "surprise": "惊讶",
    "disgust": "厌恶",
    "love": "爱意",
    "attachment": "依恋",
    "missing": "思念",
    "longing": "挂念",
    "nostalgia": "怀旧",
    "heartbeat": "心动",
    "sweetness": "甜蜜",
    "warmth": "温暖",
    "caring": "关怀",
    "protectiveness": "保护欲",
    "empathy": "共情",
    "comfort": "安慰",
    "heartache": "心疼",
    "fragile": "脆弱",
    "dependence": "依赖",
    "happiness": "幸福",
    "contentment": "满足",
    "playful": "调皮",
    "amusement": "好玩",
    "frustration": "窝火",
    "irritable": "烦躁",
    "boredom": "无聊",
    "anxiety": "焦虑",
    "insecurity": "不安全",
    "helpless": "无助",
    "lost": "迷茫",
    "emptiness": "空虚",
    "doubt": "怀疑",
    "disappointment": "失望",
    "betrayal": "背叛",
    "jealousy": "嫉妒",
    "jealous_playful": "吃醋",
    "clingy": "粘人",
    "guilt": "愧疚",
    "shame": "羞耻",
    "gratitude": "感恩",
    "moved": "感动",
    "pride": "骄傲",
    "relief": "释然",
    "peaceful": "安然",
    "resilient": "坚韧",
    "active": "积极",
    "passive": "消极",
    "defensive": "防御",
    "estrangement": "疏离",
    "closeness": "亲近",
    "aggression": "攻击性",
    "forgiveness": "原谅",
    "security": "安心",
    "adoration": "倾慕",
    "habitual_care": "日常关怀",
    "loneliness": "孤单",
    "nervous": "紧张",
    "grievance": "委屈",
    "aversion": "厌恶",
    "confusion": "困惑",
    "curiosity": "好奇",
    "openness": "敞开",
    "trust": "信任",
    "push_away": "推开",
    "satisfaction": "满足",
    "sharing": "分享",
    "excitement": "兴奋",
    "anticipation": "期待",
    "admiration": "钦佩",
    "hope": "希望",
    "reflection": "反思",
    "mixed_feelings": "五味杂陈",
    "bitter_sweet": "苦甜",
    "comfort": "安慰",
}

# ── 弥娅天生基调（每句话的基础情绪）──
MIYA_BASELINE_EMOTIONS = {
    "attachment": 0.30,
    "warmth": 0.25,
    "caring": 0.20,
}


def analyze_emotions(message: str) -> dict[str, float]:
    """
    三层分层情绪分析

    Returns: {"love": 0.97, "joy": 0.55, ...}  (值 0-1)
    """
    if not message:
        return {}

    text_lower = message.lower()
    result: dict[str, float] = {}

    # Layer 1: 检测否定
    negated = _detect_negation(text_lower)

    # Layer 2: 强度缩放系数
    scale = _intensity_scale(text_lower)

    # Layer 3: 关键词匹配
    for keywords, emotions in EMOTION_RULES:
        matched = False
        for kw in keywords:
            if kw in text_lower:
                # 检查是否被否定
                if kw in negated:
                    continue
                matched = True
                break
        if matched:
            for name, value in emotions.items():
                scaled = min(1.0, round(value * scale, 4))
                result[name] = max(result.get(name, 0), scaled)

    # 弥娅天生基调
    for name, value in MIYA_BASELINE_EMOTIONS.items():
        result[name] = max(result.get(name, 0), value)

    return result


def emotions_to_state_items(emotions: dict[str, float]) -> list[dict]:
    items = []
    for name, value in sorted(emotions.items(), key=lambda x: -x[1]):
        if value < 0.12:
            continue
        cn = EMOTION_CN_MAP.get(name, name)
        items.append(
            {
                "sa_label": f"miya_emotion::{name}",
                "display_text": cn,
                "source_type": "emotion_pool",
                "family": "miya_emotion",
                "real_energy": round(min(3.0, value * 3.0), 4),
                "anchor_meta": {
                    "channel": "emotion",
                    "source": "keyword_v2",
                    "intensity": round(value, 4),
                },
            }
        )
    return items
