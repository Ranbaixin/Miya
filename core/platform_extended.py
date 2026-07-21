"""
MIYA Platform 扩展

支持更多平台: 飞书, 钉钉, Discord, Slack, LINE, 企业微信等
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


from core.unified_platform.platform_type import MiyaPlatform as PlatformType


@dataclass
class Message:
    """消息"""

    message_id: str
    platform: PlatformType
    message_type: str
    user_id: str
    user_name: str
    group_id: Optional[str] = None
    content: str = ""
    raw: Any = None


@dataclass
class User:
    """用户"""

    user_id: str
    user_name: str
    platform: PlatformType
    avatar: Optional[str] = None


@dataclass
class Group:
    """群组"""

    group_id: str
    group_name: str
    platform: PlatformType
    members: List[str] = None


# ==================== 飞书平台 ====================


class FeishuAdapter:
    """飞书平台适配器"""

    platform_type = PlatformType.FEISHU
    name = "feishu"

    def __init__(self, config: Dict[str, Any]):
        self.app_id = config.get("app_id", "")
        self.app_secret = config.get("app_secret", "")
        self.verification_token = config.get("verification_token", "")
        self.base_url = "https://open.feishu.cn"
        self._client = None

    async def initialize(self, config: Dict) -> bool:
        self.app_id = config.get("app_id", "")
        self.app_secret = config.get("app_secret", "")
        logger.info("[FeishuAdapter] 初始化完成")
        return True

    async def connect(self) -> bool:
        import httpx

        self._client = httpx.AsyncClient()
        logger.info("[FeishuAdapter] 已连接")
        return True

    async def disconnect(self):
        if self._client:
            await self._client.aclose()

    async def send_message(self, target: str, message: str) -> bool:
        """发送消息"""

        # 获取 tenant_access_token
        token_resp = await self._client.post(
            f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal",
            json={
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            },
        )
        token_data = token_resp.json()
        tenant_access_token = token_data.get("tenant_access_token")

        # 发送消息
        chat_id = target
        await self._client.post(
            f"{self.base_url}/open-apis/chat/v4/messages",
            headers={"Authorization": f"Bearer {tenant_access_token}"},
            json={
                "receive_id": chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": message}),
            },
        )
        return True

    async def send_image(self, target: str, image_path: str) -> bool:
        """发送图片（简化版）"""
        return await self.send_message(target, f"[图片: {image_path}]")

    async def send_voice(self, target: str, voice_path: str) -> bool:
        """发送语音"""
        return await self.send_message(target, f"[语音: {voice_path}]")

    async def get_user_info(self, user_id: str) -> Optional[User]:
        """获取用户信息"""
        return User(user_id=user_id, platform=self.platform_type)


# ==================== 钉钉平台 ====================


class DingTalkAdapter:
    """钉钉平台适配器"""

    platform_type = PlatformType.DINGDING
    name = "dingding"

    def __init__(self, config: Dict[str, Any]):
        self.app_key = config.get("app_key", "")
        self.app_secret = config.get("app_secret", "")
        self.base_url = "https://api.dingtalk.com"
        self._access_token = None

    async def initialize(self, config: Dict) -> bool:
        self.app_key = config.get("app_key", "")
        self.app_secret = config.get("app_secret", "")
        logger.info("[DingTalkAdapter] 初始化完成")
        return True

    async def connect(self) -> bool:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/oauth2/access_token",
                json={
                    "appkey": self.app_key,
                    "appsecret": self.app_secret,
                },
            )
            data = resp.json()
            if data.get("errcode") == 0:
                self._access_token = data.get("access_token")
                logger.info("[DingTalkAdapter] 已连接")
                return True
        return False

    async def disconnect(self):
        self._access_token = None

    async def send_message(self, target: str, message: str) -> bool:
        """发送工作通知消息"""
        import httpx

        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.base_url}/topapi/message/robot/send",
                params={"access_token": self._access_token},
                json={
                    "agent_id": self.app_key,
                    "userid_list": target,
                    "msg": json.dumps(
                        {"msgtype": "text", "text": {"content": message}}
                    ),
                },
            )
        return True

    async def send_image(self, target: str, image_path: str) -> bool:
        return await self.send_message(target, "[图片]")

    async def send_voice(self, target: str, voice_path: str) -> bool:
        return await self.send_message(target, "[语音]")

    async def get_user_info(self, user_id: str) -> Optional[User]:
        return User(user_id=user_id, platform=self.platform_type)


# ==================== Discord平台 ====================


class DiscordAdapter:
    """Discord平台适配器"""

    platform_type = PlatformType.DISCORD
    name = "discord"

    def __init__(self, config: Dict[str, Any]):
        self.bot_token = config.get("bot_token", "")
        self.base_url = "https://discord.com/api/v10"

    async def initialize(self, config: Dict) -> bool:
        self.bot_token = config.get("bot_token", "")
        logger.info("[DiscordAdapter] 初始化完成")
        return bool(self.bot_token)

    async def connect(self) -> bool:
        import httpx

        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bot {self.bot_token}"}
        )
        # 测试连接
        resp = await self._client.get(f"{self.base_url}/users/@me")
        if resp.status_code == 200:
            logger.info("[DiscordAdapter] 已连接")
            return True
        return False

    async def disconnect(self):
        if self._client:
            await self._client.aclose()

    async def send_message(self, target: str, message: str) -> bool:
        """发送消息到频道或用户"""

        # target 可以是 channel_id 或 user_id
        await self._client.post(
            f"{self.base_url}/channels/{target}/messages", json={"content": message}
        )
        return True

    async def send_image(self, target: str, image_url: str) -> bool:

        await self._client.post(
            f"{self.base_url}/channels/{target}/messages",
            json={"embeds": [{"image": {"url": image_url}}]},
        )
        return True

    async def send_voice(self, target: str, voice_path: str) -> bool:
        return True  # Discord 需要语音频道

    async def get_user_info(self, user_id: str) -> Optional[User]:
        return User(user_id=user_id, platform=self.platform_type)


# ==================== Slack平台 ====================


class SlackAdapter:
    """Slack平台适配器"""

    platform_type = PlatformType.SLACK
    name = "slack"

    def __init__(self, config: Dict[str, Any]):
        self.bot_token = config.get("bot_token", "")
        self.signing_secret = config.get("signing_secret", "")

    async def initialize(self, config: Dict) -> bool:
        self.bot_token = config.get("bot_token", "")
        self.signing_secret = config.get("signing_secret", "")
        logger.info("[SlackAdapter] 初始化完成")
        return bool(self.bot_token)

    async def connect(self) -> bool:
        import httpx

        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.bot_token}"}
        )
        logger.info("[SlackAdapter] 已连接")
        return True

    async def disconnect(self):
        if self._client:
            await self._client.aclose()

    async def send_message(self, target: str, message: str) -> bool:
        """发送消息到 channel 或 user"""

        await self._client.post(
            "https://slack.com/api/chat.postMessage",
            json={"channel": target, "text": message},
        )
        return True

    async def send_image(self, target: str, image_url: str) -> bool:
        return await self.send_message(target, f"[图片: {image_url}]")

    async def send_voice(self, target: str, voice_path: str) -> bool:
        return await self.send_message(target, "[语音]")

    async def get_user_info(self, user_id: str) -> Optional[User]:
        return User(user_id=user_id, platform=self.platform_type)


# ==================== LINE平台 ====================


class LINEAdapter:
    """LINE平台适配器"""

    platform_type = PlatformType.LINE
    name = "line"

    def __init__(self, config: Dict[str, Any]):
        self.channel_access_token = config.get("channel_access_token", "")
        self.channel_secret = config.get("channel_secret", "")

    async def initialize(self, config: Dict) -> bool:
        self.channel_access_token = config.get("channel_access_token", "")
        self.channel_secret = config.get("channel_secret", "")
        logger.info("[LINEAdapter] 初始化完成")
        return bool(self.channel_access_token)

    async def connect(self) -> bool:
        import httpx

        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.channel_access_token}"}
        )
        logger.info("[LINEAdapter] 已连接")
        return True

    async def disconnect(self):
        if self._client:
            await self._client.aclose()

    async def send_message(self, target: str, message: str) -> bool:
        """发送消息"""

        await self._client.post(
            "https://api.line.me/v2/bot/message/push",
            json={"to": target, "messages": [{"type": "text", "text": message}]},
        )
        return True

    async def send_image(self, target: str, image_url: str) -> bool:

        await self._client.post(
            "https://api.line.me/v2/bot/message/push",
            json={
                "to": target,
                "messages": [
                    {
                        "type": "image",
                        "originalContentUrl": image_url,
                        "previewImageUrl": image_url,
                    }
                ],
            },
        )
        return True

    async def send_voice(self, target: str, voice_path: str) -> bool:
        return await self.send_message(target, "[语音]")

    async def get_user_info(self, user_id: str) -> Optional[User]:
        return User(user_id=user_id, platform=self.platform_type)


# ==================== 企业微信 ====================


class WeChatWorkAdapter:
    """企业微信适配器"""

    platform_type = PlatformType.WECHAT_WORK
    name = "wechat_work"

    def __init__(self, config: Dict[str, Any]):
        self.corp_id = config.get("corp_id", "")
        self.corp_secret = config.get("corp_secret", "")
        self.agent_id = config.get("agent_id", "")

    async def initialize(self, config: Dict) -> bool:
        self.corp_id = config.get("corp_id", "")
        self.corp_secret = config.get("corp_secret", "")
        self.agent_id = config.get("agent_id", "")
        logger.info("[WeChatWorkAdapter] 初始化完成")
        return bool(self.corp_id and self.corp_secret)

    async def connect(self) -> bool:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                params={
                    "corpid": self.corp_id,
                    "corpsecret": self.corp_secret,
                },
            )
            data = resp.json()
            if data.get("errcode") == 0:
                self._access_token = data.get("access_token")
                logger.info("[WeChatWorkAdapter] 已连接")
                return True
        return False

    async def send_message(self, target: str, message: str) -> bool:
        """发送应用消息"""

        await self._client.post(
            "https://qyapi.weixin.qq.com/cgi-bin/message/send",
            params={"access_token": self._access_token},
            json={
                "touser": target,
                "msgtype": "text",
                "agentid": self.agent_id,
                "text": {"content": message},
            },
        )
        return True

    async def send_image(self, target: str, image_path: str) -> bool:
        return await self.send_message(target, "[图���]")

    async def send_voice(self, target: str, voice_path: str) -> bool:
        return await self.send_message(target, "[语音]")

    async def get_user_info(self, user_id: str) -> Optional[User]:
        return User(user_id=user_id, platform=self.platform_type)


# ==================== Platform 注册表 ====================


class PlatformRegistry:
    """平台注册表"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._adapters: Dict[PlatformType, Any] = {}
        self._register_default_adapters()
        self._initialized = True

    def _register_default_adapters(self):
        """注册默认平台"""
        from core.platform_miya import QQAdapter, TelegramAdapter

        self._adapters = {
            PlatformType.QQ: QQAdapter,
            PlatformType.TELEGRAM: TelegramAdapter,
            PlatformType.FEISHU: FeishuAdapter,
            PlatformType.DINGDING: DingTalkAdapter,
            PlatformType.DISCORD: DiscordAdapter,
            PlatformType.SLACK: SlackAdapter,
            PlatformType.LINE: LINEAdapter,
            PlatformType.WECHAT_WORK: WeChatWorkAdapter,
        }

        logger.info(f"[PlatformRegistry] 已注册 {len(self._adapters)} 个平台")

    def get(self, platform: PlatformType) -> Optional[Any]:
        return self._adapters.get(platform)

    def list_platforms(self) -> List[Dict]:
        return [{"type": p.value, "name": p.value} for p in self._adapters]

    def register(self, platform: PlatformType, adapter_cls: Any):
        self._adapters[platform] = adapter_cls
        logger.info(f"[PlatformRegistry] 注册 {platform.value}")


