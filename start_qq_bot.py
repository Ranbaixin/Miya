"""
弥娅QQ官方机器人启动脚本

使用QQ频道机器人的Token连接QQ。
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("miya_qq.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def start_qq_bot():
    """启动QQ机器人"""
    logger.info("=" * 50)
    logger.info("🚀 弥娅QQ机器人启动中...")
    logger.info("=" * 50)

    try:
        # 尝试使用botpy
        import botpy
        from botpy import BotAPI
        from botpy.types.message import Message
        from botpy import logging as botpy_logging

        # 配置botpy日志 (兼容新版botpy)
        try:
            botpy_logging.set_log_level(logging.INFO)
        except AttributeError:
            pass  # 新版botpy可能没有这个方法

        # 机器人的Token
        TOKEN = "bot:v1_r7-SE5Jw0_psK4fBVE5wPgrPFAMGLtdmiuOZCyodG70nckXBD6L_axRiFVnCjH4dRYve0xk-Cdmow94sJFz_MDUWRmwo580niZddR-phPKA"

        # 创建自定义客户端
        class MiyaBot(botpy.Client):
            """弥娅QQ机器人"""

            async def on_ready(self):
                """机器人就绪事件"""
                logger.info(f"✅ 弥娅已上线！")
                logger.info(f"   机器人ID: {self.robot.id}")
                logger.info(f"   机器人名称: {self.robot.username}")

            async def on_at_message_create(self, message: Message):
                """收到@消息"""
                logger.info(f"📨 收到消息:")
                logger.info(f"   频道: {message.guild_id}")
                logger.info(f"   用户: {message.author.username}")
                logger.info(f"   内容: {message.content}")

                # 回复消息
                await message.reply(
                    content=f"你好！我是弥娅，我收到了: {message.content}"
                )
                logger.info(f"📤 已回复")

            async def on_group_at_message_create(self, message: Message):
                """收到群@消息"""
                logger.info(f"📨 收到群消息:")
                logger.info(f"   群: {message.group_openid}")
                logger.info(f"   用户: {message.author.member_openid}")
                logger.info(f"   内容: {message.content}")

                # 回复消息
                await message._api.post_group_message(
                    group_openid=message.group_openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=f"你好！我是弥娅，我收到了: {message.content}",
                    msg_seq=1,
                )
                logger.info(f"📤 已回复")

            async def on_direct_message_create(self, message: Message):
                """收到私信"""
                logger.info(f"📨 收到私信:")
                logger.info(f"   用户: {message.author.username}")
                logger.info(f"   内容: {message.content}")

                # 回复消息
                await message.reply(
                    content=f"你好！我是弥娅，我收到了: {message.content}"
                )
                logger.info(f"📤 已回复")

        # 创建机器人实例
        intents = botpy.Intents(
            public_messages=True,
            public_guild_messages=True,
            direct_message=True,
        )

        bot = MiyaBot(intents=intents)

        logger.info("🔌 正在连接QQ服务器...")

        # 启动机器人
        await bot.start(token=TOKEN)

    except ImportError as e:
        logger.error(f"❌ 缺少依赖: {e}")
        logger.info("请安装botpy: pip install botpy")
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
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
        logger.error(f"❌ 运行错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
