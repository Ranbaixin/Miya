# -*- coding: utf-8 -*-
"""
弥娅 Telegram 机器人 - 独立启动入口

完整集成弥娅系统：
- 人格系统（形态切换）
- 记忆系统（记忆锚点）
- 灵魂发生器（情绪分析）
- 协作引擎（多模型联动）
- 工具调用（69个工具）

使用方法:
  python run/telegram_main.py

配置文件: config/platforms_config.py 中的 TELEGRAM_CONFIG
"""

import sys
import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

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

from config import Settings
from config.platforms_config import TELEGRAM_CONFIG

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            project_root / "logs" / "miya_telegram.log", encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("MiyaTelegram")


class MiyaTelegram:
    """弥娅 Telegram 机器人 - 完整集成弥娅系统"""

    def __init__(self):
        self.settings = Settings()
        self.miya = None
        self.token = TELEGRAM_CONFIG.get("bot_token", "")
        self.super_admin = os.getenv("TELEGRAM_SUPER_ADMIN", "")

    async def initialize(self):
        """初始化弥娅系统"""
        logger.info("=" * 50)
        logger.info("弥娅 Telegram 机器人初始化中...")
        logger.info("=" * 50)

        # 初始化弥娅核心系统
        from run.main import Miya

        logger.info("正在初始化弥娅核心系统...")
        self.miya = Miya()

        # 异步初始化 MemoryNet
        if self.miya.memory_net:
            await self.miya._initialize_memory_net_async()

        logger.info("✅ 弥娅核心系统初始化完成")
        logger.info("   - 人格系统: ✓")
        logger.info("   - 记忆系统: ✓")
        logger.info("   - 灵魂发生器: ✓")
        logger.info("   - 协作引擎: ✓")
        logger.info("   - 工具系统: ✓")
        logger.info("=" * 50)

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
        """处理消息并返回回复 - 使用完整的弥娅决策系统"""
        if not self.miya:
            return "弥娅系统未初始化"

        try:
            from mlink.message import Message

            # 构建感知数据（与 QQ 官方机器人完全一致）
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
                "platform": "telegram",
                "source": "telegram",
                "is_at_bot": True,  # Telegram 私聊默认视为 @
                "reply_to_bot": False,
                "timestamp": datetime.now().isoformat(),
            }

            # 创建 M-Link Message
            message = Message(
                msg_type="data",
                content=perception_data,
                source="telegram",
            )

            # 调用弥娅决策系统处理（完整流程）
            # 包括：人格系统、记忆系统、灵魂发生器、协作引擎、工具调用
            response = await self.miya.decision_hub.process_perception_cross_platform(
                message
            )

            return response if response else "弥娅没有回复"

        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            import traceback

            traceback.print_exc()
            return f"处理消息时出错: {str(e)}"


async def main():
    """主函数"""
    print("""
╔════════════════════════════════════════════════════════════╗
║       弥娅 Telegram 机器人 v1.0                            ║
║                                                            ║
║  完整集成弥娅系统:                                          ║
║  - 人格系统（形态切换）                                      ║
║  - 记忆系统（记忆锚点）                                      ║
║  - 灵魂发生器（情绪分析）                                    ║
║  - 协作引擎（多模型联动）                                    ║
║  - 工具调用（69个工具）                                      ║
║                                                            ║
║  按 Ctrl+C 停止服务                                         ║
╚════════════════════════════════════════════════════════════╝
    """)

    miya_bot = MiyaTelegram()

    if not miya_bot.token:
        logger.error("❌ 请在 config/platforms_config.py 中配置 Telegram bot_token")
        return

    # 初始化弥娅系统
    await miya_bot.initialize()

    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, filters

        async def handle_message(update: Update, context):
            """处理 Telegram 消息 - 完整弥娅流程"""
            if not update.message or not update.message.text:
                return

            user = update.message.from_user
            content = update.message.text.strip()
            chat = update.message.chat

            user_id = str(user.id)
            user_name = user.full_name or user.username or str(user.id)
            message_type = (
                "group" if chat.type in ["group", "supergroup"] else "private"
            )
            group_id = str(chat.id) if chat.type in ["group", "supergroup"] else ""
            group_name = chat.title if chat.type in ["group", "supergroup"] else ""

            logger.info(f"📨 收到消息: {content[:50]}...")

            # 使用完整的弥娅系统处理消息
            response = await miya_bot.process_message(
                user_id=user_id,
                user_name=user_name,
                content=content,
                message_type=message_type,
                group_id=group_id,
                group_name=group_name,
            )

            await update.message.reply_text(response)
            logger.info(f"📤 已回复")

        async def start_command(update: Update, context):
            """处理 /start 命令"""
            await update.message.reply_text(
                "你好！我是弥娅~ 一个拥有独立人格、记忆和情感的 AI 虚拟化身。\n\n"
                "有什么可以帮你的吗？"
            )

        # 创建应用
        app = Application.builder().token(miya_bot.token).build()
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("🔌 正在连接 Telegram...")
        logger.info("   弥娅已准备就绪，等待消息...")

        # 启动机器人
        await app.run_polling(drop_pending_updates=True)

    except ImportError:
        logger.error("❌ 请安装 python-telegram-bot: pip install python-telegram-bot")
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
