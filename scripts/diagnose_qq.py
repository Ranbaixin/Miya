"""
QQ机器人诊断脚本
用于诊断QQ机器人连接问题和API支持情况
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


async def diagnose_qq_connection():
    """诊断QQ连接"""
    print("=" * 60)
    print("           QQ机器人连接诊断")
    print("=" * 60)
    
    try:
        # 1. 检查配置文件
        print("\n1. 检查配置文件...")
        env_path = project_root / "config" / ".env"
        if not env_path.exists():
            print(f"   ❌ 配置文件不存在: {env_path}")
            print("   💡 请复制 config/.env.example 为 config/.env 并配置")
            return False
        else:
            print(f"   ✅ 配置文件存在: {env_path}")
            
            # 读取QQ配置
            from dotenv import load_dotenv
            load_dotenv(env_path)
            
            onebot_url = os.getenv('QQ_ONEBOT_WS_URL', 'ws://localhost:3001')
            bot_qq = os.getenv('QQ_BOT_QQ', '0')
            superadmin = os.getenv('QQ_SUPERADMIN_QQ', '0')
            
            print(f"   OneBot URL: {onebot_url}")
            print(f"   机器人QQ: {bot_qq}")
            print(f"   超级管理员: {superadmin}")
            
            if onebot_url == 'ws://localhost:3001' and bot_qq == '0':
                print("   ⚠️  配置为默认值，请确保已正确配置")
        
        # 2. 检查OneBot客户端
        print("\n2. 检查OneBot客户端...")
        try:
            from webnet.qq.client import QQOneBotClient
            print("   ✅ OneBot客户端模块导入成功")
            
            # 创建客户端（但不连接）
            QQOneBotClient(
                ws_url=onebot_url,
                bot_qq=int(bot_qq) if bot_qq != '0' else 0,
                access_token=None
            )
            print("   ✅ OneBot客户端创建成功")
            
        except ImportError as e:
            print(f"   ❌ 导入OneBot客户端失败: {e}")
            return False
        except Exception as e:
            print(f"   ❌ 创建OneBot客户端失败: {e}")
            return False
        
        # 3. 检查网络连接
        print("\n3. 检查网络连接...")
        try:
            import socket
            import urllib.parse
            
            # 解析WebSocket URL
            parsed = urllib.parse.urlparse(onebot_url)
            host = parsed.hostname or 'localhost'
            port = parsed.port or (443 if parsed.scheme == 'wss' else 80)
            
            # 尝试TCP连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            try:
                result = sock.connect_ex((host, port))
                if result == 0:
                    print(f"   ✅ 网络连接正常: {host}:{port}")
                else:
                    print(f"   ❌ 网络连接失败: {host}:{port} (错误码: {result})")
                    print(f"   💡 请检查OneBot服务是否运行在 {onebot_url}")
                    return False
            finally:
                sock.close()
                
        except Exception as e:
            print(f"   ❌ 网络检查失败: {e}")
        
        # 4. 检查API兼容性
        print("\n4. 检查API兼容性...")
        print("   ⏳ 需要实际连接OneBot服务进行测试...")
        print("   💡 运行以下命令测试实际连接:")
        print(f"   python -m webnet.qq.test_connection --url {onebot_url}")
        
        # 5. 提供解决方案
        print("\n5. 常见问题解决方案:")
        print("   a) 点赞失败 (retcode=1200):")
        print("      - 检查OneBot实现是否支持 send_like API")
        print("      - 某些OneBot实现（如go-cqhttp）需要特殊配置")
        print("      - 尝试更新OneBot到最新版本")
        
        print("\n   b) 连接失败:")
        print("      - 确保OneBot服务正在运行")
        print("      - 检查防火墙设置")
        print("      - 验证WebSocket URL是否正确")
        
        print("\n   c) 权限问题:")
        print("      - 检查机器人QQ号是否正确配置")
        print("      - 确保机器人已登录")
        print("      - 验证超级管理员QQ号是否正确")
        
        # 6. 测试脚本
        print("\n6. 快速测试脚本:")
        print("""
    async def test_connection():
        import asyncio
        from webnet.qq.client import QQOneBotClient
        
        client = QQOneBotClient(
            ws_url='{}',
            bot_qq={},
            access_token=None
        )
        
        try:
            # 连接测试
            await client.connect()
            print("✅ WebSocket连接成功")
            
            # 简单消息测试
            await client.send_private_msg(
                user_id={},
                message="弥娅连接测试"
            )
            print("✅ 私聊消息发送成功")
            
            # 点赞测试
            try:
                await client.send_like({}, 1)
                print("✅ 点赞功能正常")
            except Exception as e:
                print(f"⚠️  点赞功能异常: {{e}}")
                
        except Exception as e:
            print(f"❌ 连接测试失败: {{e}}")
        finally:
            await client.disconnect()
    
    asyncio.run(test_connection())
        """.format(onebot_url, bot_qq, superadmin if superadmin != '0' else bot_qq, superadmin if superadmin != '0' else bot_qq))
        
        print("\n" + "=" * 60)
        print("诊断完成！请根据上述建议解决问题")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 诊断过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_onebot_apis():
    """测试OneBot API支持"""
    print("\n" + "=" * 60)
    print("           OneBot API支持测试")
    print("=" * 60)
    
    try:
        from dotenv import load_dotenv
        load_dotenv(project_root / "config" / ".env")
        
        onebot_url = os.getenv('QQ_ONEBOT_WS_URL', 'ws://localhost:3001')
        bot_qq = os.getenv('QQ_BOT_QQ', '0')
        
        from webnet.qq.client import QQOneBotClient
        
        print(f"连接OneBot: {onebot_url}")
        
        client = QQOneBotClient(
            ws_url=onebot_url,
            bot_qq=int(bot_qq) if bot_qq != '0' else 0,
            access_token=None
        )
        
        try:
            await client.connect()
            print("✅ WebSocket连接成功")
            
            # 测试API列表
            apis_to_test = [
                ("send_private_msg", "发送私聊消息"),
                ("send_group_msg", "发送群消息"),
                ("send_like", "发送点赞"),
                ("send_poke", "发送戳一戳"),
                ("get_friend_list", "获取好友列表"),
            ]
            
            test_user = int(bot_qq) if bot_qq != '0' else 1523878699
            
            for api_name, description in apis_to_test:
                print(f"\n测试 {api_name} ({description})...")
                
                try:
                    if api_name == "send_private_msg":
                        result = await client.send_private_msg(test_user, "API测试消息")
                        print(f"  ✅ {description}成功")
                        
                    elif api_name == "send_like":
                        result = await client.send_like(test_user, 1)
                        print(f"  ✅ {description}成功")
                        
                    elif api_name == "send_poke":
                        result = await client.send_poke(test_user)
                        print(f"  ✅ {description}成功")
                        
                    elif api_name == "get_friend_list":
                        result = await client._call_api("get_friend_list", {})
                        friend_count = len(result.get("data", []))
                        print(f"  ✅ {description}成功，好友数: {friend_count}")
                        
                    else:
                        print(f"  ⚠️  跳过 {api_name}（测试未实现）")
                        
                except Exception as e:
                    error_msg = str(e)
                    if "retcode=1200" in error_msg:
                        print(f"  ❌ {description}失败: 网络连接异常 (retcode=1200)")
                        print("     💡 此API可能不受支持或需要特殊权限")
                    elif "不支持" in error_msg or "未实现" in error_msg:
                        print(f"  ❌ {description}失败: API未实现")
                    else:
                        print(f"  ❌ {description}失败: {error_msg}")
            
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            
        finally:
            await client.disconnect()
            print("\n✅ 连接已关闭")
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("弥娅 QQ机器人诊断工具")
    print("版本: 1.0.0")
    print()
    
    # 检查Python版本
    
    # 运行诊断
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # 基本诊断
        success = loop.run_until_complete(diagnose_qq_connection())
        
        if success:
            # 询问是否进行API测试
            print("\n是否进行OneBot API支持测试？ (y/n)")
            choice = input().strip().lower()
            
            if choice == 'y':
                loop.run_until_complete(test_onebot_apis())
        
        print("\n诊断工具运行完成！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断，退出诊断工具")
    except Exception as e:
        print(f"\n❌ 诊断工具运行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        loop.close()


if __name__ == "__main__":
    main()
