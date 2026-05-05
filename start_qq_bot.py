"""
弥娅QQ官方机器人启动脚本

使用QQ频道机器人的Token连接QQ。
Token 从环境变量 QQ_BOT_TOKEN 读取（不硬编码）。
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("miya_qq.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def _load_token() -> str:
    token = os.getenv("QQ_BOT_TOKEN", "")
    if token:
        return token
    token = os.getenv("QQ_ONEBOT_TOKEN", "")
    if token:
        return token
    raise RuntimeError(
        "未设置 QQ_BOT_TOKEN 环境变量。\n"
        "请设置: set QQ_BOT_TOKEN=your_token_here  (Windows)\n"
        "     或: export QQ_BOT_TOKEN=your_token_here  (Linux/Mac)"
    )


async def start_qq_bot():
    """启动QQ机器人"""
    logger.info("=" * 50)
    logger.info("🚀 弥娅QQ机器人启动中...")
    logger.info("=" * 50)

    try:
        import botpy
        from botpy import BotAPI
        from botpy.types.message import Message

        TOKEN = _load_token()

        class MiyaBot(botpy.Client):
            """弥娅QQ机器人"""

            async def on_ready(self):
                logger.info(f"✅ 弥娅已上线！")
                logger.info(f"   机器人ID: {self.robot.id}")
                logger.info(f"   机器人名称: {self.robot.username}")

            async def on_at_message_create(self, message: Message):
                logger.info(
                    "📨 收到消息: 频道=%s 用户=%s 内容=%s",
                    message.guild_id,
                    message.author.username,
                    message.content,
                )
                try:
                    response = await self._process_message(message.content)
                    await message.reply(content=response)
                except Exception as e:
                    logger.error("处理消息失败: %s", e)
                    await message.reply(content="抱歉，我暂时无法处理这条消息...")

            async def on_group_at_message_create(self, message: Message):
                logger.info(
                    "📨 收到群消息: 群=%s 用户=%s 内容=%s",
                    message.group_openid,
                    message.author.member_openid,
                    message.content,
                )
                try:
                    response = await self._process_message(message.content)
                    await message._api.post_group_message(
                        group_openid=message.group_openid,
                        msg_type=0,
                        msg_id=message.id,
                        content=response,
                        msg_seq=1,
                    )
                except Exception as e:
                    logger.error("处理群消息失败: %s", e)

            async def on_direct_message_create(self, message: Message):
                logger.info(
                    "📨 收到私信: 用户=%s 内容=%s",
                    message.author.username,
                    message.content,
                )
                try:
                    response = await self._process_message(message.content)
                    await message.reply(content=response)
                except Exception as e:
                    logger.error("处理私信失败: %s", e)

            async def _process_message(self, content: str) -> str:
                """处理消息并生成回复

                TODO: 集成 DecisionHub 进行完整 AI 决策
                当前使用简易回显，后续替换为:
                    from hub.decision_hub import get_decision_hub
                    hub = get_decision_hub()
                    result = await hub.process(...)
                """
                return f"你好！我是弥娅，我收到了: {content}"

        intents = botpy.Intents(
            public_messages=True,
            public_guild_messages=True,
            direct_message=True,
        )
        bot = MiyaBot(intents=intents)

        logger.info("🔌 正在连接QQ服务器...")
        await bot.start(token=TOKEN)

    except RuntimeError as e:
        logger.error("❌ %s", e)
    except ImportError as e:
        logger.error("❌ 缺少依赖: %s", e)
        logger.info("请安装botpy: pip install botpy")
    except Exception as e:
        logger.error("❌ 启动失败: %s", e)
        import traceback

        traceback.print_exc()


async def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════╗
║           弥娅QQ官方机器人 v1.0                  ║
║                                                  ║
║  按 Ctrl+C 停止服务                              ║
╚══════════════════════════════════════════════════╝
    """)

    try:
        await start_qq_bot()
    except KeyboardInterrupt:
        logger.info("⏹️ 收到停止信号...")
    except Exception as e:
        logger.error("❌ 运行错误: %s", e)
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
