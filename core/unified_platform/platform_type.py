"""
弥娅统一平台类型定义 (MIYA Unified Platform Type)

合并了原先分散在 4 个模块中的 PlatformType 枚举:
  - core/platform_adapter.py
  - core/platform_miya.py
  - core/platform_extended.py
  - core/platform_adapters/__init__.py

所有平台标识符现在统一由此处定义，作为弥娅唯一权威的平台类型来源。

Usage:
    from core.unified_platform.platform_type import MiyaPlatform

    MiyaPlatform.QQ            → "qq"           (QQ/NapCat)
    MiyaPlatform.QQ_OFFICIAL   → "qq_official"  (QQ 官方机器人)
    MiyaPlatform.MOBILE        → "mobile"       (手机端)
    MiyaPlatform.DISCORD       → "discord"
    ...
"""

from enum import Enum


class MiyaPlatform(str, Enum):
    """弥娅统一平台类型 — 唯一权威定义"""

    # -- QQ 系列 --
    QQ = "qq"
    QQ_OFFICIAL = "qq_official"
    QQ_WEBHOOK = "qqofficial_webhook"
    ONEBOT = "onebot"
    AIOCQHTTP = "aiocqhttp"

    # -- 国际 --
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    LINE = "line"

    # -- 国内 --
    FEISHU = "feishu"
    DINGDING = "dingding"
    WECHAT_WORK = "wechat_work"
    WECOM = "wecom"
    WECOM_AI_BOT = "wecom_ai_bot"
    WECHAT = "wechat"
    WEIXIN_OC = "weixin_oc"
    WEIXIN_OA = "weixin_official_account"
    WEIXIN_ILINK = "weixin_ilink"
    SATORI = "satori"

    # -- 社区 --
    MATRIX = "matrix"
    KOOK = "kook"
    MATTERMOST = "mattermost"
    MISSKEY = "misskey"

    # -- 内置 --
    MOBILE = "mobile"
    TERMINAL = "terminal"
    DESKTOP = "desktop"
    GENERIC = "generic"

    # -- 别名 (向后兼容) --
    LARK = "feishu"  # 飞书别名

    @classmethod
    def active_platforms(cls) -> list[str]:
        """返回弥娅当前启用的主要平台 ID 列表（用于快速迭代）"""
        return [
            cls.QQ.value,
            cls.QQ_OFFICIAL.value,
            cls.AIOCQHTTP.value,
            cls.DESKTOP.value,
            cls.MOBILE.value,
            cls.TERMINAL.value,
        ]

    @classmethod
    def qq_family(cls) -> set[str]:
        """QQ 系列平台集合"""
        return {cls.QQ.value, cls.QQ_OFFICIAL.value, cls.AIOCQHTTP.value, cls.ONEBOT.value}

    @classmethod
    def chat_platforms(cls) -> set[str]:
        """可聊天的平台（排除 terminal）"""
        return {
            v.value
            for v in cls
            if v.value not in {"terminal", "generic"}
        }


# 向后兼容别名：原 PlatformType = MiyaPlatform
PlatformType = MiyaPlatform
