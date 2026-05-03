# -*- coding: utf-8 -*-
"""
弥娅 QQ 官方机器人 - 使用 botpy 连接 QQ 官方 API

功能与 napcat 版本完全一致：
- 人格系统（形态切换）
- 记忆系统（记忆锚点）
- 灵魂发生器（情绪分析）
- 协作引擎（多模型联动）
- 工具调用（69个工具）
"""

import sys
import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

# 设置标准输出编码为UTF-8
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入配置
from dotenv import load_dotenv

load_dotenv(project_root / "config" / ".env")

# 导入弥娅核心系统
from run.main import Miya
from config import Settings
from config.platforms_config import QQ_OFFICIAL_CONFIG

# 导入消息队列
from core.message_queue import (
    get_message_queue,
    MessageQueueManager,
)

logger = logging.getLogger("MiyaQQOfficial")


class MiyaQQOfficial:
    """弥娅 QQ 官方机器人"""

    def __init__(self):
        self.logger = self._setup_logger()
        self.settings = Settings()

        # 核心系统
        self.miya: Optional[Miya] = None

        # 消息队列
        self.message_queue = get_message_queue()

        # 从配置文件读取机器人配置
        self.app_id = QQ_OFFICIAL_CONFIG.get("appid", "")
        self.app_secret = QQ_OFFICIAL_CONFIG.get("secret", "")
        self.bot_qq = QQ_OFFICIAL_CONFIG.get("bot_qq", "")
        self.enable_group_c2c = QQ_OFFICIAL_CONFIG.get("enable_group_c2c", True)
        self.enable_guild_direct_message = QQ_OFFICIAL_CONFIG.get(
            "enable_guild_direct_message", True
        )
        self.sandbox = QQ_OFFICIAL_CONFIG.get("sandbox", False)

        # 超级管理员
        self.super_admin = os.getenv("QQ_SUPER_ADMIN", "1523878699")

    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger("MiyaQQOfficial")
        logger.setLevel(logging.DEBUG)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)

        # 文件处理器
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / "miya_qq_official.log", encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    async def initialize(self):
        """初始化弥娅系统"""
        self.logger.info("=" * 50)
        self.logger.info("弥娅 QQ 官方机器人初始化中...")
        self.logger.info("=" * 50)

        # 初始化弥娅核心系统（Miya的__init__会自动完成所有初始化）
        self.logger.info("初始化弥娅核心系统...")
        self.miya = Miya()

        self.logger.info("弥娅核心系统初始化完成")
        self.logger.info("=" * 50)

    async def process_message(
        self,
        user_id: str,
        user_name: str,
        content: str,
        message_type: str = "private",
        group_id: str = "",
        group_name: str = "",
        sender_role: str = "member",
    ) -> str:
        """处理消息并返回回复"""
        if not self.miya:
            return "弥娅系统未初始化"

        try:
            from mlink.message import Message

            # 构建感知数据
            perception_data = {
                "content": content,
                "input": content,
                "sender_name": user_name,
                "user_id": user_id,
                "sender_id": user_id,
                "message_type": message_type,
                "group_id": int(group_id) if group_id else 0,
                "group_name": group_name,
                "sender_role": sender_role,
                "platform": "qq_official",
                "source": "qq_official",
                "is_at_bot": True,  # 官方机器人只收到@消息
                "reply_to_bot": False,
                "timestamp": datetime.now().isoformat(),
            }

            # 创建 M-Link Message
            message = Message(
                msg_type="data",
                content=perception_data,
                source="qq_official",
            )

            # 调用弥娅处理
            response = await self.miya.decision_hub.process_perception_cross_platform(
                message
            )

            return response if response else "弥娅没有回复"

        except Exception as e:
            self.logger.error(f"处理消息失败: {e}")
            import traceback

            traceback.print_exc()
            return f"处理消息时出错: {str(e)}"


async def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════╗
║       弥娅 QQ 官方机器人 v1.0                    ║
║                                                  ║
║  使用 botpy 连接 QQ 官方 API                     ║
║  功能与 napcat 版本完全一致                      ║
║                                                  ║
║  按 Ctrl+C 停止服务                              ║
╚══════════════════════════════════════════════════╝
    """)

    # 创建弥娅QQ官方机器人
    miya_bot = MiyaQQOfficial()

    # 初始化弥娅系统
    await miya_bot.initialize()

    try:
        import botpy
        from botpy import logging as botpy_logging

        # 机器人的凭证
        APPID = miya_bot.app_id
        SECRET = miya_bot.app_secret

        # 创建自定义客户端
        class MiyaBotClient(botpy.Client):
            """弥娅QQ官方机器人客户端"""

            async def on_ready(self):
                """机器人就绪事件"""
                logger.info(f"✅ 弥娅已上线！")
                logger.info(f"   机器人ID: {self.robot.id}")
                logger.info(f"   机器人名称: 弥娅")

            async def on_at_message_create(self, message):
                """收到频道@消息"""
                user_id = message.author.id
                user_name = message.author.username
                content = message.content.strip()

                logger.info(f"📨 收到频道消息: {content}")

                # 调用弥娅处理
                response = await miya_bot.process_message(
                    user_id=user_id,
                    user_name=user_name,
                    content=content,
                    message_type="channel",
                )

                # 回复消息
                await message.reply(content=response)
                logger.info(f"📤 已回复")

            async def on_group_at_message_create(self, message):
                """收到群@消息"""
                user_id = message.author.member_openid
                user_name = message.author.member_openid
                content = message.content.strip()

                logger.info(f"📨 收到群消息: {content}")

                # 调用弥娅处理
                response = await miya_bot.process_message(
                    user_id=user_id,
                    user_name=user_name,
                    content=content,
                    message_type="group",
                    group_id=message.group_openid,
                )

                # 回复消息
                await message._api.post_group_message(
                    group_openid=message.group_openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=response,
                    msg_seq=1,
                )
                logger.info(f"📤 已回复")

            async def on_direct_message_create(self, message):
                """收到私信"""
                user_id = message.author.id
                user_name = message.author.username
                content = message.content.strip()

                logger.info(f"📨 收到私信: {content}")

                # 调用弥娅处理
                response = await miya_bot.process_message(
                    user_id=user_id,
                    user_name=user_name,
                    content=content,
                    message_type="private",
                )

                # 回复消息
                await message.reply(content=response)
                logger.info(f"📤 已回复")

            async def on_c2c_message_create(self, message):
                """收到C2C消息"""
                user_id = message.author.user_openid
                user_name = message.author.user_openid
                content = message.content.strip()

                logger.info(f"📨 收到C2C消息: {content}")

                # 调用弥娅处理
                response = await miya_bot.process_message(
                    user_id=user_id,
                    user_name=user_name,
                    content=content,
                    message_type="c2c",
                )

                # 回复消息
                await message._api.post_c2c_message(
                    openid=message.author.user_openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=response,
                    msg_seq=1,
                )
                logger.info(f"📤 已回复")

        # 创建机器人实例
        intents = botpy.Intents(
            public_messages=True,
            public_guild_messages=True,
            direct_message=True,
        )

        bot = MiyaBotClient(intents=intents)

        logger.info("🔌 正在连接QQ服务器...")
        logger.info(f"   AppID: {APPID}")

        # 启动机器人
        await bot.start(appid=APPID, secret=SECRET)

    except ImportError as e:
        logger.error(f"❌ 缺少依赖: {e}")
        logger.info("请安装botpy: pip install qq-botpy")
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
