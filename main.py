"""
Miya System v6.0 - Entry Point

Usage:
    python main.py              # Start core system
    python main.py --port 6185  # Specify Dashboard port
    python main.py --help      # Help
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_env():
    """Check environment"""
    if sys.version_info.major == 3 and sys.version_info.minor >= 10:
        pass
    else:
        print("Please use Python 3.10+")
        sys.exit(1)

    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    for subdir in ["config", "plugins", "temp", "knowledge_base", "logs"]:
        (data_dir / subdir).mkdir(exist_ok=True)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Miya System v6.0")
    parser.add_argument("--webui-dir", type=str)
    parser.add_argument("--port", type=int)
    parser.add_argument("--host", type=str)
    args = parser.parse_args()

    check_env()

    if args.port:
        os.environ["MIYA_DASHBOARD_PORT"] = str(args.port)
    if args.host:
        os.environ["MIYA_DASHBOARD_HOST"] = args.host

    asyncio.run(_main_async(args.webui_dir))


async def _main_async(webui_dir):
    """Async main"""
    print("=" * 50)
    print("  Miya System v6.0")
    print("=" * 50)
    print()

    from core.miya_initial_loader import MiyaInitialLoader
    from core.log_broker import LogBroker, LogManager

    lb = LogBroker()
    LogManager.set_queue_handler(lb)

    loader = MiyaInitialLoader(lb)
    loader.webui_dir = webui_dir
    await loader.start()


if __name__ == "__main__":
    main()
