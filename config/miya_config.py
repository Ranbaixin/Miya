"""
弥娅系统 v5.0 - 配置文件
"""

# 平台配置
ADAPTERS = {
    "qq": {"enabled": False, "type": "onebot"},
    "telegram": {"enabled": False, "token": ""},
    "discord": {"enabled": False, "token": ""},
    "terminal": {"enabled": True},
}

# AI 提供商配置
PROVIDERS = {
    "default": "openai",
    "openai": {"model": "gpt-4o", "api_key": ""},
    "deepseek": {"model": "deepseek-chat", "api_key": ""},
}

# 知识库配置
KNOWLEDGE = {
    "enabled": False,
    "top_k": 5,
}

# 工具配置
TOOLS = {
    "enabled": True,
    "max_concurrent": 3,
}

# 消息流水线
PIPELINE = {
    "enabled": True,
    "stages": [
        "preprocess",
        "whitelist",
        "safety",
        "rate_limit",
        "wake",
        "session",
        "process",
        "response",
        "decorate",
    ],
}

# 计算机工具
COMPUTER = {
    "enabled": True,
    "timeout": 30,
    "allowed_dirs": ["./workspace"],
}

# 数据库
DATABASE = {
    "path": "./data/miya.db",
}

# 系统配置
SYSTEM = {
    "name": "弥娅",
    "version": "5.0",
    "mode": "unified",
    "log_level": "INFO",
}

__all__ = [
    "ADAPTERS",
    "PROVIDERS",
    "KNOWLEDGE",
    "TOOLS",
    "PIPELINE",
    "COMPUTER",
    "DATABASE",
    "SYSTEM",
]
