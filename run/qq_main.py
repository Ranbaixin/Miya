# -*- coding: utf-8 -*-
"""
弥娅 QQ 模式主入口 - 使用新版 ToolNet 架构

启动弥娅 QQ 机器人
"""

import sys
import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Any, List, Optional

# 设置标准输出编码为UTF-8以正确显示中文
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入配置
from config import Settings
from run.main import Miya
from dotenv import load_dotenv

# 导入QQ相关
from webnet import QQNet

# 导入消息队列
from core.message_queue import (
    get_message_queue,
    MessageQueueManager,
    QUEUE_LANE_SUPERADMIN,
    QUEUE_LANE_GROUP_SUPERADMIN,
    QUEUE_LANE_PRIVATE,
    QUEUE_LANE_GROUP_MENTION,
    QUEUE_LANE_GROUP_NORMAL,
    QUEUE_LANE_BACKGROUND,
)


class MiyaQQ:
    """弥娅 QQ 模式主类 - 使用新版 ToolNet 架构"""

    def __init__(self):
        import sys

        sys.setrecursionlimit(max(sys.getrecursionlimit(), 2000))
        self.logger: logging.Logger = self._setup_logger()
        self.settings: Any = Settings()

        # 初始化核心系统
        self.miya: Any = None
        self.qq_net: Any = None
        self.tts_net: Any = None

        # 初始化消息队列
        self.message_queue = get_message_queue()
        self._queue_initialized = False
        self._superadmin_qq = 0

    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger("MiyaQQ")
        logger.setLevel(logging.DEBUG)

        # 控制台处理器 - 使用更详细的格式
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 文件处理器
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)

        file_handler = logging.FileHandler(log_dir / "miya_qq.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # 控制台格式化 - 简洁风格
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # 文件格式化 - 完整格式
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def _log_system_info(self):
        """记录系统信息"""
        import platform
        import sys
        from datetime import datetime

        self.logger.info(f"系统信息:")
        self.logger.info(f"  操作系统: {platform.system()} {platform.version()}")
        self.logger.info(f"  Python: {sys.version.split()[0]}")
        self.logger.info(f"  工作目录: {Path(__file__).parent.parent}")
        self.logger.info(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    async def initialize(self):
        """初始化系统"""
        self.logger.info("弥娅 QQ 机器人初始化中...")
        self._log_system_info()

        # 加载环境变量
        env_path = Path(__file__).parent.parent / "config" / ".env"
        load_dotenv(env_path)

        # 读取 QQ 配置
        onebot_ws_url = os.getenv("QQ_ONEBOT_WS_URL", "")
        onebot_token = os.getenv("QQ_ONEBOT_TOKEN", "")
        bot_qq = int(os.getenv("QQ_BOT_QQ", "0"))
        superadmin_qq = int(os.getenv("QQ_SUPERADMIN_QQ", "0"))

        if not onebot_ws_url:
            raise RuntimeError("未配置 QQ_ONEBOT_WS_URL，请在 config/.env 中设置")
        if bot_qq == 0:
            raise RuntimeError("未配置 QQ_BOT_QQ，请在 config/.env 中设置")

        self.logger.info(f"QQ 配置加载完成:")
        self.logger.info(f"  OneBot URL: {onebot_ws_url}")
        self.logger.info(f"  Bot QQ: {bot_qq}")
        self.logger.info(f"  Super Admin: {superadmin_qq}")

        # 保存 superadmin QQ 用于队列判断
        self._superadmin_qq = superadmin_qq

        # 创建弥娅核心实例（使用新版架构）
        self.miya = Miya()

        # 异步初始化 MemoryNet
        if self.miya.memory_net:
            await self.miya._initialize_memory_net_async()

        # 让 core.ai_client 的工具调用日志也输出到终端
        self._setup_ai_client_logger()

        self.logger.info("弥娅核心系统初始化完成（新版 ToolNet 架构）")

        # 初始化 TTS 系统
        self._init_tts_system()

        # 初始化 QQNet
        if not self.miya.net_manager:
            raise RuntimeError("NetManager 未初始化")

        # QQNet 的构造函数签名不同，需要调整参数
        self.qq_net = QQNet(
            miya_core=self.miya,
            mlink=self.miya.mlink,
            memory_net=self.miya.memory_net,
            tts_net=self.tts_net,
        )

        # 设置消息处理回调
        self.qq_net.set_message_callback(self._handle_qq_callback)

        # 注册 M-Link 节点
        self._register_mlink_nodes()

        # 注册跨端终端
        self._register_cross_terminal()

        # 配置 QQNet
        self.qq_net.configure(
            onebot_ws_url=onebot_ws_url,
            onebot_token=onebot_token,
            bot_qq=bot_qq,
            superadmin_qq=superadmin_qq,
        )

        # 初始化消息队列
        self._init_message_queue()

        # 初始化消息汇总窗口期管理器
        self._init_message_batcher()

        self.logger.info("QQNet 配置完成")

    def _setup_ai_client_logger(self):
        """让 core.ai_client 的工具调用日志也输出到终端"""
        import logging

        ai_logger = logging.getLogger("core.ai_client")
        ai_logger.setLevel(logging.INFO)

        # 添加一个控制台处理器，复用 MiyaQQ 的格式
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)

        # 避免重复添加（如果已经添加过）
        if not any(isinstance(h, logging.StreamHandler) for h in ai_logger.handlers):
            ai_logger.addHandler(console_handler)
        ai_logger.propagate = True  # 允许传播到根日志

    def _init_tts_system(self):
        """初始化 TTS 系统"""
        try:
            from core.tts import TTSNet
            import json
            from core.constants import Encoding

            # 初始化 TTSNet
            self.tts_net = TTSNet(self.miya.mlink)

            # 加载TTS配置
            tts_config_path = (
                Path(__file__).parent.parent / "config" / "tts_config.json"
            )
            if tts_config_path.exists():
                with open(tts_config_path, "r", encoding=Encoding.UTF8) as f:
                    tts_config = json.load(f)
                self.tts_net.initialize(tts_config)
                self.logger.info("TTS系统初始化成功")
            else:
                self.logger.warning("TTS配置文件不存在,使用默认配置")
                self.tts_net = None

        except Exception as e:
            self.logger.warning(f"TTS系统初始化失败: {e}")
            self.tts_net = None

    def _init_message_queue(self):
        """初始化消息队列"""
        try:
            import json
            from pathlib import Path

            config_path = Path(__file__).parent.parent / "config" / "qq_config.yaml"
            queue_config = {}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    import yaml

                    full_config = yaml.safe_load(f)
                    queue_config = full_config.get("qq", {}).get("message_queue", {})

            enabled = queue_config.get("enabled", True)
            if not enabled:
                self.logger.info("[消息队列] 消息队列已禁用")
                return

            default_interval = queue_config.get("default_interval", 1.0)
            model_intervals = queue_config.get("model_intervals", {})

            self.message_queue = MessageQueueManager.get_instance(default_interval)
            if model_intervals:
                self.message_queue.update_model_intervals(model_intervals)

            async def handle_request(request: dict):
                await self._queue_process_message(request)

            self.message_queue.start(handle_request)
            self._queue_initialized = True

            self.logger.info(
                f"[消息队列] 队列管理器已启动: interval={default_interval}s, models={list(model_intervals.keys()) or ['default']}"
            )
        except Exception as e:
            self.logger.warning(f"[消息队列] 初始化失败: {e}")

    async def _queue_process_message(self, request: dict):
        """队列处理消息"""
        qq_message = request.get("qq_message")
        perception = request.get("perception")

        if qq_message and perception:
            await self._process_message_with_perception(
                qq_message, qq_message.message, perception
            )

    def _get_queue_lane(self, qq_message: Any, is_superadmin: bool = False) -> str:
        """判断消息应该进入哪个队列"""
        msg_type = (
            qq_message.message_type
            if hasattr(qq_message, "message_type")
            else "private"
        )

        if msg_type == "private":
            if is_superadmin:
                return QUEUE_LANE_SUPERADMIN
            return QUEUE_LANE_PRIVATE

        if msg_type == "group":
            group_id = getattr(qq_message, "group_id", 0)
            if is_superadmin and group_id:
                return QUEUE_LANE_GROUP_SUPERADMIN

            is_at_bot = getattr(qq_message, "is_at_bot", False)
            if is_at_bot:
                return QUEUE_LANE_GROUP_MENTION
            return QUEUE_LANE_GROUP_NORMAL

        return QUEUE_LANE_BACKGROUND

    async def _enqueue_message(
        self, qq_message: Any, perception: dict, model_name: str = "default"
    ):
        """将消息加入队列"""
        if not self._queue_initialized:
            return await self._process_message_with_perception(
                qq_message, qq_message.message, perception
            )

        is_superadmin = (
            getattr(qq_message, "sender_id", 0) == self._superadmin_qq
            and self._superadmin_qq > 0
        )

        lane = self._get_queue_lane(qq_message, is_superadmin)

        request = {
            "qq_message": qq_message,
            "perception": perception,
            "user_id": getattr(qq_message, "sender_id", 0),
            "group_id": getattr(qq_message, "group_id", 0),
            "model_name": model_name,
        }

        if lane == QUEUE_LANE_SUPERADMIN:
            await self.message_queue.add_superadmin(request, model_name)
        elif lane == QUEUE_LANE_GROUP_SUPERADMIN:
            await self.message_queue.add_group_superadmin(request, model_name)
        elif lane == QUEUE_LANE_PRIVATE:
            await self.message_queue.add_private(request, model_name)
        elif lane == QUEUE_LANE_GROUP_MENTION:
            await self.message_queue.add_group_mention(request, model_name)
        elif lane == QUEUE_LANE_GROUP_NORMAL:
            await self.message_queue.add_group_normal(request, model_name)
        else:
            await self.message_queue.add_background(request, model_name)

    def _init_message_batcher(self):
        """初始化消息汇总窗口期管理器"""
        try:
            from webnet.qq.message_batcher import MessageBatcher
            import yaml

            config_path = Path(__file__).parent.parent / "config" / "qq_config.yaml"
            batch_config = {}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    full_config = yaml.safe_load(f)
                    batch_config = full_config.get("qq", {}).get("message_batching", {})

            enabled = batch_config.get("enabled", True)
            if not enabled:
                self.message_batcher = None
                self.logger.info("[消息汇总] 消息汇总窗口期已禁用")
                return

            async def send_status(group_id, message):
                """发送状态提示回调"""
                if self.qq_net and group_id:
                    try:
                        await self.qq_net.send_group_message(group_id, message)
                    except Exception as e:
                        self.logger.warning(f"[消息汇总] 发送状态提示失败: {e}")

            self.message_batcher = MessageBatcher(
                window_seconds=batch_config.get("window_seconds", 5.0),
                max_window_seconds=batch_config.get("max_window_seconds", 10.0),
                max_messages=batch_config.get("max_messages", 15),
                only_group=batch_config.get("only_group", True),
                status_message=batch_config.get("status_message", ""),
                send_status_callback=send_status,
                cooldown_seconds=batch_config.get("cooldown_seconds", 3.0),
            )

            self.logger.info(
                f"[消息汇总] 消息汇总窗口期已启用: "
                f"window={batch_config.get('window_seconds', 8.0)}s, "
                f"max_window={batch_config.get('max_window_seconds', 15.0)}s, "
                f"max_messages={batch_config.get('max_messages', 20)}"
            )
        except Exception as e:
            self.logger.warning(f"[消息汇总] 消息汇总窗口期初始化失败: {e}")
            self.message_batcher = None

    def _register_mlink_nodes(self):
        """注册 M-Link 节点"""
        if not self.miya.mlink:
            return

        try:
            # 注册 QQNet 节点
            self.miya.mlink.register_node(
                "qq_net",
                [
                    "qq_group_chat",
                    "qq_private_chat",
                    "qq_command",
                    "qq_message_history",
                    "qq_poke",
                    "qq_multimedia",
                    "qq_tts",
                ],
            )

            # 注册 TTSNet 节点（如果存在）
            if self.tts_net:
                self.miya.mlink.register_node(
                    "tts_net", ["tts_generation", "voice_synthesis", "audio_output"]
                )

            self.logger.info("M-Link 节点注册完成")
        except Exception as e:
            self.logger.error(f"M-Link 节点注册失败: {e}")

    def _register_cross_terminal(self):
        """跨端功能已由 Open-ClaudeCode 提供"""
        self.logger.info("跨端功能由 Open-ClaudeCode 提供")

    async def _handle_qq_callback(self, qq_message: Any) -> None:
        """
        处理QQ消息回调

        Args:
            qq_message: QQMessage对象
        """
        try:
            # 记录收到消息
            msg_preview = (
                qq_message.message[:80]
                if len(qq_message.message) > 80
                else qq_message.message
            )
            self.logger.info(
                f"QQ消息 -> {qq_message.message_type} | {qq_message.sender_id}({qq_message.sender_name})"
            )
            if qq_message.group_id:
                self.logger.info(
                    f"    群: {qq_message.group_id}({qq_message.group_name})"
                )
            if qq_message.is_at_bot:
                self.logger.info(f"    @弥娅: 是")
            self.logger.info(f"    内容: {msg_preview}")

            # 检查是否启用消息汇总窗口期
            if self.message_batcher:
                msg_type = qq_message.message_type
                if msg_type not in ["group", "private"]:
                    if qq_message.group_id and qq_message.group_id > 0:
                        msg_type = "group"
                    else:
                        msg_type = "private"

                should_wait = await self.message_batcher.submit_message(
                    message_type=msg_type,
                    group_id=qq_message.group_id,
                    user_id=qq_message.sender_id,
                    sender_name=qq_message.sender_name,
                    content=qq_message.message,
                    is_at_bot=qq_message.is_at_bot,
                    raw_event=getattr(qq_message, "raw_event", None),
                )

                if should_wait:
                    # 消息已加入窗口队列，等待窗口期结束后由后台任务处理
                    return
                # should_wait=False 表示私聊或窗口已满，继续正常处理

            # 单条消息的正常处理流程
            await self._process_single_message(qq_message)

        except Exception as e:
            self.logger.error(f"处理QQ消息失败: {e}", exc_info=True)

    async def _process_single_message(self, qq_message: Any) -> None:
        """处理单条消息（加入队列或直接处理）"""
        safe_msg = {
            k: v
            for k, v in qq_message.__dict__.items()
            if k not in ["image_data", "files", "image_analysis"]
        }
        self.logger.info(f"[_process_single_message] qq_message: {safe_msg}")
        self.logger.info(
            f"[_process_single_message] has_image={getattr(qq_message, 'has_image', 'N/A')}"
        )
        if hasattr(qq_message, "image_analysis"):
            analysis = qq_message.image_analysis
            if analysis and analysis.get("description"):
                desc_len = len(analysis.get("description", ""))
                self.logger.info(
                    f"[_process_single_message] image_analysis: 描述长度={desc_len}字符, 成功={analysis.get('success')}"
                )

        msg_type = qq_message.message_type
        if msg_type not in ["group", "private"]:
            if qq_message.group_id and qq_message.group_id > 0:
                msg_type = "group"
            else:
                msg_type = "private"

        # 【优化】入队前轻量预过滤：纯图片/表情且无@无关键词的群消息，直接跳过
        if msg_type == "group" and not qq_message.is_at_bot:
            # 检查发送者是否为超级管理员
            is_superadmin = (
                self.qq_net and qq_message.sender_id == self.qq_net.superadmin_qq
            )
            if not is_superadmin:
                content_str = str(qq_message.message) if qq_message.message else ""
                has_image = getattr(qq_message, "has_image", False)
                # 纯图片/表情（无实质文本）→ 跳过
                if has_image and (
                    not content_str
                    or content_str.strip() == ""
                    or content_str in ("", "[图片]", "[动画表情]")
                ):
                    self.logger.info(
                        f"[预过滤] 跳过纯图片/表情群消息: group={qq_message.group_id}, sender={qq_message.sender_id}"
                    )
                    return
                # 纯QQ表情消息（face类型无文本）→ 跳过
                if not has_image and (not content_str or content_str.strip() == ""):
                    raw_msg = getattr(qq_message, "raw_message", [])
                    if isinstance(raw_msg, list):
                        is_face_only = all(
                            isinstance(item, dict) and item.get("type") == "face"
                            for item in raw_msg
                        )
                        if is_face_only:
                            self.logger.info(
                                f"[预过滤] 跳过纯QQ表情群消息: group={qq_message.group_id}, sender={qq_message.sender_id}"
                            )
                            return

        perception = {
            "source": "qq",
            "message_type": msg_type,
            "raw_message_type": qq_message.message_type,
            "user_id": qq_message.sender_id,
            "sender_id": qq_message.sender_id,
            "sender_name": qq_message.sender_name,
            "group_id": qq_message.group_id,
            "group_name": getattr(qq_message, "group_name", ""),
            "content": qq_message.message,
            "is_at_bot": qq_message.is_at_bot,
            "at_list": getattr(qq_message, "at_list", []),
            "bot_qq": self.qq_net.bot_qq if self.qq_net else 0,
            "timestamp": datetime.now().isoformat(),
            "message_id": getattr(qq_message, "message_id", 0),
            "reply": getattr(qq_message, "reply", None),
            "files": getattr(qq_message, "files", []),
            "raw_message": getattr(qq_message, "raw_message", []),
            "has_media": getattr(qq_message, "has_media", False),
            "has_image": getattr(qq_message, "has_image", False),
            "image_analysis": getattr(qq_message, "image_analysis", None),
        }

        if self._queue_initialized:
            await self._enqueue_message(qq_message, perception)
        else:
            await self._process_message_with_perception(
                qq_message, qq_message.message, perception
            )

    async def _batch_consumer_loop(self) -> None:
        """后台消费窗口期批次消息的循环"""
        processing_keys = set()  # 防止重复处理
        while True:
            try:
                if not self.message_batcher:
                    await asyncio.sleep(1)
                    continue
                result = await self.message_batcher.get_next_batch()
                if result is None:
                    continue

                group_key, batch = result

                # 防止重复处理同一批次
                if group_key in processing_keys:
                    continue
                processing_keys.add(group_key)

                self.logger.info(
                    f"[消息汇总] 消费批次: {group_key}, {len(batch)} 条消息"
                )
                try:
                    await self._process_message_batch(batch)
                finally:
                    processing_keys.discard(group_key)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"[消息汇总] 消费批次失败: {e}", exc_info=True)

    async def _process_message_batch(self, batch: List) -> None:
        """处理批量消息"""
        if not batch:
            return

        # 使用最后一条消息的 qq_message 对象作为基础
        last_msg = batch[-1]
        first_msg = batch[0]

        # 构建汇总内容
        summarized_content = self._summarize_batch(batch)

        # 创建一个临时的 perception 对象，包含汇总后的消息
        # 收集所有图片分析结果
        image_analyses = []
        has_any_image = False
        for msg in batch:
            if hasattr(msg, "image_analysis") and msg.image_analysis:
                image_analyses.append(
                    {
                        "sender": msg.sender_name,
                        "analysis": msg.image_analysis,
                    }
                )
                has_any_image = True

        msg_type = first_msg.message_type
        if msg_type not in ["group", "private"]:
            group_id = first_msg.group_id
            if group_id and group_id > 0:
                msg_type = "group"
            else:
                msg_type = "private"

        # 构建包含所有消息的 perception
        perception = {
            "source": "qq",
            "message_type": msg_type,
            "raw_message_type": first_msg.message_type,
            "user_id": last_msg.user_id,
            "sender_id": last_msg.user_id,
            "sender_name": last_msg.sender_name,
            "group_id": first_msg.group_id,
            "group_name": getattr(first_msg, "group_name", ""),
            "content": summarized_content,
            "is_at_bot": any(m.is_at_bot for m in batch),
            "at_list": [],
            "bot_qq": self.qq_net.bot_qq if self.qq_net else 0,
            "timestamp": datetime.now().isoformat(),
            "message_id": last_msg.raw_event.get("message_id", 0)
            if last_msg.raw_event
            else 0,
            "reply": None,
            "files": [],
            "has_media": has_any_image,
            "has_image": has_any_image,
            "image_analysis": image_analyses[0]["analysis"] if image_analyses else None,
            "batch_image_analyses": image_analyses if len(image_analyses) > 1 else None,
            "batch_info": {
                "is_batch": True,
                "message_count": len(batch),
                "time_span": f"{batch[-1].timestamp - batch[0].timestamp:.1f}秒",
            },
        }

        # 如果有图片分析结果，直接注入到 perception 的 _image_analysis 字段
        if has_any_image and image_analyses:
            perception["_image_analysis"] = image_analyses[0]["analysis"]
            if len(image_analyses) > 1:
                perception["_batch_image_analyses"] = image_analyses

        class TempQQMessage:
            def __init__(
                self,
                msg_type,
                group_id,
                sender_id,
                sender_name,
                message,
                is_at_bot,
                has_image=False,
                image_analysis=None,
                image_response="",
            ):
                self.message_type = msg_type
                self.group_id = group_id
                self.sender_id = sender_id
                self.sender_name = sender_name
                self.message = message
                self.is_at_bot = is_at_bot
                self.reply = None
                self.files = []
                self.has_media = has_image
                self.has_image = has_image
                self.image_analysis = image_analysis
                self.image_response = image_response
                self.at_list = []
                self.user_id = sender_id

        temp_qq_message = TempQQMessage(
            msg_type=msg_type,
            group_id=first_msg.group_id,
            sender_id=last_msg.user_id,
            sender_name=last_msg.sender_name,
            message=summarized_content,
            is_at_bot=any(m.is_at_bot for m in batch),
            has_image=has_any_image,
            image_analysis=image_analyses[0]["analysis"] if image_analyses else None,
        )

        await self._process_message_with_perception(
            temp_qq_message, summarized_content, perception
        )

    def _summarize_batch(self, batch: List) -> str:
        """将多条消息汇总为一段文本，包含图片分析结果"""
        # 过滤空消息
        valid_msgs = [m for m in batch if m.content and str(m.content).strip()]
        if not valid_msgs:
            return batch[-1].content if batch else ""

        if len(valid_msgs) == 1:
            msg = valid_msgs[0]
            content = msg.content
            if hasattr(msg, "image_analysis") and msg.image_analysis:
                analysis = msg.image_analysis
                desc = analysis.get("description", "")
                if desc:
                    return f"[图片描述] {desc}\n\n用户消息: {content if isinstance(content, str) else '[图片]'}"
            return content if isinstance(content, str) else "[图片]"

        lines = ["【群聊消息汇总】"]
        for msg in valid_msgs:
            sender = msg.sender_name or "未知用户"
            content = msg.content
            image_desc = ""

            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            text_parts.append(item.get("data", {}).get("text", ""))
                        elif item.get("type") == "image":
                            text_parts.append("[图片]")
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = " ".join(text_parts) if text_parts else "[图片]"

                if hasattr(msg, "image_analysis") and msg.image_analysis:
                    analysis = msg.image_analysis
                    desc = analysis.get("description", "")
                    if desc:
                        image_desc = f" (图片内容: {desc[:80]})"

            # 再次检查内容是否为空
            if not content or not str(content).strip():
                continue

            lines.append(f"[{sender}] {content}{image_desc}")

        if len(lines) <= 1:
            # 所有消息都被过滤了，返回最后一条原始消息
            return batch[-1].content if batch else ""

        return "\n".join(lines)

    async def _process_message_with_perception(
        self, qq_message: Any, content: Any, override_perception: Optional[dict] = None
    ) -> None:
        """使用感知数据处理消息"""
        try:
            # 构建感知数据
            msg_type = qq_message.message_type
            if msg_type not in ["group", "private"]:
                if qq_message.group_id and qq_message.group_id > 0:
                    msg_type = "group"
                else:
                    msg_type = "private"

            if override_perception:
                perception = override_perception
            else:
                perception = {
                    "source": "qq",
                    "message_type": msg_type,
                    "raw_message_type": qq_message.message_type,
                    "user_id": qq_message.sender_id,
                    "sender_id": qq_message.sender_id,
                    "sender_name": qq_message.sender_name,
                    "group_id": qq_message.group_id,
                    "group_name": qq_message.group_name,
                    "content": qq_message.message,
                    "is_at_bot": qq_message.is_at_bot,
                    "at_list": qq_message.at_list,
                    "bot_qq": self.qq_net.bot_qq if self.qq_net else 0,
                    "timestamp": datetime.now().isoformat(),
                    "message_id": qq_message.message_id,
                    "reply": {
                        "message_id": qq_message.reply.message_id,
                        "sender_name": qq_message.reply.sender_name,
                        "content": qq_message.reply.content,
                    }
                    if qq_message.reply
                    else None,
                    "files": [
                        {
                            "file_id": f.file_id,
                            "name": f.name,
                            "size": f.size,
                            "file_type": f.file_type,
                        }
                        for f in qq_message.files
                    ]
                    if qq_message.files
                    else [],
                    "has_media": qq_message.has_media,
                    "has_image": qq_message.has_image,
                    "image_analysis": qq_message.image_analysis,
                }

            # 检查消息是否已有图片分析回复（已禁用，直接走决策层）
            # img_keywords_str = ""
            # try:
            #     from core.text_loader import get_text

            #     img_keywords_str = get_text("image_response.keywords", "")
            # except Exception:
            #     pass

            # if hasattr(qq_message, "image_response") and qq_message.image_response:
            #     self.logger.info("[图片回复] 检测到图片分析回复，直接发送")
            #     await self._send_qq_response(qq_message, qq_message.image_response)
            #     return

            # if hasattr(qq_message, "message") and qq_message.message:
            #     msg_content = qq_message.message
            #     if img_keywords_str:
            #         keywords = [
            #             k.strip() for k in img_keywords_str.split(",") if k.strip()
            #         ]
            #         if any(kw in msg_content for kw in keywords):
            #             self.logger.info("[图片回复] 检测到图片分析回复内容，直接发送")
            #             await self._send_qq_response(qq_message, msg_content)
            #             return

            # 检查TTS切换指令
            content_str = str(perception.get("content", "")).strip().lower()
            direct_response = None
            if content_str in ["/voice", "/语音"]:
                if self.qq_net:
                    _ = self.qq_net.set_tts_mode("voice")
                direct_response = "[OK] 已切换为语音模式"
            elif content_str in ["/text", "/文本"]:
                if self.qq_net:
                    _ = self.qq_net.set_tts_mode("text")
                direct_response = "[OK] 已切换为文本模式"

            if direct_response:
                await self._send_qq_response(qq_message, direct_response)
                return

            # 通过 DecisionHub 处理
            if self.miya.mlink and self.miya.decision_hub:
                from mlink.message import Message, MessageType

                message = Message(
                    msg_type=MessageType.DATA.value,
                    content=perception,
                    source="qq_net",
                    destination="decision_hub",
                    priority=1,
                )

                success = await self.miya.mlink.send(message, ["decision_hub"])

                if success:
                    self.logger.info("决策处理 -> 开始")
                    import time

                    start_time = time.time()

                    tool_info = ""
                    tool_calls = []
                    memory_info = ""

                    if (
                        hasattr(self.miya.decision_hub, "tool_subnet")
                        and self.miya.decision_hub.tool_subnet is not None
                    ):
                        tool_info = (
                            self.miya.decision_hub.tool_subnet.get_last_execution_info()
                        )
                    if hasattr(self.miya.decision_hub, "_last_tool_calls"):
                        tool_calls = self.miya.decision_hub._last_tool_calls or []
                    if hasattr(self.miya.decision_hub, "memory_manager"):
                        mm = self.miya.decision_hub.memory_manager
                        if hasattr(mm, "_last_operation"):
                            memory_info = mm._last_operation

                    if tool_calls:
                        self.logger.info(f"工具调用 -> {len(tool_calls)} 个工具")
                    if tool_info:
                        self.logger.info(f"工具详情 -> {tool_info}")
                    if memory_info:
                        self.logger.info(f"记忆操作 -> {memory_info}")

                    perception = message.content
                    content_preview = perception.get("content", "")[:50]
                    self.logger.info(f"消息分析 -> {content_preview}...")

                    response_text = await self.miya.decision_hub.process_perception(
                        message
                    )

                    last_model = getattr(
                        self.miya.decision_hub, "_last_selected_model", ""
                    )
                    last_task_type = getattr(
                        self.miya.decision_hub, "_last_task_type", ""
                    )
                    if last_model:
                        self.logger.info(
                            f"[模型调用] 使用模型: {last_model} | 任务类型: {last_task_type}"
                        )

                    process_time = time.time() - start_time
                    self.logger.info(f"处理完成 -> 耗时: {process_time:.3f}秒")

                    if response_text:
                        response_preview = response_text[:100]
                        self.logger.info(f"弥娅回复 -> {response_preview}...")
                        await self._send_qq_response(qq_message, response_text)
                        self.logger.info(f"消息处理 -> 完成")

                        # 实时记录到 LifeBook 日记
                        if (
                            hasattr(self.miya, "decision_hub")
                            and self.miya.decision_hub
                        ):
                            try:
                                from memory.lifebook import get_lifebook

                                lifebook = get_lifebook()
                                user_msg = perception.get("content", "")
                                topics = []
                                emotion = "平静"
                                await lifebook.record_interaction(
                                    user_message=user_msg,
                                    lover_response=response_text,
                                    topics=topics,
                                    emotion=emotion,
                                )
                                self.logger.debug("LifeBook 实时记录完成")
                            except Exception as e:
                                self.logger.warning(f"LifeBook 实时记录失败: {e}")

                        # 检测离别语，触发会话结束处理
                        if (
                            hasattr(self.miya, "decision_hub")
                            and self.miya.decision_hub
                        ):
                            from core.qq_command_config import is_farewell_keyword

                            if is_farewell_keyword(str(perception.get("content", ""))):
                                self.logger.info("检测到离别语，触发会话结束处理...")
                                try:
                                    user_id = (
                                        str(qq_message.user_id)
                                        if qq_message.user_id
                                        else "qq"
                                    )
                                    await self.miya.decision_hub.handle_session_end(
                                        session_id=user_id, platform="qq"
                                    )
                                    self.logger.info("会话结束处理完成")
                                except Exception as e:
                                    self.logger.error(f"会话结束处理失败: {e}")
                    else:
                        self.logger.warning("弥娅无回复内容")
                else:
                    self.logger.warning("M-Link 发送消息失败")
            else:
                self.logger.warning("M-Link 或决策层未初始化")

        except Exception as e:
            self.logger.error(f"处理QQ消息失败: {e}", exc_info=True)

    async def _send_qq_response(self, qq_message: Any, response_text: str) -> None:
        """发送QQ响应"""
        if not response_text or not self.qq_net:
            return

        filtered_text = response_text

        try:
            import json
            from pathlib import Path

            config_path = Path(__file__).parent.parent / "config" / "text_config.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

                output_filter = config.get("output_filter", {})
                if output_filter.get("enabled", True):
                    threshold = output_filter.get("exclamation_threshold")
                    if threshold and threshold > 0:
                        exclamation_count = sum(1 for c in response_text if c == "!")
                        if exclamation_count >= threshold:
                            fallback_responses = output_filter.get("fallback_responses")
                            if fallback_responses:
                                self.logger.warning(
                                    f"[刷屏过滤] 检测到过多感叹号 ({exclamation_count}个)，将被替换为礼貌回应"
                                )
                                import random

                                filtered_text = random.choice(fallback_responses)
        except Exception:
            pass

        # 【新增】过滤思考过程（DeepSeek R1 等模型的推理内容）
        import re

        patterns_to_remove = [
            r"^好的，用户是在.*?\n",  # 开头的分析段落
            r"^首先，用户.*?\n",
            r"^接下来，我需要.*?\n",
            r"^在之前的对话中.*?\n",
            r"^所以我的回答.*?\n",
            r"^综上所述.*?\n",
            r"^嗯，我是弥娅.*?\n",
            r"^这个问题的回答.*?\n",
            r"^根据设定，我.*?\n",
            r"^作为.*?我.*?\n",
        ]
        for pattern in patterns_to_remove:
            filtered_text = re.sub(pattern, "", filtered_text, flags=re.IGNORECASE)

        # 清理多余空行
        filtered_text = re.sub(r"\n{3,}", "\n\n", filtered_text)
        filtered_text = filtered_text.strip()

        try:
            if qq_message.message_type == "poke":
                if qq_message.group_id and qq_message.group_id > 0:
                    self.logger.info(f"发送群聊拍一拍回复至 {qq_message.group_id}")
                    _ = await self.qq_net.send_group_message(
                        qq_message.group_id, filtered_text
                    )
                elif qq_message.user_id and qq_message.user_id > 0:
                    self.logger.info(f"发送私聊拍一拍回复至 {qq_message.user_id}")
                    _ = await self.qq_net.send_private_message(
                        qq_message.user_id, filtered_text
                    )
            elif qq_message.message_type == "group":
                self.logger.info(f"发送群消息至 {qq_message.group_id}")
                _ = await self.qq_net.send_group_message(
                    qq_message.group_id, filtered_text
                )
            elif qq_message.message_type == "private":
                self.logger.info(f"发送私聊消息至 {qq_message.user_id}")
                _ = await self.qq_net.send_private_message(
                    qq_message.user_id, filtered_text
                )
        except Exception as e:
            self.logger.error(f"QQ响应发送失败: {e}", exc_info=True)

    async def start(self):
        """启动 QQ 机器人"""
        self.logger.info("弥娅 QQ 机器人启动中...")

        try:
            # 连接到 QQ
            if self.qq_net:
                self.logger.info("连接到 OneBot WebSocket...")
                await self.qq_net.connect()
                self.logger.info("QQ 机器人连接成功！")

                # 设置 onebot_client 到 decision_hub
                if (
                    self.miya.decision_hub
                    and hasattr(self.qq_net, "onebot_client")
                    and self.qq_net.onebot_client
                ):
                    self.miya.decision_hub.onebot_client = self.qq_net.onebot_client
                    self.logger.info("DecisionHub onebot_client 已设置")

                # 设置 qq_net 引用到 decision_hub（用于权限检查）
                if self.miya.decision_hub and self.qq_net:
                    self.miya.decision_hub.qq_net = self.qq_net
                    self.logger.info("DecisionHub qq_net 已设置")

                # 2. 主动聊天系统通过 DecisionHub 管理 (core/proactive_chat)

                # 3. 跨端终端注册
                self.logger.info("注册跨端终端...")
                self._register_cross_terminal()

                # 4. 加载定时任务
                self.logger.info("加载定时任务...")

                # 启动定时任务调度器
                if self.miya.scheduler:
                    try:
                        # 设置 onebot_client 用于发送消息
                        if self.qq_net and self.qq_net.onebot_client:
                            self.miya.scheduler.onebot_client = (
                                self.qq_net.onebot_client
                            )

                        # 设置全局调度器（用于ToolNet中的工具获取）
                        from hub.scheduler import set_global_scheduler

                        set_global_scheduler(self.miya.scheduler)

                        # 启动调度器
                        await self.miya.scheduler.start()
                        self.logger.info("定时任务调度器已启动")
                    except Exception as e:
                        self.logger.warning(f"定时任务调度器启动失败: {e}")

                # 5. 启动消息汇总窗口期消费者
                if self.message_batcher:
                    self._batch_consumer_task = asyncio.create_task(
                        self._batch_consumer_loop()
                    )
                    self.logger.info("消息汇总消费者已启动")

                # 6. 启动消息接收循环
                self.logger.info("启动消息接收循环...")

                if self.miya.identity:
                    self.logger.info(f"弥娅 QQ 机器人已启动: {self.miya.identity.name}")
                    self.logger.info(f"  UUID: {self.miya.identity.uuid}")
                    self.logger.info(f"  版本: {self.miya.identity.version}")
                self.logger.info(f"  工具: ToolNet (新版架构)")
                self.logger.info(f"  主动聊天: 已启用 (定时+上下文)")
                self.logger.info(f"  跨端联动: 已启用")

                # 启动 QQNet
                await self.qq_net.start()

        except KeyboardInterrupt:
            self.logger.info("\n收到中断信号，正在关闭...")
        except Exception as e:
            self.logger.error(f"启动失败: {e}", exc_info=True)
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        """清理资源"""
        self.logger.info("正在清理资源...")
        if self.message_batcher:
            await self.message_batcher.shutdown()
        if hasattr(self, "_batch_consumer_task") and self._batch_consumer_task:
            self._batch_consumer_task.cancel()
            try:
                await self._batch_consumer_task
            except asyncio.CancelledError:
                pass
        if self.qq_net:
            await self.qq_net.stop()
        self.logger.info("已停止")


async def main():
    """主函数"""
    print("弥娅 QQ 机器人启动中...")

    app = MiyaQQ()

    try:
        await app.initialize()
        await app.start()
    except ConnectionRefusedError as e:
        print()
        print("=" * 60)
        print("[ERROR] 连接失败!")
        print("=" * 60)
        print()
        print(f"错误信息: {e}")
        print()
        print("可能的原因:")
        print("  1. OneBot服务未启动")
        print("  2. WebSocket地址配置错误")
        print("  3. 端口被占用")
        print()
        print("解决方法:")
        print("  1. 启动OneBot服务 (NapCat或go-cqhttp)")
        print("  2. 检查 config/.env 中的 QQ_ONEBOT_WS_URL")
        print("  3. 参考 docs/QQ_BOT_SETUP.md 进行配置")
        print()
        print("=" * 60)
    except Exception as e:
        print(f"启动失败: {e}")
        logging.error(f"运行错误: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
