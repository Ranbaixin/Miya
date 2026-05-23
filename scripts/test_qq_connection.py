"""
QQ连接测试脚本
快速测试QQ机器人连接状态
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_connection():
    """测试连接"""
    print("=" * 50)
    print("      QQ机器人连接测试")
    print("=" * 50)
    
    try:
        # 加载配置
        from dotenv import load_dotenv
        env_path = project_root / "config" / ".env"
        
        if not env_path.exists():
            print("❌ 配置文件不存在，请先配置 config/.env")
            return False
        
        load_dotenv(env_path)
        
        onebot_url = os.getenv('QQ_ONEBOT_WS_URL', 'ws://localhost:3001')
        bot_qq = os.getenv('QQ_BOT_QQ', '0')
        superadmin = os.getenv('QQ_SUPERADMIN_QQ', '1523878699')
        
        print(f"OneBot URL: {onebot_url}")
        print(f"机器人QQ: {bot_qq}")
        print(f"超级管理员: {superadmin}")
        print()
        
        # 导入客户端
        try:
            from webnet.qq.client import QQOneBotClient
        except ImportError as e:
            print(f"❌ 导入失败: {e}")
            print("💡 请确保在项目根目录运行此脚本")
            return False
        
        # 创建客户端
        client = QQOneBotClient(
            ws_url=onebot_url,
            bot_qq=int(bot_qq) if bot_qq != '0' else 3681817929,
            access_token=None
        )
        
        print("正在连接OneBot服务...")
        
        try:
            # 连接
            await client.connect(timeout=10)
            print("✅ WebSocket连接成功")
            
            # 等待连接就绪
            await asyncio.sleep(2)
            
            # 测试私聊消息
            test_user = int(superadmin) if superadmin != '0' else 1523878699
            print(f"\n测试私聊消息到 QQ{test_user}...")
            
            try:
                await client.send_private_msg(
                    user_id=test_user,
                    message="🧪 弥娅连接测试消息"
                )
                print("✅ 私聊消息发送成功")
            except Exception as e:
                print(f"❌ 私聊消息发送失败: {e}")
            
            # 测试点赞功能
            print(f"\n测试点赞功能到 QQ{test_user}...")
            
            try:
                await client.send_like(test_user, 1)
                print("✅ 点赞功能正常")
            except Exception as e:
                error_msg = str(e)
                if "retcode=1200" in error_msg:
                    print("❌ 点赞失败: 网络连接异常 (retcode=1200)")
                    print("💡 可能原因:")
                    print("   1. OneBot实现不支持 send_like API")
                    print("   2. 网络连接问题")
                    print("   3. 权限不足")
                elif "不支持" in error_msg or "未实现" in error_msg:
                    print("❌ 点赞失败: API未实现")
                    print("💡 此OneBot版本不支持点赞功能")
                else:
                    print(f"❌ 点赞失败: {error_msg}")
            
            # 测试戳一戳
            print(f"\n测试戳一戳功能到 QQ{test_user}...")
            
            try:
                await client.send_poke(test_user)
                print("✅ 戳一戳功能正常")
            except Exception as e:
                error_msg = str(e)
                if "retcode=1200" in error_msg:
                    print("❌ 戳一戳失败: 网络连接异常")
                elif "不支持" in error_msg:
                    print("❌ 戳一戳失败: API未实现")
                else:
                    print(f"❌ 戳一戳失败: {error_msg}")
            
            print("\n" + "=" * 50)
            print("连接测试完成！")
            print("=" * 50)
            
            return True
            
        except asyncio.TimeoutError:
            print("❌ 连接超时")
            print("💡 请检查:")
            print(f"   1. OneBot服务是否运行在 {onebot_url}")
            print("   2. 防火墙是否阻止连接")
            print("   3. 网络是否正常")
            return False
            
        except ConnectionRefusedError:
            print("❌ 连接被拒绝")
            print(f"💡 OneBot服务未在 {onebot_url} 运行")
            return False
            
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
            
        finally:
            # 清理
            try:
                await client.disconnect()
                print("\n连接已关闭")
            except:
                pass
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 运行测试
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        success = loop.run_until_complete(test_connection())
        
        if not success:
            print("\n⚠️  测试失败，请检查:")
            print("   1. 确保OneBot服务正在运行")
            print("   2. 检查 config/.env 配置")
            print("   3. 验证网络连接")
            print("\n常见OneBot实现:")
            print("   - go-cqhttp: https://docs.go-cqhttp.org/")
            print("   - OneBot 11: https://11.onebot.dev/")
            print("   - LLOneBot: https://github.com/llonebot/llonebot")
            
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
