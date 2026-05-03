"""
弥娅系统 v6.0 - 统一入口

使用方法:
    python run/miya_main.py          # 终端模式
    python run/miya_main.py --qq       # QQ 模式
    python run/miya_main.py --web      # Web 模式
    python run/miya_main.py --help    # 查看帮助
"""

import sys
import asyncio
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(name)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )


async def main_async(mode: str = "terminal", webui_dir: str = None):
    """异步主函数"""
    from core.miya_lifecycle import MiyaCoreLifecycle, get_miya_lifecycle

    lifecycle = get_miya_lifecycle()
    success = await lifecycle.initialize()

    if not success:
        print("[ERROR] 系统初始化失败")
        return 1

    print("\n" + "=" * 60)
    print("  弥娅系统 v6.0 - Unified Edition")
    print("=" * 60)

    status = lifecycle.get_status()
    print("\n【系统状态】")
    print(f"  版本: v{status['version']}")
    print(f"  数据库: {'已启用' if status['database'] else '使用内置'}")
    print(f"  平台: {'已启用' if status['platforms'] else '使用内置'} (18 平台)")
    print(
        f"  AI 提供商: {'已启用' if status['providers'] else '使用内置'} (35+ 提供商)"
    )
    print(f"  知识库: {'已启用' if status['knowledge'] else '未启用'}")
    print(f"  插件: {'已启用' if status['plugins'] else '未启用'}")
    print(f"  流水线: {'已启用' if status['pipeline'] else '未启用'}")
    print(f"  Miya 核心: {'已启用' if status['miya_core'] else '未启用'}")

    await lifecycle.start()

    print("\n" + "=" * 60)
    print("  弥娅系统 v6.0 已启动!")
    print("=" * 60)

    if mode == "terminal":
        print("\n输入消息开始对话，输入 exit 退出\n")
        while True:
            try:
                user_input = input("你: ")
                if user_input.lower() in ["exit", "quit", "退出"]:
                    break
                if user_input.strip():
                    print("弥娅: [系统处理中...]")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"错误: {e}")

    await lifecycle.stop()
    print("\n弥娅系统已退出")
    return 0


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="弥娅系统 v6.0")
    parser.add_argument("--mode", type=str, default="terminal", help="运行模式")
    parser.add_argument("--qq", action="store_true", help="QQ 模式")
    parser.add_argument("--web", action="store_true", help="Web 模式")
    parser.add_argument("--webui-dir", type=str, help="WebUI 目录")
    args = parser.parse_args()

    mode = "terminal"
    if args.qq:
        mode = "qq"
    elif args.web:
        mode = "web"

    setup_logging()
    return asyncio.run(main_async(mode, args.webui_dir))


if __name__ == "__main__":
    sys.exit(main())
