# -*- coding: utf-8 -*-
"""
弥娅多平台启动脚本

启动所有配置的平台，让弥娅可以在多个平台上同时运行。

使用方法:
  python start_platforms.py          # 启动所有启用的平台
  python start_platforms.py --list   # 列出所有可用平台
  python start_platforms.py --guide  # 显示平台申请指南

配置文件: config/platforms_config.py
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def show_platform_list():
    """显示所有可用平台"""
    from config.platforms_config import list_all_platforms, get_enabled_platforms

    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║              弥娅支持的平台列表                            ║")
    print("╚════════════════════════════════════════════════════════════╝")

    platforms = list_all_platforms()
    enabled = get_enabled_platforms()

    print("\n📱 平台状态:")
    print("-" * 60)

    for p in platforms:
        status_icon = "✅" if p["enabled"] else "❌"
        print(f"  {status_icon} {p['id']:<25} {'已启用' if p['enabled'] else '未启用'}")

    print("-" * 60)
    print(f"\n🎯 当前启用: {len(enabled)} 个平台")

    if enabled:
        print("   启用的平台:")
        for pid in enabled:
            print(f"   ✓ {pid}")

    print()


def show_platform_guide():
    """显示平台申请指南"""
    from config.platforms_config import get_platform_guide

    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║              弥娅平台申请指南                               ║")
    print("╚════════════════════════════════════════════════════════════╝")

    guide = get_platform_guide()

    for platform_id, info in guide.items():
        print(f"\n📌 {info['name']}")
        print(f"   申请地址: {info['url']}")
        print(f"   需要凭证: {', '.join(info['credentials'])}")
        print(f"   文档: {info['docs']}")

    print("\n💡 配置方法:")
    print("   1. 访问对应平台申请机器人凭证")
    print("   2. 编辑 config/platforms_config.py")
    print("   3. 将 enabled 设为 True")
    print("   4. 填入凭证信息")
    print("   5. 运行 python start_platforms.py 启动")
    print()


def main():
    """主函数"""
    # 检查参数
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()

        if arg in ["--list", "-l", "list"]:
            show_platform_list()
            return
        elif arg in ["--guide", "-g", "guide", "help", "--help", "-h"]:
            show_platform_guide()
            return

    # 启动多平台
    from core.multi_platform_launcher import main as launcher_main

    asyncio.run(launcher_main())


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║              弥娅多平台服务 v2.0                            ║
║                                                            ║
║  支持平台: QQ官方, Telegram, Discord, 飞书, 钉钉,           ║
║           企业微信, Slack, LINE, KOOK, Mattermost,         ║
║           Misskey, 网页聊天, OneBot/NapCat                  ║
║                                                            ║
║  使用方法:                                                  ║
║    python start_platforms.py          # 启动所有平台        ║
║    python start_platforms.py --list   # 列出所有平台        ║
║    python start_platforms.py --guide  # 申请指南            ║
║                                                            ║
║  配置文件: config/platforms_config.py                       ║
║                                                            ║
║  按 Ctrl+C 停止服务                                         ║
╚════════════════════════════════════════════════════════════╝
    """)

    main()
