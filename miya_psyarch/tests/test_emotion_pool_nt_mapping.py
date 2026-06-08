"""测试情绪池 → NT 通道联动映射"""

import pytest
from miya_psyarch.emotion_pool import analyze_emotions, EMOTION_CN_MAP


def test_analyze_positive_emotions():
    result = analyze_emotions("我好想你，真的好喜欢你")
    assert result
    assert result.get("missing", 0) > 0.3
    assert result.get("love", 0) > 0.3


def test_analyze_negative_emotions():
    result = analyze_emotions("我好累，有点不开心")
    assert result
    assert result.get("fatigue", 0) > 0.3
    assert result.get("sadness", 0) > 0.1


def test_analyze_neutral_greeting():
    result = analyze_emotions("晚安，早点休息")
    assert result
    assert result.get("peaceful", 0) > 0.2


def test_analyze_surprise():
    result = analyze_emotions("真的吗？好惊讶")
    assert result
    assert result.get("surprise", 0) > 0.2


def test_analyze_closeness():
    result = analyze_emotions("抱抱你")
    assert result
    assert result.get("closeness", 0) > 0.4


def test_analyze_curiosity():
    result = analyze_emotions("为什么？不懂啊")
    assert result
    assert result.get("lost", 0) > 0.2 or result.get("curiosity", 0) > 0.2


def test_analyze_jealousy():
    result = analyze_emotions("你是不是不喜欢我了")
    assert result
    assert result.get("jealousy", 0) > 0.2 or result.get("insecurity", 0) > 0.2


def test_analyze_attachment():
    result = analyze_emotions("别走，留下来陪我")
    assert result
    assert result.get("clingy", 0) > 0.3 or result.get("attachment", 0) > 0.4


def test_analyze_miya_praise():
    result = analyze_emotions("弥娅真好，弥娅好棒")
    assert result
    assert result.get("pride", 0) > 0.2 or result.get("joy", 0) > 0.2


def test_analyze_gratitude():
    result = analyze_emotions("谢谢你，有你在真好")
    assert result
    assert result.get("gratitude", 0) > 0.3


def test_negation_handling():
    result = analyze_emotions("没有不开心")
    assert result.get("sadness", 0) < 0.3


def test_emotion_cn_map_complete():
    expected = {
        "love",
        "attachment",
        "missing",
        "longing",
        "nostalgia",
        "heartbeat",
        "sweetness",
        "warmth",
        "caring",
        "protectiveness",
        "empathy",
        "comfort",
        "happiness",
        "contentment",
        "playful",
        "amusement",
        "boredom",
        "anxiety",
        "insecurity",
        "helpless",
        "lost",
        "emptiness",
        "doubt",
        "disappointment",
        "jealousy",
        "clingy",
        "guilt",
        "shame",
        "gratitude",
        "moved",
        "pride",
        "relief",
        "peaceful",
        "active",
        "passive",
        "defensive",
        "estrangement",
        "closeness",
        "aggression",
        "forgiveness",
        "security",
        "adoration",
        "habitual_care",
        "loneliness",
        "nervous",
        "grievance",
        "aversion",
        "confusion",
        "curiosity",
        "openness",
        "trust",
        "push_away",
        "satisfaction",
        "sharing",
        "excitement",
        "anticipation",
        "admiration",
        "hope",
        "reflection",
        "mixed_feelings",
        "bitter_sweet",
        "heartache",
        "fragile",
        "dependence",
        "irritable",
        "frustration",
        "sadness",
        "fear",
        "anger",
        "surprise",
        "disgust",
        "joy",
        "jealous_playful",
        "resilient",
    }
    missing = expected - set(EMOTION_CN_MAP.keys())
    assert not missing, f"EMOTION_CN_MAP 缺少: {missing}"


def test_intensity_amplifier():
    normal = analyze_emotions("我累")
    amplified = analyze_emotions("我非常累")
    assert normal.get("fatigue", 0) < amplified.get("fatigue", 0)


def test_intensity_diminisher():
    normal = analyze_emotions("我难过")
    diminished = analyze_emotions("我有点难过")
    assert normal.get("sadness", 0) > diminished.get("sadness", 0)
