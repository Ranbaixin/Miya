# MIYA Platform 切换指南

## 概述

MIYA 系统支持两套 Platform 系统：

| 系统 | 路径 | 状态 | 支持平台 |
|------|------|------|----------|
| MIYA Platform | `core/platform_miya.py` | ✅ 推荐 | QQ, Telegram, Discord, 飞书等 |
| AstrBot Platform | `core/platform_astrbot/` | ⚠️ 兼容 | 18+ 平台 (70+ 适配器) |

---

## 快速切换

### 方法 1: 使用 MIYA 自己的 Platform (推荐)

```python
from core.platform_miya import PlatformManager, QQAdapter, TelegramAdapter

# 创建平台管理器
manager = PlatformManager()

# 注册适配器
manager.register_adapter("qq", QQAdapter())
manager.register_adapter("telegram", TelegramAdapter())

# 使用
adapter = manager.get_adapter("qq")
await adapter.send_message("123456", "Hello")
```

### 方法 2: 保留 AstrBot Platform

```python
from core.platform_astrbot.manager import PlatformManager
```

---

## 支持的平台

### MIYA Platform (`platform_miya.py`)

| 平台 | 类名 | 协议 |
|------|------|------|
| QQ | `QQAdapter` | OneBot v11 |
| Telegram | `TelegramAdapter` | Bot API |
| Discord | `DiscordAdapter` | Gateway |
| 飞书 | `FeishuAdapter` | Webhook |
| 钉钉 | `DingTalkAdapter` | Webhook |

### AstrBot Platform (`platform_astrbot/`)

支持 18+ 平台，包括：
- QQ (OneBot v11/v12)
- Telegram
- Discord
- 飞书
- 钉钉
- 企业微信
- KOOK
- Slack
- Line
- Satori
- 等

---

## 适配器结构

```python
class PlatformAdapter(ABC):
    """平台适配器基类"""
    
    name: str = ""
    platform_type: PlatformType = PlatformType.QQ
    enabled: bool = True
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        pass
    
    @abstractmethod
    async def disconnect(self):
        pass
    
    @abstractmethod
    async def send_message(self, target: str, message: str) -> bool:
        pass
    
    @abstractmethod
    async def send_image(self, target: str, image_url: str) -> bool:
        pass
```

---

## 配置示例

### QQ 配置 `config/qq_config.yaml`

```yaml
platform:
  type: qq
  onebot_url: "http://127.0.0.1:3000"
  enable_group_response: true
  enable_private_response: true
  
response:
  strategy: "smart"  # smart, all, mention
```

### Telegram 配置

```json
{
  "platform": "telegram",
  "token": "YOUR_BOT_TOKEN",
  "proxy": ""
}
```

---

## 启动时自动加载

系统启动时自动检测并加载配置的适配器：

```python
# core/miya_lifecycle.py 中的逻辑
try:
    from core.platform.manager import PlatformManager as AstrPlatformMgr
    self.platform_manager = AstrPlatformMgr
    logger.info("  ✅ 平台管理器 (18 平台)")
except Exception:
    from core.miya.adapters import get_adapter_manager
    self.platform_manager = get_adapter_manager
    logger.info("  ⚠ 平台 (使用 Miya 适配器)")
```

---

## 消息处理

### 接收消息

```python
# 设置消息处理器
adapter.set_message_handler(my_handler)

async def my_handler(message: Message):
    print(f"收到消息: {message.content}")
    print(f"来自: {message.user_name}")
    print(f"平台: {message.platform}")
```

### 发送消息

```python
# 发送文本
await adapter.send_message("123456", "Hello World")

# 发送图片
await adapter.send_image("123456", "https://example.com/image.jpg")

# 发送语音
await adapter.send_voice("123456", "https://example.com/voice.mp3")
```

---

## 平台类型枚举

```python
class PlatformType(str, Enum):
    QQ = "qq"
    TELEGRAM = "telegram"
    FEISHU = "feishu"
    DINGDING = "dingding"
    DISCORD = "discord"
    SLACK = "slack"
    LINE = "line"
    WECHAT_WORK = "wechat_work"
    WECHAT = "wechat"
    SATORI = "satori"
```

---

*最后更新：2026-04-29*