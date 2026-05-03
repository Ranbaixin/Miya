"""
================================================================
        弥娅多平台配置中心 (MIYA Multi-Platform Config)
================================================================

支持的平台列表 (共18个):
  - QQ 官方机器人 (qqofficial)
  - QQ 官方 Webhook (qqofficial_webhook)
  - Telegram (telegram)
  - Discord (discord)
  - 飞书 (lark)
  - 钉钉 (dingtalk)
  - 企业微信 (wecom)
  - 企业微信 AI Bot (wecom_ai_bot)
  - 微信开放平台 (weixin_oc)
  - 微信公众号 (weixin_official_account)
  - Slack (slack)
  - LINE (line)
  - KOOK (kook)
  - Mattermost (mattermost)
  - Misskey (misskey)
  - Satori (satori)
  - 网页聊天 (webchat)
  - OneBot/NapCat (aiocqhttp)

使用方法:
  1. 在对应平台申请机器人凭证
  2. 将 enabled 设为 True
  3. 填入凭证信息
  4. 运行 python start_platforms.py 启动所有平台

作者: 编程大师
================================================================
"""

# ==================== QQ 官方机器人 ====================
# 申请地址: https://q.qq.com/
# 文档: https://bot.q.qq.com/wiki/develop/api/
#
# 支持两种配置方式:
#   方式1: 使用 appid + secret (推荐，功能更全)
#   方式2: 使用 token (格式: bot:v1_xxx)
#
# 功能: 群聊、C2C私聊、频道消息、频道私信

QQ_OFFICIAL_CONFIG = {
    "enabled": True,
    # 方式1: appid + secret (推荐)
    "appid": "1903922226",
    "secret": "ulU0JPIQSHsHSP9f",
    # 方式2: token (如果方式1不行，取消注释下面这行)
    # "token": "bot:v1_xxx",
    # 机器人QQ号
    "bot_qq": "4015699176",
    # 功能开关
    "enable_group_c2c": True,  # 启用群聊和C2C消息
    "enable_guild_direct_message": True,  # 启用频道私信
    "sandbox": False,  # 沙箱环境（测试用）
}

# ==================== QQ 官方 Webhook 模式 ====================
# 申请地址: https://q.qq.com/
# 说明: 使用 Webhook 方式接收消息，无需保持长连接
# 适合: 服务器部署、无固定IP环境

QQ_OFFICIAL_WEBHOOK_CONFIG = {
    "enabled": False,
    "appid": "",
    "secret": "",
    "token": "",
    "bot_qq": "",
    # Webhook 回调地址 (需要公网可访问)
    "callback_url": "https://your-domain.com/qq/webhook",
    # 验证 Token
    "verify_token": "",
    # 沙箱模式
    "sandbox": False,
}

# ==================== Telegram ====================
# 申请地址: https://t.me/BotFather
# 步骤: 发送 /newbot -> 获取 bot_token
# 文档: https://core.telegram.org/bots/api
#
# 功能: 私聊、群组、频道、内联查询

TELEGRAM_CONFIG = {
    "enabled": False,
    "bot_token": "",  # 格式: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    # 可选: 使用代理 (中国大陆可能需要)
    # "proxy": {
    #     "type": "http",  # http, socks5
    #     "host": "127.0.0.1",
    #     "port": 7890,
    # },
}

# ==================== Discord ====================
# 申请地址: https://discord.com/developers/applications
# 步骤: 创建应用 -> Bot -> 获取 Token
# 文档: https://discord.com/developers/docs/intro
#
# 功能: 服务器消息、私信、斜杠命令

DISCORD_CONFIG = {
    "enabled": False,
    "bot_token": "",  # 你的 Bot Token
    # 可选: 设置 intents
    # "intents": ["guilds", "guild_messages", "direct_messages"],
}

# ==================== 飞书 ====================
# 申请地址: https://open.feishu.cn/
# 步骤: 创建企业自建应用 -> 获取 app_id 和 app_secret
# 文档: https://open.feishu.cn/document/home/index
#
# 功能: 单聊、群聊、消息卡片

FEISHU_CONFIG = {
    "enabled": False,
    "app_id": "",  # 应用 App ID
    "app_secret": "",  # 应用 App Secret
    # 可选: 事件回调验证
    # "verification_token": "",
    # "encrypt_key": "",
}

# ==================== 钉钉 ====================
# 申请地址: https://open.dingtalk.com/
# 步骤: 创建应用 -> 获取 app_key 和 app_secret
# 文档: https://open.dingtalk.com/document
#
# 功能: 单聊、群聊、工作通知

DINGDING_CONFIG = {
    "enabled": False,
    "app_key": "",  # 应用 App Key
    "app_secret": "",  # 应用 App Secret
    # 可选: 机器人 Webhook
    # "webhook": "",
    # "secret": "",
}

# ==================== 企业微信 ====================
# 申请地址: https://work.weixin.qq.com/
# 步骤: 创建应用 -> 获取 corpid 和 corpsecret
# 文档: https://developer.work.weixin.qq.com/document/path/90556
#
# 功能: 应用消息、群机器人

