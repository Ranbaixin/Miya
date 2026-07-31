# 平台接入清单

> v8.0 当前支持的平台: QQ/OneBot, Telegram, Discord, QQ Official, Lark, WebChat

## 接入新平台必做 5 步

### 1. 实现平台类

在 `core/unified_platform_impl/` 下新建或扩展现有文件，继承 `WebhookPlatform` 或 `BasePlatform` + `MessageMixin`。

**Webhook 型（接收 HTTP POST）**：

```python
from fastapi import Request
from fastapi.responses import PlainTextResponse, Response
from .webhook_base import WebhookPlatform

class ExamplePlatform(WebhookPlatform):
    platform_id = "example"
    platform_name = "Example"

    def __init__(self, config=None):
        super().__init__(config)
        self._token = config.get("token", "")  # 从配置读凭据

    def get_webhook_routes(self) -> dict:
        async def webhook_handler(request: Request):  # 必须注解 Request!
            body = await request.json()
            text = body.get("content", "")
            user_id = body.get("user", "")
            if text.strip():
                # 拿到 AI 回复后必须自己发送
                response = await self.route_to_decision_hub(
                    content=text, user_id=user_id, message_type="private",
                )
                if response:
                    await self._send_to_platform(user_id, response)
            return {"code": 0}

        return {"prefix": "/webhook/example", "routes": [("POST", "", webhook_handler)]}

    async def send_message(self, target: str, content: str, **kwargs) -> bool:
        # 实现发送逻辑: HTTP POST / SDK / WS
        ...
```

### 2. 注册到平台映射

`core/unified_platform_impl/__init__.py`：
```python
from .example_platform import ExamplePlatform
```

`core/miya_daemon.py` 的 `platform_map`：
```python
"example": ExamplePlatform,
```

### 3. 配置凭据

`config/platforms_config.py`：用 `_env(...)` 从环境变量读取凭据。

`config/.env.example`：补充对应的环境变量占位符。

### 4. 查看遗留参考实现

正确实现（含微信/企微被动回复 XML 逻辑）存档在：
```bash
git show legacy/pre-cleanup-snapshot:core/unified_platform_impl/wechat_platforms.py
```

### 5. 验证

```bash
python scripts/check_platform_config.py --all  # 凭据链路无断裂
python scripts/smoke_test.py --fast             # 平台注册正常
```

---

## 常见坑

| 坑 | 说明 |
|---|---|
| **handler 无类型注解** | `async def handler(request)` → FastAPI 不会注入 Request，消息收不到 |
| **丢弃 route_to_decision_hub 返回值** | 基类不会替你发，必须 `response = await self.route_to_decision_hub(...)` 拿到后再调发送 API |
| **微信/企微的 GET 验证** | 必须 `PlainTextResponse(echostr)`，否则验证失败 |
| **XML 被动回复被 JSON 转义** | 必须 `Response(content=xml, media_type="application/xml")` |
| **凭据硬编码空串** | `config/platforms_config.py` 必须用 `_env("KEY")` |
| **未在 platform_map 注册** | 会静默退化成什么也不做的 `GenericPlatform` |
