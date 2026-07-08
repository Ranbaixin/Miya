"""
QQ交互子网 - 核心子网逻辑
从原 qq.py 中拆分出来的核心网络逻辑
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Set

from .client import QQOneBotClient
from .message_handler import QQMessageHandler
from .tts_handler import QQTTsHandler

# 注意：IntelligentActiveChatManager 已废弃，使用 core.proactive_chat.ProactiveChatSystem
from .unified_config import get_connection_config, get_multimedia_config, get_qq_config

logger = logging.getLogger(__name__)

from .image_handler import QQImageHandler


class QQNet:
    """
    QQ交互子网
    完全吸收Undefined的QQ机器人能力，作为弥娅的一个子网运行
    """

    def __init__(self, miya_core, mlink=None, memory_net=None, tts_net=None):
        """
        初始化QQ子网

        Args:
            miya_core: 弥娅核心实例
            mlink: M-Link 核心实例（用于全局记忆系统）
            memory_net: MemoryNet 全局记忆子网实例
            tts_net: TTSNet TTS子网实例
        """
        self.miya_core = miya_core
        self.mlink = mlink
        self.memory_net = memory_net
        self.tts_net = tts_net
        self.net_id = "qq_net"
        self.capabilities = [
            "qq_group_chat",
            "qq_private_chat",
            "qq_command",
            "qq_message_history",
            "qq_poke",
            "qq_multimedia",
            "qq_tts",
        ]

        # 配置
        self.onebot_ws_url = None
        self.onebot_token = None
        self.bot_qq = None
        self.superadmin_qq = None

        # 客户端
        self.onebot_client: Optional[QQOneBotClient] = None

        # 缓存管理器（新增）
        from .cache_manager import get_qq_cache_manager

        self.cache_manager = get_qq_cache_manager()
        logger.info("[QQNet] 缓存管理器已集成")

        # 处理模块
        self.message_handler = QQMessageHandler(self)
        self.tts_handler = QQTTsHandler(self)
        # 传递personality给图片处理器
        personality = (
            miya_core.personality
            if miya_core and hasattr(miya_core, "personality")
            else None
        )
        self.image_handler = QQImageHandler(self, personality)
        # 主动聊天功能现在使用 core.proactive_chat.ProactiveChatSystem
        # 旧系统已废弃，不再初始化
        self.active_chat_manager = None
        logger.info("[QQNet] 主动聊天系统使用 v2.1 (core.proactive_chat)")

        # 访问控制
        self.group_whitelist: Set[int] = set()
        self.group_blacklist: Set[int] = set()
        self.user_whitelist: Set[int] = set()
        self.user_blacklist: Set[int] = set()

        # 配置加载
        self._load_default_config()

        # 消息处理回调
        self.on_message_callback: Optional[Callable] = None

    def _load_default_config(self):
        """加载默认配置"""
        # 从配置文件加载
        self._load_config_from_file()

    def _load_config_from_file(self):
        """从配置文件加载配置（使用统一配置系统）"""
        try:
            # 使用统一配置系统（新结构：qq.connection.*）
            conn = get_connection_config()
            multi = get_multimedia_config()
            features = get_qq_config("features") or {}
            img_rec = get_qq_config("image_recognition") or {}
            task_sched = get_qq_config("task_scheduler") or {}
            access_ctrl = get_qq_config("access_control") or {}
            commands = get_qq_config("commands") or {}
            perf = get_qq_config("performance") or {}
            logging_cfg = get_qq_config("logging") or {}

            # 基础连接配置
            self.onebot_ws_url = conn.get("ws_url", "ws://localhost:3001")
            self.onebot_token = conn.get("token", "")
            self.bot_qq = conn.get("bot_qq", 0)
            self.superadmin_qq = conn.get("superadmin_qq", 0)
            self.reconnect_interval = conn.get("reconnect_interval", 5.0)
            self.ping_interval = conn.get("ping_interval", 20)
            self.ping_timeout = conn.get("ping_timeout", 30)
            self.max_message_size = conn.get("max_message_size", 104857600)

            # 访问控制
            ac_enabled = access_ctrl.get("enabled", False)
            gw = access_ctrl.get("group_whitelist", [])
            gb = access_ctrl.get("group_blacklist", [])
            uw = access_ctrl.get("user_whitelist", [])
            ub = access_ctrl.get("user_blacklist", [])

            self.group_whitelist = set(gw) if isinstance(gw, list) else set()
            self.group_blacklist = set(gb) if isinstance(gb, list) else set()
            self.user_whitelist = set(uw) if isinstance(uw, list) else set()
            self.user_blacklist = set(ub) if isinstance(ub, list) else set()
            self.access_control_enabled = ac_enabled

            # 多媒体配置
            self.image_config = multi.get("image", {})
            self.file_config = multi.get("file", {})

            # 图片识别配置
            ocr_cfg = img_rec.get("ocr", {})
            self.ocr_config = {
                "enabled": ocr_cfg.get("enabled", False),
                "engine": ocr_cfg.get("engine", "none"),
            }
            self.ai_analysis_config = img_rec.get("ai_analysis", {})
            self.image_cache_config = img_rec.get("cache", {})

            # 功能开关
            self.active_chat_enabled = features.get("active_chat", True)
            self.passive_chat_enabled = features.get("passive_chat", True)
            self.poke_reply_enabled = features.get("poke_reply", True)
            self.emoji_request_enabled = features.get("emoji_request", True)
            self.scheduled_tasks_enabled = features.get("scheduled_tasks", True)
            self.welcome_new_member = features.get("welcome_new_member", False)

            self.active_chat_limits = {
                "max_daily_messages": 10,
                "min_interval": 300,
            }

            # 任务调度配置
            self.task_scheduler_enabled = task_sched.get("enabled", True)

            # 命令配置
            self.command_prefix = commands.get("prefix", "/")
            # 命令别名从 text_config.json 读取
            from core.text_loader import get_command_keywords

            self.command_aliases = get_command_keywords()
            # 快速响应从 text_config.json 读取
            from core.text_loader import get_text

            self.quick_responses = get_text("quick_responses", {})
            # 错误消息从 text_config.json 读取
            self.error_messages = get_text("error_messages", {})

            # 消息解析配置
            msg_parse = get_qq_config("message_parsing") or {}
            self.enable_reply_parsing = msg_parse.get("enable_reply_parsing", True)
            self.enable_file_parsing = msg_parse.get("enable_file_parsing", True)
            self.enable_media_detection = msg_parse.get("enable_media_detection", True)

            # 合并转发配置
            forward_cfg = get_qq_config("forward") or {}
            self.enable_forward_parsing = forward_cfg.get("enable_parsing", True)
            self.max_forward_depth = forward_cfg.get("max_expand_depth", 3)

            # 性能配置
            cache_cfg = perf.get("cache", {})
            self.message_history_cache = cache_cfg.get("message_history", 100)
            self.user_info_cache = cache_cfg.get("user_info", 1000)

            # 日志配置
            self.log_message_detail = logging_cfg.get("log_message_detail", False)
            self.debug_mode = logging_cfg.get("debug", False)

            # TTS配置
            self.tts_enabled = True
            self.tts_voice_mode = "text"
            self.smart_tts_enabled = False

            # QQ消息分段配置
            self.qq_message_split = True
            self.qq_max_message_length = 200

            # 本地播放配置
            self.local_playback_enabled = False
            self.local_playback_volume = 1.0
            self.audio_player = None

            logger.info(f"QQNet 统一配置加载成功，WebSocket地址: {self.onebot_ws_url}")
            logger.info(f"Bot QQ: {self.bot_qq}")
            logger.info(f"Super Admin: {self.superadmin_qq}")
            logger.info(f"重连间隔: {self.reconnect_interval}秒")
            logger.info(f"心跳间隔: {self.ping_interval}秒")
            logger.info(
                f"OCR识别: {'启用' if self.ocr_config.get('enabled') else '禁用'}"
            )
            logger.info(f"主动聊天: {'启用' if self.active_chat_enabled else '禁用'}")
            logger.info(
                f"任务调度: {'启用' if self.task_scheduler_enabled else '禁用'}"
            )
            logger.info(
                f"功能开关: poke={self.poke_reply_enabled}, emoji={self.emoji_request_enabled}"
            )

        except Exception as e:
            logger.error(f"[QQNet] 加载配置失败: {e}")
            self.onebot_ws_url = ""
            self.onebot_token = ""
            self.bot_qq = 0
            self.superadmin_qq = 0
            self.reconnect_interval = 5.0
            self.ping_interval = 20
            self.ping_timeout = 30
            self.max_message_size = 104857600

            self.group_whitelist = set()
            self.group_blacklist = set()
            self.user_whitelist = set()
            self.user_blacklist = set()
            self.access_control_enabled = False

            self.image_config = {
                "max_size": 10485760,
                "allowed_formats": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
            }
            self.file_config = {"max_size": 52428800}
            self.ocr_config = {"enabled": False, "engine": "none"}
            self.active_chat_enabled = True
            self.passive_chat_enabled = True
            self.poke_reply_enabled = True
            self.emoji_request_enabled = True
            self.scheduled_tasks_enabled = True
            self.active_chat_limits = {"max_daily_messages": 10, "min_interval": 300}
            self.task_scheduler_enabled = True

            self.command_prefix = "/"
            self.command_aliases = {}
            self.quick_responses = {}
            self.error_messages = {}

            self.enable_reply_parsing = True
            self.enable_file_parsing = True
            self.enable_media_detection = True
            self.enable_forward_parsing = True
            self.max_forward_depth = 3

            self.tts_enabled = True
            self.tts_voice_mode = "text"
            self.smart_tts_enabled = False
            self.qq_message_split = True
            self.qq_max_message_length = 200
            self.local_playback_enabled = False
            self.local_playback_volume = 1.0
            self.audio_player = None

    def configure(
        self,
        onebot_ws_url: str,
        onebot_token: str = "",
        bot_qq: int = 0,
        superadmin_qq: int = 0,
        group_whitelist: List[int] = None,
        group_blacklist: List[int] = None,
        user_whitelist: List[int] = None,
        user_blacklist: List[int] = None,
        tts_enabled: bool = True,
        tts_voice_mode: str = "text",
        smart_tts_enabled: bool = False,
        qq_message_split: bool = True,
        qq_max_message_length: int = 200,
        local_playback_enabled: bool = False,
        local_playback_volume: float = 1.0,
    ) -> None:
        """配置QQ子网"""
        self.onebot_ws_url = onebot_ws_url
        self.onebot_token = onebot_token
        self.bot_qq = bot_qq
        self.superadmin_qq = superadmin_qq

        if group_whitelist:
            self.group_whitelist = set(group_whitelist)
        if group_blacklist:
            self.group_blacklist = set(group_blacklist)
        if user_whitelist:
            self.user_whitelist = set(user_whitelist)
        if user_blacklist:
            self.user_blacklist = set(user_blacklist)

        self.tts_enabled = tts_enabled
        self.tts_voice_mode = tts_voice_mode
        self.smart_tts_enabled = smart_tts_enabled

        # QQ消息分段配置
        self.qq_message_split = qq_message_split
        self.qq_max_message_length = qq_max_message_length

        # 本地播放配置
        self.local_playback_enabled = local_playback_enabled
        self.local_playback_volume = local_playback_volume

        # 初始化音频播放器
        if local_playback_enabled:
            from core.audio_player import get_audio_player

            self.audio_player = get_audio_player()
            self.audio_player.set_volume(local_playback_volume)

        # 更新处理模块配置
        self.message_handler.configure(
            group_whitelist=self.group_whitelist,
            group_blacklist=self.group_blacklist,
            user_whitelist=self.user_whitelist,
            user_blacklist=self.user_blacklist,
            bot_qq=self.bot_qq,
            enable_image_ocr=False,
            enable_ai_image_analysis=True,
            image_handler=self.image_handler,
            onebot_client=self.onebot_client,
        )

        # 配置图片处理器 - 仅使用视觉模型
        self.image_handler.configure()

        self.tts_handler.configure(
            tts_enabled=self.tts_enabled,
            tts_voice_mode=self.tts_voice_mode,
            smart_tts_enabled=self.smart_tts_enabled,
            qq_message_split=self.qq_message_split,
            qq_max_message_length=self.qq_max_message_length,
            local_playback_enabled=self.local_playback_enabled,
            local_playback_volume=self.local_playback_volume,
            audio_player=self.audio_player,
        )

        logger.info(
            f"[QQNet] 配置完成: bot_qq={bot_qq}, "
            f"superadmin={superadmin_qq}, "
            f"groups={len(self.group_whitelist)}/{len(self.group_blacklist)}, "
            f"tts_enabled={tts_enabled}, tts_mode={tts_voice_mode}, "
            f"smart_tts={smart_tts_enabled}, "
            f"message_split={self.qq_message_split}, max_length={self.qq_max_message_length}, "
            f"local_playback={self.local_playback_enabled}, local_volume={self.local_playback_volume}"
        )

    def set_message_callback(self, callback: Callable) -> None:
        """设置消息处理回调"""
        self.on_message_callback = callback
        if self.onebot_client:
            self.onebot_client.set_message_handler(self._handle_qq_message)

    async def connect(self) -> None:
        """连接到QQ"""
        if not self.onebot_ws_url:
            raise RuntimeError("未配置OneBot WebSocket URL")

        self.onebot_client = QQOneBotClient(self.onebot_ws_url, self.onebot_token)
        self.onebot_client.set_message_handler(self._handle_qq_message)

        # 连接后更新消息处理器的 client
        self.message_handler.message_parser.set_client(self.onebot_client)
        logger.info("[QQNet] 已更新消息解析器的 onebot_client")

        await self.onebot_client.connect()
        logger.info("[QQNet] 已连接到QQ")

    async def start(self) -> None:
        """启动QQ子网"""
        if not self.onebot_client:
            await self.connect()

        # 启动消息接收循环
        await self.onebot_client.run_with_reconnect()

    async def stop(self) -> None:
        """停止QQ子网"""
        # 停止QQ客户端
        if self.onebot_client:
            self.onebot_client.stop()
            await self.onebot_client.disconnect()

    async def _handle_qq_message(self, event: Dict) -> None:
        """处理QQ消息事件"""
        # 记录接收到的原始事件
        post_type = event.get("post_type", "unknown")
        logger.debug(f"[QQNet] 收到事件: post_type={post_type}")

        # 委托给消息处理器
        qq_message = await self.message_handler.handle_event(event)

        if qq_message:
            logger.debug(
                f"[QQNet] 消息解析完成: type={qq_message.message_type}, from={qq_message.sender_id}"
            )

            if self.on_message_callback:
                await self.on_message_callback(qq_message)
        else:
            logger.debug("[QQNet] 消息被过滤或解析失败")

    async def send_group_message(
        self, group_id: int, message: str | List[Dict], use_tts: bool = None
    ) -> bool:
        """发送群消息"""
        return await self.tts_handler.send_group_message(
            group_id=group_id, message=message, use_tts=use_tts
        )

    async def send_private_message(
        self, user_id: int, message: str | List[Dict], use_tts: bool = None
    ) -> bool:
        """发送私聊消息"""
        return await self.tts_handler.send_private_message(
            user_id=user_id, message=message, use_tts=use_tts
        )

    def get_history(self, chat_id: int, limit: int = 20) -> List[Dict]:
        """获取历史消息"""
        return self.message_handler.get_history(chat_id, limit)

    def set_tts_mode(self, mode: str):
        """设置TTS模式 (text 或 voice)"""
        self.tts_handler.set_tts_mode(mode)

    def toggle_tts(self, enabled: bool = None):
        """切换TTS开关"""
        return self.tts_handler.toggle_tts(enabled)

    def toggle_local_playback(self, enabled: bool = None):
        """切换本地播放开关"""
        return self.tts_handler.toggle_local_playback(enabled)

    def set_local_playback_volume(self, volume: float):
        """设置本地播放音量"""
        self.tts_handler.set_local_playback_volume(volume)

    def toggle_smart_tts(self, enabled: bool = None):
        """切换智能TTS判断开关"""
        return self.tts_handler.toggle_smart_tts(enabled)

    async def process_request(self, request: Dict) -> Dict:
        """处理QQ子网请求"""
        req_type = request.get("type")

        if req_type == "send_group":
            success = await self.send_group_message(
                request.get("group_id"), request.get("message")
            )
            return {"success": success}

        elif req_type == "send_private":
            success = await self.send_private_message(
                request.get("user_id"), request.get("message")
            )
            return {"success": success}

        elif req_type == "get_history":
            history = self.get_history(request.get("chat_id"), request.get("limit", 20))
            return {"history": history}

        elif req_type == "get_connection_status":
            if self.onebot_client:
                return {"status": self.onebot_client.connection_status()}
            return {"status": {"connected": False}}

        elif req_type == "toggle_smart_tts":
            enabled = request.get("enabled")
            result = self.toggle_smart_tts(enabled)
            return {"success": True, "enabled": result}

        elif req_type == "get_tts_status":
            return {
                "tts_enabled": self.tts_enabled,
                "tts_voice_mode": self.tts_voice_mode,
                "smart_tts_enabled": self.smart_tts_enabled,
                "local_playback_enabled": self.local_playback_enabled,
                "local_playback_volume": self.local_playback_volume,
            }

        else:
            return {"error": "Unknown request type"}

    # ========== 主动聊天方法 ==========

    async def schedule_active_message(
        self,
        target_type: str,
        target_id: int,
        content: str,
        trigger_type: str = "time",
        trigger_config: Dict = None,
        priority: str = "normal",
        metadata: Dict = None,
    ) -> str:
        """
        安排主动消息（已废弃，使用 core.proactive_chat）
        """
        logger.warning(
            "[QQNet] schedule_active_message 已废弃，请使用 core.proactive_chat"
        )
        return ""

    def set_user_preference(self, user_id: int, preferences: Dict[str, Any]):
        """
        设置用户偏好（已废弃）
        """
        logger.warning("[QQNet] set_user_preference 已废弃")

    def get_user_preference(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户偏好（已废弃）
        """
        return {}

    def get_active_chat_stats(self) -> Dict[str, Any]:
        """
        获取主动聊天统计（已废弃）
        """
        return {"status": "deprecated", "message": "使用 core.proactive_chat"}

    def get_pending_messages(self) -> List[Dict[str, Any]]:
        """
        获取待发消息列表（已废弃）
        """
        return []

    def get_sent_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取已发消息列表（已废弃）
        """
        return []

    def cancel_active_message(self, message_id: str) -> bool:
        """
        取消主动消息（已废弃）
        """
        return False

    def cleanup_expired_messages(self):
        """清理过期消息（已废弃）"""
        pass