WECOM_CONFIG = {
    "enabled": False,
    "corpid": "",  # 企业 ID
    "corpsecret": "",  # 应用 Secret
    # 可选: 应用 AgentId
    # "agent_id": "",
}

# ==================== 企业微信 AI Bot ====================
# 申请地址: https://work.weixin.qq.com/
# 说明: 企业微信 AI 机器人模式
# 文档: https://developer.work.weixin.qq.com/document/path/95903

WECOM_AI_BOT_CONFIG = {
    "enabled": False,
    "corpid": "",
    "corpsecret": "",
    "bot_token": "",
    "encoding_aes_key": "",
}

# ==================== 微信开放平台 ====================
# 申请地址: https://open.weixin.qq.com/
# 步骤: 创建网站应用 -> 获取 appid 和 secret
# 文档: https://open.weixin.qq.com/cgi-bin/showdocument
#
# 功能: 微信扫码登录、微信消息

WEIXIN_OC_CONFIG = {
    "enabled": False,
    "appid": "",  # 应用 AppID
    "secret": "",  # 应用 AppSecret
    # 可选: 消息加解密
    # "token": "",
    # "encoding_aes_key": "",
}

# ==================== 微信公众号 ====================
# 申请地址: https://mp.weixin.qq.com/
# 步骤: 注册公众号 -> 开发 -> 基本配置
# 文档: https://developers.weixin.qq.com/doc/offiaccount/GettingStarted/
#
# 功能: 关注回复、消息自动回复、菜单

WEIXIN_OFFICIAL_CONFIG = {
    "enabled": False,
    "appid": "",  # 公众号 AppID
    "secret": "",  # 公众号 AppSecret
    "token": "",  # 服务器配置 Token
    "encoding_aes_key": "",  # 消息加解密密钥
}

# ==================== Slack ====================
# 申请地址: https://api.slack.com/apps
# 步骤: Create New App -> Bot Token Scopes -> Install
# 文档: https://api.slack.com/start/building
#
# 功能: 频道消息、私信、斜杠命令

SLACK_CONFIG = {
    "enabled": False,
    "bot_token": "",  # xoxb-开头的 Bot Token
    # 可选: App Token (用于 Socket Mode)
    # "app_token": "",
}

# ==================== LINE ====================
# 申请地址: https://developers.line.biz/console/
# 步骤: 创建 Channel -> Messaging API -> 获取 Token
# 文档: https://developers.line.biz/en/docs/messaging-api/overview/
#
# 功能: 单聊、群聊、Rich Menu

LINE_CONFIG = {
    "enabled": False,
    "channel_access_token": "",  # 长期 Channel Access Token
    "channel_secret": "",  # Channel Secret
}

# ==================== KOOK ====================
# 申请地址: https://developer.kookapp.cn/
# 步骤: 创建应用 -> 获取 token
# 文档: https://developer.kookapp.cn/doc/intro
#
# 功能: 频道消息、私信、卡片消息

KOOK_CONFIG = {
    "enabled": False,
    "token": "",  # Bot Token
    # 可选: Webhook 模式
    # "webhook_verify_key": "",
}

# ==================== Mattermost ====================
# 申请地址: 自建服务器管理后台
# 步骤: System Console -> Integrations -> Bot Accounts
# 文档: https://developers.mattermost.com/integrate/reference/
#
# 功能: 频道消息、私信

MATTERMOST_CONFIG = {
    "enabled": False,
    "server_url": "",  # Mattermost 服务器地址
    "token": "",  # Bot Access Token
    # 可选: 团队和频道
    # "team": "",
    # "channel": "",
}

# ==================== Misskey ====================
# 申请地址: Misskey 实例管理后台
# 步骤: 设置 -> 开发者 -> 创建应用
# 文档: https://misskey-hub.net/docs/
#
# 功能: 时间线、私信、通知

MISSKEY_CONFIG = {
    "enabled": False,
    "instance_url": "",  # Misskey 实例地址 (如: https://misskey.io)
    "token": "",  # Access Token
}

# ==================== Satori ====================
# 说明: Satori 是通用聊天平台协议
# 文档: https://satori.js.org/zh-CN/
#
# 支持: Koishi、OneBot、Telegram 等多种协议

SATORI_CONFIG = {
    "enabled": False,
    "host": "127.0.0.1",
    "port": 5500,
    # 可选: 认证
    # "token": "",
}

# ==================== 网页聊天 ====================
# 说明: 内置的网页聊天界面，无需申请
# 访问: http://localhost:8080

WEBCHAT_CONFIG = {
    "enabled": True,
    "port": 8080,
    # 可选: 主题和语言
    # "theme": "default",
    # "language": "zh-CN",
}

# ==================== OneBot / NapCat ====================
# 说明: 使用 OneBot v11 协议连接 NapCat/go-cqhttp
# NapCat: https://github.com/NapNeko/NapCatQQ
# go-cqhttp: https://github.com/Mrs4s/go-cqhttp
#
# 功能: 群聊、私聊、消息段、闪照、撤回
#
# 注意: 此平台通过 run/qq_main.py 单独启动
# 配置在 config/.env 中