def get_platform_registry() -> PlatformRegistry:
    return PlatformRegistry()


# ==================== MIYA Platform 管理器 ====================


class PlatformInstance:
    """平台实例包装"""

    def __init__(self, platform_type: PlatformType, adapter: Any, config: Dict):
        self.platform_type = platform_type
        self.adapter = adapter
        self.config = config
        self.enabled = config.get("enabled", True)
        self.client_self_id = config.get("client_self_id", "")

    async def run(self):
        """运行平台适配器"""
        if hasattr(self.adapter, "run"):
            await self.adapter.run()

    async def connect(self) -> bool:
        """连接平台"""
        if hasattr(self.adapter, "connect"):
            return await self.adapter.connect()
        return True

    async def disconnect(self):
        """断开连接"""
        if hasattr(self.adapter, "disconnect"):
            await self.adapter.disconnect()

    async def send_message(self, user_id: str, content: str):
        """发送消息"""
        if hasattr(self.adapter, "send_message"):
            await self.adapter.send_message(user_id, content)


class PlatformManager:
    """
    MIYA Platform 管理器

    功能:
    - 平台适配器生命周期管理
    - 消息事件队列
    - 平台配置管理
    - Webhook 支持
    """

    def __init__(self, event_queue=None):
        self.platform_insts: List[PlatformInstance] = []
        self._platform_map: Dict[str, PlatformInstance] = {}
        self._event_queue = event_queue
        self._running_tasks: Dict[str, Any] = {}
        logger.info("[PlatformManager] 初始化完成")

    async def load_platform(self, platform_type: PlatformType, config: Dict) -> bool:
        """加载平台适配器"""
        try:
            if not config.get("enabled", True):
                logger.info(f"[PlatformManager] {platform_type.value} 已禁用")
                return False

            platform_id = config.get("id", platform_type.value)
            logger.info(f"[PlatformManager] 加载 {platform_type.value}({platform_id})")

            adapter = self._create_adapter(platform_type, config)
            if not adapter:
                logger.error(f"[PlatformManager] 无法创建 {platform_type.value} 适配器")
                return False

            inst = PlatformInstance(platform_type, adapter, config)
            inst.client_self_id = config.get("client_self_id", platform_id)

            await adapter.initialize(config)
            await adapter.connect()

            self.platform_insts.append(inst)
            self._platform_map[platform_id] = inst

            logger.info(f"[PlatformManager] {platform_type.value} 加载成功")
            return True

        except Exception as e:
            logger.error(f"[PlatformManager] 加载 {platform_type.value} 失败: {e}")
            return False

    def _create_adapter(
        self, platform_type: PlatformType, config: Dict
    ) -> Optional[Any]:
        """创建平台适配器"""
        adapter_map = {
            PlatformType.FEISHU: FeishuAdapter,
            PlatformType.DINGDING: DingTalkAdapter,
            PlatformType.DISCORD: DiscordAdapter,
            PlatformType.SLACK: SlackAdapter,
            PlatformType.LINE: LINEAdapter,
            PlatformType.WECHAT_WORK: WeChatWorkAdapter,
        }
        adapter_cls = adapter_map.get(platform_type)
        if adapter_cls:
            return adapter_cls(config)
        return None

    async def start_platform(self, platform_id: str):
        """启动平台任务"""
        inst = self._platform_map.get(platform_id)
        if not inst:
            return

        task = asyncio.create_task(inst.run(), name=f"platform_{platform_id}")
        self._running_tasks[platform_id] = task
        logger.info(f"[PlatformManager] 启动平台: {platform_id}")

    async def stop_platform(self, platform_id: str):
        """停止平台任务"""
        task = self._running_tasks.pop(platform_id, None)
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        logger.info(f"[PlatformManager] 停止平台: {platform_id}")

    async def stop_all(self):
        """停止所有平台"""
        for platform_id in list(self._running_tasks.keys()):
            await self.stop_platform(platform_id)
        for inst in self.platform_insts:
            await inst.disconnect()
        logger.info("[PlatformManager] 已停止所有平台")

    def get_platform(self, platform_id: str) -> Optional[PlatformInstance]:
        """获取平台实例"""
        return self._platform_map.get(platform_id)

    def list_platforms(self) -> List[Dict]:
        """列出所有平台"""
        result = []
        for inst in self.platform_insts:
            result.append(
                {
                    "id": inst.client_self_id,
                    "type": inst.platform_type.value,
                    "enabled": inst.enabled,
                }
            )
        return result

    async def send_message_to_user(self, platform_id: str, user_id: str, content: str):
        """发送消息给用户"""
        inst = self._platform_map.get(platform_id)
        if inst:
            await inst.send_message(user_id, content)


_platform_manager = None


def get_platform_manager(event_queue=None) -> PlatformManager:
    """获取平台管理器"""
    global _platform_manager
    if _platform_manager is None:
        _platform_manager = PlatformManager(event_queue)
    return _platform_manager


__all__ = [
    "PlatformType",
    "Message",
    "User",
    "Group",
    "FeishuAdapter",
    "DingTalkAdapter",
    "DiscordAdapter",
    "SlackAdapter",
    "LINEAdapter",
    "WeChatWorkAdapter",
    "PlatformRegistry",
    "get_platform_registry",
    "PlatformInstance",
    "PlatformManager",
    "get_platform_manager",
]
