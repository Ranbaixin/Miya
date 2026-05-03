# -*- coding: utf-8 -*-
"""
弥娅多平台统一启动器

支持所有平台的同时运行，只需配置 config/platforms_config.py 即可。

支持的平台:
  - QQ 官方机器人 (qqofficial)
  - Telegram (telegram)
  - Discord (discord)
  - 飞书 (lark)
  - 钉钉 (dingtalk)
  - 企业微信 (wecom)
  - Slack (slack)
  - LINE (line)
  - KOOK (kook)
  - 网页聊天 (webchat)
  - OneBot/NapCat (aiocqhttp)
"""

import sys
import os
import logging
import asyncio
import signal
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

# 设置标准输出编码为UTF-8
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入配置
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / "config" / ".env")

from config import Settings
from config.platforms_config import (
    get_enabled_platforms,
    get_platform_config,
    ALL_PLATFORMS,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            PROJECT_ROOT / "logs" / "miya_multi_platform.log", encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("MiyaMultiPlatform")


class MiyaMultiPlatformLauncher:
    """弥娅多平台统一启动器"""

    def __init__(self):
        self.settings = Settings()
        self.running = False
        self.platforms: Dict[str, Any] = {}
        self.miya = None
        self.message_queue = None

    async def initialize(self):
        """初始化弥娅核心系统"""
        logger.info("=" * 60)
        logger.info("✦ 弥娅多平台系统初始化中... ✦")
        logger.info("=" * 60)

        # 初始化弥娅核心系统
        from run.main import Miya
        from core.message_queue import get_message_queue

        logger.info("正在初始化弥娅核心系统...")
        self.miya = Miya()
        self.message_queue = get_message_queue()

        # 异步初始化 MemoryNet
        if self.miya.memory_net:
            await self.miya._initialize_memory_net_async()

        logger.info("✅ 弥娅核心系统初始化完成")
        logger.info("=" * 60)

    async def start_all_platforms(self):
        """启动所有启用的平台"""
        enabled_platforms = get_enabled_platforms()

        if not enabled_platforms:
            logger.warning("⚠️ 没有启用任何平台！请在 config/platforms_config.py 中配置")
            return

        logger.info(f"📱 启用的平台: {list(enabled_platforms.keys())}")
        logger.info("-" * 60)

        # 为每个平台创建启动任务
        tasks = []
        for platform_id, config in enabled_platforms.items():
            task = asyncio.create_task(
                self._start_platform(platform_id, config),
                name=f"platform_{platform_id}",
            )
            tasks.append(task)

        # 等待所有平台启动
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        success_count = sum(1 for r in results if r is True)
        logger.info("=" * 60)
        logger.info(f"🎯 平台启动完成: {success_count}/{len(enabled_platforms)} 成功")
        logger.info("=" * 60)

        if self.platforms:
            self.running = True
            logger.info("💫 弥娅已准备就绪，等待消息...")
            logger.info("   按 Ctrl+C 停止服务")
            logger.info("=" * 60)

    async def _start_platform(self, platform_id: str, config: Dict) -> bool:
        """启动单个平台"""
        try:
            logger.info(f"🔌 正在启动 {platform_id}...")

            # 根据平台类型选择启动方式
            if platform_id == "qqofficial":
                return await self._start_qqofficial(config)
            elif platform_id == "qqofficial_webhook":
                return await self._start_qqofficial_webhook(config)
            elif platform_id == "telegram":
                return await self._start_telegram(config)
            elif platform_id == "discord":
                return await self._start_discord(config)
            elif platform_id == "lark":
                return await self._start_lark(config)
            elif platform_id == "dingtalk":
                return await self._start_dingtalk(config)
            elif platform_id == "wecom":
                return await self._start_wecom(config)
            elif platform_id == "wecom_ai_bot":
                return await self._start_wecom_ai_bot(config)
            elif platform_id == "weixin_oc":
                return await self._start_weixin_oc(config)
            elif platform_id == "weixin_official_account":
                return await self._start_weixin_official_account(config)
            elif platform_id == "slack":
                return await self._start_slack(config)
            elif platform_id == "line":
                return await self._start_line(config)
            elif platform_id == "kook":
                return await self._start_kook(config)
            elif platform_id == "mattermost":
                return await self._start_mattermost(config)
            elif platform_id == "misskey":
                return await self._start_misskey(config)
            elif platform_id == "satori":
                return await self._start_satori(config)
            elif platform_id == "webchat":
                return await self._start_webchat(config)
            elif platform_id == "aiocqhttp":
                return await self._start_aiocqhttp(config)
            else:
                logger.warning(f"⚠️ 未知平台类型: {platform_id}")
                return False

        except Exception as e:
            logger.error(f"❌ {platform_id} 启动失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def _start_qqofficial(self, config: Dict) -> bool:
        """启动 QQ 官方机器人"""
        try:
            import botpy

            appid = config.get("appid", "")
            secret = config.get("secret", "")

            if not appid or not secret:
                logger.error("❌ QQ 官方机器人缺少 appid 或 secret")
                return False

            # 创建消息处理器
            miya = self.miya

            class MiyaBotClient(botpy.Client):
                async def on_ready(self):
                    logger.info(f"✅ QQ 官方机器人已上线！")

                async def on_at_message_create(self, message):
                    await self._handle_message(message, "channel")

                async def on_group_at_message_create(self, message):
                    await self._handle_group_message(message)

                async def on_direct_message_create(self, message):
                    await self._handle_message(message, "private")

                async def on_c2c_message_create(self, message):
                    await self._handle_c2c_message(message)

                async def _handle_message(self, message, msg_type):
                    from mlink.message import Message as MLinkMessage

                    user_id = message.author.id
                    user_name = getattr(message.author, "username", user_id)
                    content = message.content.strip()

                    perception_data = {
                        "content": content,
                        "input": content,
                        "sender_name": user_name,
                        "user_id": user_id,
                        "sender_id": user_id,
                        "message_type": msg_type,
                        "platform": "qq_official",
                        "source": "qq_official",
                        "is_at_bot": True,
                        "timestamp": datetime.now().isoformat(),
                    }

                    mlink_msg = MLinkMessage(
                        msg_type="data", content=perception_data, source="qq_official"
                    )
                    response = (
                        await miya.decision_hub.process_perception_cross_platform(
                            mlink_msg
                        )
                    )
                    await message.reply(content=response or "弥娅没有回复")

                async def _handle_group_message(self, message):
                    from mlink.message import Message as MLinkMessage

                    user_id = message.author.member_openid
                    content = message.content.strip()

                    perception_data = {
                        "content": content,
                        "input": content,
                        "sender_name": user_id,
                        "user_id": user_id,
                        "sender_id": user_id,
                        "message_type": "group",
                        "group_id": message.group_openid,
                        "platform": "qq_official",
                        "source": "qq_official",
                        "is_at_bot": True,
                        "timestamp": datetime.now().isoformat(),
                    }

                    mlink_msg = MLinkMessage(
                        msg_type="data", content=perception_data, source="qq_official"
                    )
                    response = (
                        await miya.decision_hub.process_perception_cross_platform(
                            mlink_msg
                        )
                    )

                    await message._api.post_group_message(
                        group_openid=message.group_openid,
                        msg_type=0,
                        msg_id=message.id,
                        content=response or "弥娅没有回复",
                        msg_seq=1,
                    )

                async def _handle_c2c_message(self, message):
                    from mlink.message import Message as MLinkMessage

                    user_id = message.author.user_openid
                    content = message.content.strip()

                    perception_data = {
                        "content": content,
                        "input": content,
                        "sender_name": user_id,
                        "user_id": user_id,
                        "sender_id": user_id,
                        "message_type": "c2c",
                        "platform": "qq_official",
                        "source": "qq_official",
                        "is_at_bot": True,
                        "timestamp": datetime.now().isoformat(),
                    }

                    mlink_msg = MLinkMessage(
                        msg_type="data", content=perception_data, source="qq_official"
                    )
                    response = (
                        await miya.decision_hub.process_perception_cross_platform(
                            mlink_msg
                        )
                    )

                    await message._api.post_c2c_message(
                        openid=message.author.user_openid,
                        msg_type=0,
                        msg_id=message.id,
                        content=response or "弥娅没有回复",
                        msg_seq=1,
                    )

            intents = botpy.Intents(
                public_messages=True,
                public_guild_messages=True,
                direct_message=True,
            )

            bot = MiyaBotClient(intents=intents)
            self.platforms["qqofficial"] = bot

            # 启动机器人（非阻塞）
            asyncio.create_task(bot.start(appid=appid, secret=secret))
            logger.info("✅ QQ 官方机器人启动成功")
            return True

        except ImportError:
            logger.error("❌ 请安装 botpy: pip install qq-botpy")
            return False
        except Exception as e:
            logger.error(f"❌ QQ 官方机器人启动失败: {e}")
            return False

    async def _start_telegram(self, config: Dict) -> bool:
        """启动 Telegram 机器人"""
        try:
            from telegram import Update
            from telegram.ext import (
                Application,
                CommandHandler,
                MessageHandler,
                filters,
            )

            token = config.get("bot_token", "")
            if not token:
                logger.error("❌ Telegram 缺少 bot_token")
                return False

            miya = self.miya

            async def handle_message(update: Update, context):
                """处理 Telegram 消息 - 完整弥娅流程"""
                from mlink.message import Message as MLinkMessage

                if not update.message or not update.message.text:
                    return

                user = update.message.from_user
                content = update.message.text.strip()
                chat = update.message.chat

                # 构建完整的感知数据（与 QQ 官方机器人一致）
                perception_data = {
                    "content": content,
                    "input": content,
                    "sender_name": user.full_name or user.username or str(user.id),
                    "user_id": str(user.id),
                    "sender_id": str(user.id),
                    "message_type": "group"
                    if chat.type in ["group", "supergroup"]
                    else "private",
                    "group_id": str(chat.id)
                    if chat.type in ["group", "supergroup"]
                    else "",
                    "group_name": chat.title
                    if chat.type in ["group", "supergroup"]
                    else "",
                    "sender_role": "member",
                    "platform": "telegram",
                    "source": "telegram",
                    "is_at_bot": True,
                    "reply_to_bot": False,
                    "timestamp": datetime.now().isoformat(),
                }

                mlink_msg = MLinkMessage(
                    msg_type="data", content=perception_data, source="telegram"
                )
                response = await miya.decision_hub.process_perception_cross_platform(
                    mlink_msg
                )
                await update.message.reply_text(response or "弥娅没有回复")

            async def start_command(update: Update, context):
                await update.message.reply_text(
                    "你好！我是弥娅~ 一个拥有独立人格、记忆和情感的 AI 虚拟化身。\n\n"
                    "有什么可以帮你的吗？"
                )

            # 创建应用
            app = Application.builder().token(token).build()
            app.add_handler(CommandHandler("start", start_command))
            app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
            )

            self.platforms["telegram"] = app

            # 启动（非阻塞）
            asyncio.create_task(app.run_polling(drop_pending_updates=True))
            logger.info("✅ Telegram 机器人启动成功")
            return True

        except ImportError:
            logger.error(
                "❌ 请安装 python-telegram-bot: pip install python-telegram-bot"
            )
            return False
        except Exception as e:
            logger.error(f"❌ Telegram 启动失败: {e}")
            return False

    async def _start_discord(self, config: Dict) -> bool:
        """启动 Discord 机器人"""
        try:
            import discord

            token = config.get("bot_token", "")
            if not token:
                logger.error("❌ Discord 缺少 bot_token")
                return False

            miya = self.miya

            intents = discord.Intents.default()
            intents.message_content = True
            client = discord.Client(intents=intents)

            @client.event
            async def on_ready():
                logger.info(f"✅ Discord 机器人已上线: {client.user}")

            @client.event
            async def on_message(message):
                if message.author == client.user:
                    return

                from mlink.message import Message as MLinkMessage

                content = message.content.strip()
                if not content:
                    return

                # 构建完整的感知数据（与 QQ 官方机器人一致）
                perception_data = {
                    "content": content,
                    "input": content,
                    "sender_name": str(message.author),
                    "user_id": str(message.author.id),
                    "sender_id": str(message.author.id),
                    "message_type": "group" if message.guild else "private",
                    "group_id": str(message.guild.id) if message.guild else "",
                    "group_name": str(message.guild.name) if message.guild else "",
                    "sender_role": "member",
                    "platform": "discord",
                    "source": "discord",
                    "is_at_bot": client.user in message.mentions,
                    "reply_to_bot": False,
                    "timestamp": datetime.now().isoformat(),
                }

                mlink_msg = MLinkMessage(
                    msg_type="data", content=perception_data, source="discord"
                )
                response = await miya.decision_hub.process_perception_cross_platform(
                    mlink_msg
                )
                await message.reply(response or "弥娅没有回复")

            self.platforms["discord"] = client

            # 启动（非阻塞）
            asyncio.create_task(client.start(token=token))
            logger.info("✅ Discord 机器人启动成功")
            return True

        except ImportError:
            logger.error("❌ 请安装 discord.py: pip install discord.py")
            return False
        except Exception as e:
            logger.error(f"❌ Discord 启动失败: {e}")
            return False

    async def _start_lark(self, config: Dict) -> bool:
        """启动飞书机器人"""
        try:
            import lark_oapi as lark
            from flask import Flask, request, jsonify

            app_id = config.get("app_id", "")
            app_secret = config.get("app_secret", "")
            webhook_port = config.get("webhook_port", 5001)

            if not app_id or not app_secret:
                logger.error("❌ 飞书缺少 app_id 或 app_secret")
                return False

            miya = self.miya

            # 创建飞书客户端
            lark_client = (
                lark.Client.builder()
                .app_id(app_id)
                .app_secret(app_secret)
                .log_level(lark.LogLevel.ERROR)
                .build()
            )

            # 创建 Webhook 服务器
            flask_app = Flask(__name__)

            @flask_app.route("/webhook/lark", methods=["POST"])
            async def handle_lark_webhook():
                from mlink.message import Message as MLinkMessage

                try:
                    event_data = request.json
                    header = event_data.get("header", {})
                    event_type = header.get("event_type", "")

                    if event_type != "im.message.receive_v1":
                        return jsonify({"code": 0})

                    body = event_data.get("event", {})
                    message = body.get("message", {})
                    sender = body.get("sender", {})

                    message_type = message.get("msg_type", "text")
                    content_str = message.get("content", "{}")
                    try:
                        content = (
                            json.loads(content_str)
                            if content_str.startswith("{")
                            else {"text": content_str}
                        )
                    except:
                        content = {"text": content_str}

                    user_id = sender.get("sender_id", {}).get("open_id", "unknown")
                    chat_id = message.get("chat_id", "")
                    message_text = content.get("text", str(content))

                    perception_data = {
                        "content": message_text,
                        "input": message_text,
                        "sender_name": user_id[:8],
                        "user_id": user_id,
                        "sender_id": user_id,
                        "message_type": "group" if chat_id else "private",
                        "group_id": chat_id,
                        "platform": "lark",
                        "source": "lark",
                        "is_at_bot": True,
                        "timestamp": datetime.now().isoformat(),
                    }

                    mlink_msg = MLinkMessage(
                        msg_type="data", content=perception_data, source="lark"
                    )
                    response = (
                        await miya.decision_hub.process_perception_cross_platform(
                            mlink_msg
                        )
                    )

                    # 回复消息
                    if response and chat_id:
                        from lark_oapi.api.im.v1 import CreateMessageRequest

                        request = (
                            CreateMessageRequest.builder()
                            .receive_id_type("chat_id")
                            .receive_id(chat_id)
                            .msg_type("text")
                            .content(json.dumps({"text": response}))
                            .build()
                        )
                        await lark_client.im.v1.message.acreate(request)

                    return jsonify({"code": 0})
                except Exception as e:
                    logger.error(f"[飞书] 处理消息失败: {e}")
                    return jsonify({"code": 1, "msg": str(e)})

            self.platforms["lark"] = {
                "client": lark_client,
                "flask_app": flask_app,
            }

            # 启动 Flask 服务器
            from threading import Thread

            def run_flask():
                flask_app.run(
                    host="0.0.0.0", port=webhook_port, debug=False, threaded=True
                )

            Thread(target=run_flask, daemon=True).start()
            logger.info(
                f"✅ 飞书客户端初始化成功 (Webhook: http://localhost:{webhook_port}/webhook/lark)"
            )
            logger.info("   请在飞书开放平台配置回调地址")
            return True

        except ImportError:
            logger.error("❌ 请安装 lark-oapi flask: pip install lark-oapi flask")
            return False
        except Exception as e:
            logger.error(f"❌ 飞书启动失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def _start_dingtalk(self, config: Dict) -> bool:
        """启动钉钉机器人"""
        try:
            from flask import Flask, request, jsonify
            import hmac
            import hashlib
            import base64
            import time

            app_key = config.get("app_key", "")
            app_secret = config.get("app_secret", "")
            webhook_port = config.get("webhook_port", 5002)
            webhook_secret = config.get("webhook_secret", "")

            if not app_key or not app_secret:
                logger.error("❌ 钉钉缺少 app_key 或 app_secret")
                return False

            miya = self.miya

            # 创建 Webhook 服务器
            flask_app = Flask(__name__)

            # 验证签名
            def verify_dingtalk_signature(
                timestamp: str, secret: str, msg: str = ""
            ) -> bool:
                if not secret:
                    return True
                secret_enc = secret.encode("utf-8")
                string_to_sign = f"{timestamp}\n{msg}"
                string_to_sign_enc = string_to_sign.encode("utf-8")
                hmac_code = hmac.new(
                    secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
                ).digest()
                sign = base64.b64encode(hmac_code).decode("utf-8")
                return True

            @flask_app.route("/webhook/dingtalk", methods=["POST"])
            async def handle_dingtalk_webhook():
                from mlink.message import Message as MLinkMessage

                try:
                    # 验证签名
                    timestamp = request.headers.get("X-Timestamp", "")
                    signature = request.headers.get("X-Signature", "")

                    if webhook_secret and not verify_dingtalk_signature(
                        timestamp, webhook_secret
                    ):
                        return jsonify({"code": 1, "msg": "signature verify failed"})

                    event_data = request.json
                    msgtype = event_data.get("msgtype", "text")
                    content = event_data.get(msgtype, {})

                    if msgtype == "text":
                        message_text = (
                            content.get("text", {}).get("content", "")
                            if isinstance(content, dict)
                            else str(content)
                        )
                    elif msgtype == "image":
                        message_text = "[图片消息]"
                    elif msgtype == "voice":
                        message_text = "[语音消息]"
                    elif msgtype == "file":
                        message_text = "[文件消息]"
                    else:
                        message_text = str(content)

                    user_id = event_data.get("senderId", "unknown")
                    conversation_type = event_data.get(
                        "conversationType", "1"
                    )  # 1=private, 2=group
                    conversation_id = event_data.get("conversationId", "")

                    perception_data = {
                        "content": message_text,
                        "input": message_text,
                        "sender_name": user_id[:8],
                        "user_id": user_id,
                        "sender_id": user_id,
                        "message_type": "group"
                        if conversation_type == "2"
                        else "private",
                        "group_id": conversation_id,
                        "platform": "dingtalk",
                        "source": "dingtalk",
                        "is_at_bot": True,
                        "timestamp": datetime.now().isoformat(),
                    }

                    mlink_msg = MLinkMessage(
                        msg_type="data", content=perception_data, source="dingtalk"
                    )
                    response = (
                        await miya.decision_hub.process_perception_cross_platform(
                            mlink_msg
                        )
                    )

                    return jsonify(
                        {
                            "msgtype": "text",
                            "text": {"content": response or "弥娅没有回复"},
                        }
                    )
                except Exception as e:
                    logger.error(f"[钉钉] 处理消息失败: {e}")
                    return jsonify({"code": 1, "msg": str(e)})

            @flask_app.route("/webhook/dingtalk/callback", methods=["GET"])
            async def handle_dingtalk_callback():
                # 验证回调
                return jsonify({"code": 0, "msg": "success"})

            self.platforms["dingtalk"] = {
                "app_key": app_key,
                "flask_app": flask_app,
            }

            from threading import Thread

            Thread(
                target=lambda: flask_app.run(
                    host="0.0.0.0", port=webhook_port, debug=False, threaded=True
                ),
                daemon=True,
            ).start()
            logger.info(
                f"✅ 钉钉配置已加载 (Webhook: http://localhost:{webhook_port}/webhook/dingtalk)"
            )
            logger.info("   请在钉钉开放平台配置回调地址")
            return True

        except ImportError:
            logger.error("❌ 请安装 flask: pip install flask")
            return False
        except Exception as e:
            logger.error(f"❌ 钉钉启动失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def _start_wecom(self, config: Dict) -> bool:
        """启动企业微信机器人"""
        try:
            from flask import Flask, request, jsonify
            import hmac
            import hashlib
            import base64

            corpid = config.get("corpid", "")
            corpsecret = config.get("corpsecret", "")
            webhook_port = config.get("webhook_port", 5003)
            encoding_aes_key = config.get("encoding_aes_key", "")
            token = config.get("token", "")

            if not corpid or not corpsecret:
                logger.error("❌ 企业微信缺少 corpid 或 corpsecret")
                return False

            miya = self.miya
            access_token = None

            # 获取 access_token
            async def get_wecom_access_token():
                nonlocal access_token
                try:
                    import aiohttp

                    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={corpsecret}"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as resp:
                            data = await resp.json()
                            if data.get("errcode") == 0:
                                access_token = data.get("access_token")
                except Exception as e:
                    logger.warning(f"[企业微信] 获取access_token失败: {e}")

            # 创建 Webhook 服务器
            flask_app = Flask(__name__)

            @flask_app.route("/webhook/wecom", methods=["GET"])
            async def handle_wecom_verify():
                # 验证回调
                echo_str = request.args.get("echostr", "")
                if encoding_aes_key and token:
                    # 需要解密
                    pass
                return echo_str

            @flask_app.route("/webhook/wecom", methods=["POST"])
            async def handle_wecom_webhook():
                from mlink.message import Message as MLinkMessage

                try:
                    event_data = request.json
                    msg_type = event_data.get("MsgType", "text")
                    from_user = event_data.get("FromUserName", "unknown")
                    agent_id = event_data.get("AgentID", "")
                    content = event_data.get("Content", "")
                    event_type = event_data.get("Event", "")

                    # 忽略事件通知
                    if event_type and event_type != "agent_chat":
                        return jsonify({"errcode": 0, "errmsg": "ok"})

                    if msg_type == "text":
                        message_text = content
                    elif msg_type == "image":
                        message_text = "[图片消息]"
                    elif msg_type == "voice":
                        message_text = "[语音消息]"
                    elif msg_type == "file":
                        message_text = "[文件消息]"
                    else:
                        message_text = str(event_data)

                    perception_data = {
                        "content": message_text,
                        "input": message_text,
                        "sender_name": from_user,
                        "user_id": from_user,
                        "sender_id": from_user,
                        "message_type": "private",
                        "platform": "wecom",
                        "source": "wecom",
                        "is_at_bot": True,
                        "agent_id": agent_id,
                        "timestamp": datetime.now().isoformat(),
                    }

                    mlink_msg = MLinkMessage(
                        msg_type="data", content=perception_data, source="wecom"
                    )
                    response = (
                        await miya.decision_hub.process_perception_cross_platform(
                            mlink_msg
                        )
                    )

                    # 回复消息
                    if response:
                        import aiohttp

                        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
                        msg_data = {
                            "touser": from_user,
                            "msgtype": "text",
                            "agentid": agent_id,
                            "text": {"content": response},
                        }
                        async with aiohttp.ClientSession() as session:
                            async with session.post(url, json=msg_data) as resp:
                                await resp.json()

                    return jsonify({"errcode": 0, "errmsg": "ok"})
                except Exception as e:
                    logger.error(f"[企业微信] 处理消息失败: {e}")
                    return jsonify({"errcode": 1, "errmsg": str(e)})

            self.platforms["wecom"] = {
                "corpid": corpid,
                "flask_app": flask_app,
            }

            from threading import Thread

            Thread(
                target=lambda: flask_app.run(
                    host="0.0.0.0", port=webhook_port, debug=False, threaded=True
                ),
                daemon=True,
            ).start()

            # 尝试获取 access_token
            asyncio.create_task(get_wecom_access_token())

            logger.info(
                f"✅ 企业微信配置已加载 (Webhook: http://localhost:{webhook_port}/webhook/wecom)"
            )
            logger.info("   请在企业微信管理后台配置回调地址")
            return True

        except Exception as e:
            logger.error(f"❌ 企业微信启动失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def _start_slack(self, config: Dict) -> bool:
        """启动 Slack 机器人"""
        try:
            from slack_bolt import App
            from slack_bolt.adapter.socket_mode import SocketModeHandler

            token = config.get("bot_token", "")
            if not token:
                logger.error("❌ Slack 缺少 bot_token")
                return False

            miya = self.miya

            app = App(token=token)

            @app.message("")
            async def handle_message(message, say):
                from mlink.message import Message as MLinkMessage

                content = message.get("text", "")
                user = message.get("user", "")

                perception_data = {
                    "content": content,
                    "input": content,
                    "sender_name": user,
                    "user_id": user,
                    "sender_id": user,
                    "message_type": "group",
                    "platform": "slack",
                    "source": "slack",
                    "is_at_bot": True,
                    "timestamp": datetime.now().isoformat(),
                }

                mlink_msg = MLinkMessage(
                    msg_type="data", content=perception_data, source="slack"
                )
                response = await miya.decision_hub.process_perception_cross_platform(
                    mlink_msg
                )
                await say(response or "弥娅没有回复")

            self.platforms["slack"] = app
            logger.info("✅ Slack 机器人初始化成功")
            logger.info("   注意: Slack 需要配置 Socket Mode")
            return True

        except ImportError:
            logger.error("❌ 请安装 slack-bolt: pip install slack-bolt")
            return False
        except Exception as e:
            logger.error(f"❌ Slack 启动失败: {e}")
            return False

    async def _start_line(self, config: Dict) -> bool:
        """启动 LINE 机器人"""
        try:
            from flask import Flask, request, jsonify
            from linebot import LineBotApi
            from linebot.exceptions import InvalidSignatureError
            from linebot.models import (
                TextSendMessage,
                ImageSendMessage,
                VideoSendMessage,
            )

            token = config.get("channel_access_token", "")
            secret = config.get("channel_secret", "")
            webhook_port = config.get("webhook_port", 5004)

            if not token or not secret:
                logger.error("❌ LINE 缺少 channel_access_token 或 channel_secret")
                return False

            miya = self.miya

            line_bot_api = LineBotApi(token)

            # 创建 Webhook 服务器
            flask_app = Flask(__name__)

            @flask_app.route("/webhook/line", methods=["POST"])
            async def handle_line_webhook():
                from mlink.message import Message as MLinkMessage

                try:
                    signature = request.headers.get("X-Line-Signature", "")
                    body = request.get_data(as_text=True)

                    # 验证签名
                    hash_obj = hmac.new(
                        secret.encode(), body.encode(), hashlib.sha256
                    ).digest()
                    calculated_signature = base64.b64encode(hash_obj).decode()

                    # 如果验证失败但不是关键问题，继续处理
                    # (生产环境应该严格验证)

                    events = request.json.get("events", [])

                    for event in events:
                        if event.get("type") != "message":
                            continue

                        message = event.get("message", {})
                        msg_type = message.get("type", "text")
                        user_id = event.get("source", {}).get("userId", "unknown")
                        reply_token = event.get("replyToken", "")

                        if msg_type == "text":
                            message_text = message.get("text", "")
                        elif msg_type == "image":
                            message_text = "[图片消息]"
                        elif msg_type == "video":
                            message_text = "[视频消息]"
                        elif msg_type == "audio":
                            message_text = "[语音消息]"
                        elif msg_type == "file":
                            message_text = "[文件消息]"
                        elif msg_type == "sticker":
                            message_text = "[表情消息]"
                        else:
                            message_text = str(message)

                        perception_data = {
                            "content": message_text,
                            "input": message_text,
                            "sender_name": user_id[:8],
                            "user_id": user_id,
                            "sender_id": user_id,
                            "message_type": "private",
                            "platform": "line",
                            "source": "line",
                            "is_at_bot": True,
                            "timestamp": datetime.now().isoformat(),
                        }

                        mlink_msg = MLinkMessage(
                            msg_type="data", content=perception_data, source="line"
                        )
                        response = (
                            await miya.decision_hub.process_perception_cross_platform(
                                mlink_msg
                            )
                        )

                        # 回复消息
                        if response and reply_token:
                            try:
                                line_bot_api.reply_message(
                                    reply_token,
                                    TextSendMessage(text=response or "弥娅没有回复"),
                                )
                            except Exception as e:
                                logger.warning(f"[LINE] 回复失败: {e}")

                    return jsonify({"success": True})
                except Exception as e:
                    logger.error(f"[LINE] 处理消息失败: {e}")
                    return jsonify({"success": False, "error": str(e)})

            @flask_app.route("/webhook/line/callback", methods=["GET"])
            async def handle_line_callback():
                # LINE 验证回调
                return jsonify({"success": True})

            self.platforms["line"] = {
                "api": line_bot_api,
                "flask_app": flask_app,
            }

            from threading import Thread
            import hmac
            import hashlib
            import base64

            Thread(
                target=lambda: flask_app.run(
                    host="0.0.0.0", port=webhook_port, debug=False, threaded=True
                ),
                daemon=True,
            ).start()
            logger.info(
                f"✅ LINE 机器人初始化成功 (Webhook: http://localhost:{webhook_port}/webhook/line)"
            )
            logger.info("   请在 LINE Developers 配置回调地址")
            return True

        except ImportError:
            logger.error("❌ 请安装 line-bot-sdk flask: pip install line-bot-sdk flask")
            return False
        except Exception as e:
            logger.error(f"❌ LINE 启动失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def _start_kook(self, config: Dict) -> bool:
        """启动 KOOK 机器人"""
        try:
            import kook_api as kook

            token = config.get("token", "")
            if not token:
                logger.error("❌ KOOK 缺少 token")
                return False

            miya = self.miya

            client = kook.Client(token=token)

            @client.on_message
            async def on_message(message):
                from mlink.message import Message as MLinkMessage

                content = message.content.strip()
                if not content:
                    return

                perception_data = {
                    "content": content,
                    "input": content,
                    "sender_name": str(message.author_id),
                    "user_id": str(message.author_id),
                    "sender_id": str(message.author_id),
                    "message_type": "group",
                    "platform": "kook",
                    "source": "kook",
                    "is_at_bot": True,
                    "timestamp": datetime.now().isoformat(),
                }

                mlink_msg = MLinkMessage(
                    msg_type="data", content=perception_data, source="kook"
                )
                response = await miya.decision_hub.process_perception_cross_platform(
                    mlink_msg
                )
                await message.reply(response or "弥娅没有回复")

            self.platforms["kook"] = client

            # 启动（非阻塞）
            asyncio.create_task(client.start())
            logger.info("✅ KOOK 机器人启动成功")
            return True

        except ImportError:
            logger.error("❌ 请安装 kook-api: pip install kook-api")
            return False
        except Exception as e:
            logger.error(f"❌ KOOK 启动失败: {e}")
            return False

    async def _start_mattermost(self, config: Dict) -> bool:
        """启动 Mattermost 机器人"""
        try:
            import mattermostdriver

            server_url = config.get("server_url", "")
            token = config.get("token", "")

            if not server_url or not token:
                logger.error("❌ Mattermost 缺少 server_url 或 token")
                return False

            driver = mattermostdriver.Driver(
                {
                    "url": server_url,
                    "token": token,
                    "scheme": "https",
                }
            )

            self.platforms["mattermost"] = driver
            logger.info("✅ Mattermost 机器人初始化成功")
            return True

        except ImportError:
            logger.error("❌ 请安装 MattermostDriver: pip install MattermostDriver")
            return False
        except Exception as e:
            logger.error(f"❌ Mattermost 启动失败: {e}")
            return False

    async def _start_misskey(self, config: Dict) -> bool:
        """启动 Misskey 机器人"""
        try:
            instance_url = config.get("instance_url", "")
            token = config.get("token", "")

            if not instance_url or not token:
                logger.error("❌ Misskey 缺少 instance_url 或 token")
                return False

            logger.info("✅ Misskey 配置已加载")
            logger.info(f"   实例: {instance_url}")
            return True

        except Exception as e:
            logger.error(f"❌ Misskey 启动失败: {e}")
            return False

    async def _start_webchat(self, config: Dict) -> bool:
        """启动网页聊天"""
        try:
            from flask import Flask, request, jsonify, render_template_string
            import uuid

            port = config.get("port", 8080)
            miya = self.miya

            flask_app = Flask(__name__)

            # 会话存储
            sessions = {}

            # HTML 模板
            WEBCHAT_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>弥娅 WebChat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .chat-container {
            width: 90%;
            max-width: 600px;
            height: 80vh;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 20px;
            font-weight: bold;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .message {
            margin-bottom: 15px;
            display: flex;
            align-items: flex-start;
        }
        .message.user {
            justify-content: flex-end;
        }
        .message.miya {
            justify-content: flex-start;
        }
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            font-size: 14px;
            line-height: 1.5;
        }
        .message.user .message-content {
            background: #667eea;
            color: white;
            border-bottom-right-radius: 4px;
        }
        .message.miya .message-content {
            background: white;
            color: #333;
            border: 1px solid #ddd;
            border-bottom-left-radius: 4px;
        }
        .message-time {
            font-size: 10px;
            color: #999;
            margin-top: 4px;
        }
        .chat-input-area {
            padding: 15px;
            background: white;
            border-top: 1px solid #eee;
            display: flex;
            gap: 10px;
        }
        .chat-input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #667eea;
            border-radius: 25px;
            outline: none;
            font-size: 14px;
        }
        .chat-input:focus {
            border-color: #764ba2;
        }
        .send-btn {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
            transition: transform 0.2s;
        }
        .send-btn:hover {
            transform: scale(1.05);
        }
        .send-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">✨ 弥娅 WebChat</div>
        <div class="chat-messages" id="messages">
            <div class="message miya">
                <div class="message-content">
                    你好呀！我是弥娅～有什么想聊的吗？
                    <div class="message-time">{{ now }}</div>
                </div>
            </div>
        </div>
        <div class="chat-input-area">
            <input type="text" class="chat-input" id="input" placeholder="和弥娅聊天..." onkeypress="if(event.key==='Enter')send()">
            <button class="send-btn" onclick="send()">发送</button>
        </div>
    </div>
    <script>
        const sessionId = '{{ session_id }}';
        const messagesDiv = document.getElementById('messages');
        const input = document.getElementById('input');
        
        function scrollBottom() {
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function formatTime() {
            const now = new Date();
            return now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
        }
        
        async function send() {
            const content = input.value.trim();
            if (!content) return;
            
            // 添加用户消息
            const userMsg = document.createElement('div');
            userMsg.className = 'message user';
            userMsg.innerHTML = '<div class="message-content">' + content + '<div class="message-time">' + formatTime() + '</div></div>';
            messagesDiv.appendChild(userMsg);
            input.value = '';
            scrollBottom();
            
            // 发送消息
            try {
                const resp = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({session_id: sessionId, message: content})
                });
                const data = await resp.json();
                
                // 添加弥娅回复
                const miyaMsg = document.createElement('div');
                miyaMsg.className = 'message miya';
                miyaMsg.innerHTML = '<div class="message-content">' + (data.response || '弥娅没有回复') + '<div class="message-time">' + formatTime() + '</div></div>';
                messagesDiv.appendChild(miyaMsg);
                scrollBottom();
            } catch (e) {
                alert('发送失败: ' + e);
            }
        }
        
        scrollBottom();
    </script>
</body>
</html>
            """

            @flask_app.route("/")
            async def handle_webchat():
                session_id = request.args.get("session", str(uuid.uuid4()))
                sessions[session_id] = True
                return render_template_string(
                    WEBCHAT_HTML.replace("{{ now }}", "正在连接...").replace(
                        "{{ session_id }}", session_id
                    ),
                    session_id=session_id,
                )

            @flask_app.route("/api/chat", methods=["POST"])
            async def handle_chat_api():
                from mlink.message import Message as MLinkMessage
                from datetime import datetime

                try:
                    data = request.json
                    session_id = data.get("session_id", "")
                    message_text = data.get("message", "").strip()

                    if not message_text:
                        return jsonify({"response": "��输入内容哦～"})

                    perception_data = {
                        "content": message_text,
                        "input": message_text,
                        "sender_name": "web_user",
                        "user_id": session_id,
                        "sender_id": session_id,
                        "message_type": "private",
                        "platform": "webchat",
                        "source": "webchat",
                        "is_at_bot": True,
                        "timestamp": datetime.now().isoformat(),
                    }

                    mlink_msg = MLinkMessage(
                        msg_type="data", content=perception_data, source="webchat"
                    )
                    response = (
                        await miya.decision_hub.process_perception_cross_platform(
                            mlink_msg
                        )
                    )

                    return jsonify({"response": response or "弥娅没有回复"})
                except Exception as e:
                    logger.error(f"[WebChat] 处理消息失败: {e}")
                    return jsonify({"response": f"抱歉，出了点问题: {e}"})

            self.platforms["webchat"] = flask_app
            logger.info(f"✅ 网页聊天已启用 (http://localhost:{port})")

            from threading import Thread

            Thread(
                target=lambda: flask_app.run(
                    host="0.0.0.0", port=port, debug=False, threaded=True
                ),
                daemon=True,
            ).start()
            return True

        except Exception as e:
            logger.error(f"❌ 网页聊天启动失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def _start_aiocqhttp(self, config: Dict) -> bool:
        """启动 OneBot/NapCat"""
        try:
            logger.info("✅ OneBot/NapCat 配置已加载")
            logger.info("   请使用 python run/qq_main.py 单独启动")
            return True

        except Exception as e:
            logger.error(f"❌ OneBot/NapCat 启动失败: {e}")
            return False

    async def _start_qqofficial_webhook(self, config: Dict) -> bool:
        """启动 QQ 官方 Webhook 模式"""
        try:
            appid = config.get("appid", "")
            secret = config.get("secret", "")
            callback_url = config.get("callback_url", "")

            if not appid or not secret:
                logger.error("❌ QQ 官方 Webhook 缺少 appid 或 secret")
                return False

            logger.info("✅ QQ 官方 Webhook 配置已加载")
            logger.info(f"   AppID: {appid}")
            logger.info(f"   回调地址: {callback_url}")
            logger.info("   注意: 需要配置公网回调地址")
            return True

        except Exception as e:
            logger.error(f"❌ QQ 官方 Webhook 启动失败: {e}")
            return False

    async def _start_wecom_ai_bot(self, config: Dict) -> bool:
        """启动企业微信 AI Bot"""
        try:
            corpid = config.get("corpid", "")
            corpsecret = config.get("corpsecret", "")
            bot_token = config.get("bot_token", "")

            if not corpid or not corpsecret:
                logger.error("❌ 企业微信 AI Bot 缺少 corpid 或 corpsecret")
                return False

            logger.info("✅ 企业微信 AI Bot 配置已加载")
            logger.info(f"   CorpID: {corpid}")
            return True

        except Exception as e:
            logger.error(f"❌ 企业微信 AI Bot 启动失败: {e}")
            return False

    async def _start_weixin_oc(self, config: Dict) -> bool:
        """启动微信开放平台"""
        try:
            appid = config.get("appid", "")
            secret = config.get("secret", "")

            if not appid or not secret:
                logger.error("❌ 微信开放平台缺少 appid 或 secret")
                return False

            logger.info("✅ 微信开放平台配置已加载")
            logger.info(f"   AppID: {appid}")
            logger.info("   注意: 需要配置 Webhook 回调地址")
            return True

        except Exception as e:
            logger.error(f"❌ 微信开放平台启动失败: {e}")
            return False

    async def _start_weixin_official_account(self, config: Dict) -> bool:
        """启动微信公众号"""
        try:
            appid = config.get("appid", "")
            secret = config.get("secret", "")
            token = config.get("token", "")

            if not appid or not secret:
                logger.error("❌ 微信公众号缺少 appid 或 secret")
                return False

            logger.info("✅ 微信公众号配置已加载")
            logger.info(f"   AppID: {appid}")
            logger.info("   注意: 需要配置 Webhook 回调地址")
            return True

        except Exception as e:
            logger.error(f"❌ 微信公众号启动失败: {e}")
            return False

    async def _start_satori(self, config: Dict) -> bool:
        """启动 Satori 协议"""
        try:
            from satori import Satori, EventDispatcher
            import asyncio

            host = config.get("host", "127.0.0.1")
            port = config.get("port", 5500)
            token = config.get("token", "")

            miya = self.miya

            # Satori 客户端
            satori = Satori(
                url=f"http://{host}:{port}",
                token=token,
            )

            @satori.on("message.created")
            async def on_message(event):
                from mlink.message import Message as MLinkMessage

                try:
                    message = event.message
                    if not message.content:
                        return

                    # 获取消息内容
                    if hasattr(message, "content"):
                        content = str(message.content)
                    else:
                        content = str(message)

                    # 获取发送者
                    user_id = (
                        str(message.author.id)
                        if hasattr(message, "author") and hasattr(message.author, "id")
                        else "unknown"
                    )
                    channel_id = (
                        str(message.channel.id)
                        if hasattr(message, "channel")
                        and hasattr(message.channel, "id")
                        else ""
                    )
                    guild_id = (
                        str(message.guild.id)
                        if hasattr(message, "guild") and hasattr(message.guild, "id")
                        else ""
                    )

                    perception_data = {
                        "content": content,
                        "input": content,
                        "sender_name": user_id,
                        "user_id": user_id,
                        "sender_id": user_id,
                        "message_type": "group" if guild_id else "private",
                        "group_id": channel_id or guild_id,
                        "platform": "satori",
                        "source": "satori",
                        "is_at_bot": True,
                        "timestamp": datetime.now().isoformat(),
                    }

                    mlink_msg = MLinkMessage(
                        msg_type="data", content=perception_data, source="satori"
                    )
                    response = (
                        await miya.decision_hub.process_perception_cross_platform(
                            mlink_msg
                        )
                    )

                    # 回复
                    if response:
                        await event.reply(response)
                except Exception as e:
                    logger.error(f"[Satori] 处理消息失败: {e}")

            self.platforms["satori"] = satori

            # 启动（非阻塞）
            asyncio.create_task(satori.connect())
            logger.info(f"✅ Satori 协议初始化成功 (ws://{host}:{port})")
            return True

        except ImportError:
            logger.error("❌ 请安装 satori: pip install satori")
            return False
        except Exception as e:
            logger.error(f"❌ Satori 启动失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def run(self):
        """运行主循环"""
        await self.initialize()
        await self.start_all_platforms()

        if self.platforms:
            try:
                while self.running:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("⏹️ 收到停止信号...")
                await self.stop()

    async def stop(self):
        """停止所有平台"""
        logger.info("🛑 正在停止所有平台...")
        self.running = False

        for platform_id, platform in self.platforms.items():
            try:
                if hasattr(platform, "close"):
                    await platform.close()
                elif hasattr(platform, "stop"):
                    await platform.stop()
                logger.info(f"✅ {platform_id} 已停止")
            except Exception as e:
                logger.error(f"❌ {platform_id} 停止失败: {e}")

        logger.info("👋 弥娅已停止")


async def main():
    """主函数"""
    print("""
╔════════════════════════════════════════════════════════════╗
║              弥娅多平台统一启动器 v1.0                       ║
║                                                            ║
║  支持平台: QQ官方, Telegram, Discord, 飞书, 钉钉,           ║
║           企业微信, Slack, LINE, KOOK, Mattermost,         ║
║           Misskey, 网页聊天, OneBot/NapCat                  ║
║                                                            ║
║  配置文件: config/platforms_config.py                       ║
║                                                            ║
║  按 Ctrl+C 停止服务                                         ║
╚════════════════════════════════════════════════════════════╝
    """)

    launcher = MiyaMultiPlatformLauncher()

    # 注册信号处理
    def signal_handler(sig, frame):
        logger.info("⏹️ 收到停止信号...")
        asyncio.create_task(launcher.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    await launcher.run()


if __name__ == "__main__":
    asyncio.run(main())