AIOCQHTTP_CONFIG = {
    "enabled": True,
    # WebSocket 反向连接地址 (NapCat 连接到弥娅)
    "ws_reverse_host": "127.0.0.1",
    "ws_reverse_port": 8095,
    # 或者正向连接 (弥娅连接到 NapCat)
    # "ws_url": "ws://127.0.0.1:3001",
    # 访问令牌
    "token": "",
}


# =================================================================
#                      平台汇总配置
# =================================================================

ALL_PLATFORMS = {
    # QQ 系列
    "qqofficial": QQ_OFFICIAL_CONFIG,
    "qqofficial_webhook": QQ_OFFICIAL_WEBHOOK_CONFIG,
    "aiocqhttp": AIOCQHTTP_CONFIG,
    # 国际平台
    "telegram": TELEGRAM_CONFIG,
    "discord": DISCORD_CONFIG,
    "slack": SLACK_CONFIG,
    "line": LINE_CONFIG,
    # 国内平台
    "lark": FEISHU_CONFIG,
    "dingtalk": DINGDING_CONFIG,
    "wecom": WECOM_CONFIG,
    "wecom_ai_bot": WECOM_AI_BOT_CONFIG,
    "weixin_oc": WEIXIN_OC_CONFIG,
    "weixin_official_account": WEIXIN_OFFICIAL_CONFIG,
    # 社区平台
    "kook": KOOK_CONFIG,
    "mattermost": MATTERMOST_CONFIG,
    "misskey": MISSKEY_CONFIG,
    "satori": SATORI_CONFIG,
    # 内置平台
    "webchat": WEBCHAT_CONFIG,
}


def get_enabled_platforms():
    """获取所有启用的平台"""
    return {
        platform_id: config
        for platform_id, config in ALL_PLATFORMS.items()
        if config.get("enabled", False)
    }


def get_platform_config(platform_id: str):
    """获取指定平台的配置"""
    return ALL_PLATFORMS.get(platform_id, {})


def list_all_platforms():
    """列出所有可用平台及其状态"""
    result = []
    for platform_id, config in ALL_PLATFORMS.items():
        status = "✅ 已启用" if config.get("enabled", False) else "❌ 未启用"
        result.append(
            {
                "id": platform_id,
                "status": status,
                "enabled": config.get("enabled", False),
            }
        )
    return result


# =================================================================
#                      平台申请指南
# =================================================================

PLATFORM_GUIDE = {
    "qqofficial": {
        "name": "QQ 官方机器人",
        "url": "https://q.qq.com/",
        "credentials": ["appid", "secret"],
        "docs": "https://bot.q.qq.com/wiki/develop/api/",
    },
    "telegram": {
        "name": "Telegram",
        "url": "https://t.me/BotFather",
        "credentials": ["bot_token"],
        "docs": "https://core.telegram.org/bots/api",
    },
    "discord": {
        "name": "Discord",
        "url": "https://discord.com/developers/applications",
        "credentials": ["bot_token"],
        "docs": "https://discord.com/developers/docs/intro",
    },
    "lark": {
        "name": "飞书",
        "url": "https://open.feishu.cn/",
        "credentials": ["app_id", "app_secret"],
        "docs": "https://open.feishu.cn/document/home/index",
    },
    "dingtalk": {
        "name": "钉钉",
        "url": "https://open.dingtalk.com/",
        "credentials": ["app_key", "app_secret"],
        "docs": "https://open.dingtalk.com/document",
    },
    "wecom": {
        "name": "企业微信",
        "url": "https://work.weixin.qq.com/",
        "credentials": ["corpid", "corpsecret"],
        "docs": "https://developer.work.weixin.qq.com/document/path/90556",
    },
    "slack": {
        "name": "Slack",
        "url": "https://api.slack.com/apps",
        "credentials": ["bot_token"],
        "docs": "https://api.slack.com/start/building",
    },
    "line": {
        "name": "LINE",
        "url": "https://developers.line.biz/console/",
        "credentials": ["channel_access_token", "channel_secret"],
        "docs": "https://developers.line.biz/en/docs/messaging-api/overview/",
    },
    "kook": {
        "name": "KOOK",
        "url": "https://developer.kookapp.cn/",
        "credentials": ["token"],
        "docs": "https://developer.kookapp.cn/doc/intro",
    },
    "mattermost": {
        "name": "Mattermost",
        "url": "自建服务器",
        "credentials": ["server_url", "token"],
        "docs": "https://developers.mattermost.com/integrate/reference/",
    },
    "misskey": {
        "name": "Misskey",
        "url": "Misskey 实例",
        "credentials": ["instance_url", "token"],
        "docs": "https://misskey-hub.net/docs/",
    },
}


def get_platform_guide(platform_id: str = None):
    """获取平台申请指南"""
    if platform_id:
        return PLATFORM_GUIDE.get(platform_id)
    return PLATFORM_GUIDE
