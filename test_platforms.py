import asyncio
import sys
sys.path.insert(0, '.')

from core.platform_extended import PlatformRegistry, PlatformType
from core.platform_adapters import (
    QQOfficialAdapter, OneBotAdapter, FeishuAdapter,
    DingTalkAdapter, TelegramAdapter, DiscordAdapter
)

async def test_adapter(adapter_cls, platform_type, config):
    try:
        adapter = adapter_cls(config)
        if hasattr(adapter, 'initialize'):
            ok = await adapter.initialize(config)
            if not ok:
                print(f"  {platform_type.value}: initialize failed")
                return False
        if hasattr(adapter, 'connect'):
            ok = await adapter.connect()
            if not ok:
                print(f"  {platform_type.value}: connect failed")
                return False
        print(f"  {platform_type.value}: OK")
        return True
    except Exception as e:
        print(f"  {platform_type.value}: ERROR - {e}")
        return False

async def main():
    print("Testing platform adapters...")
    # Dummy configs
    configs = {
        PlatformType.QQ_OFFICIAL: {"app_id": "test", "token": "test", "secret": "test"},
        PlatformType.ONEBOT: {"host": "127.0.0.1", "port": 6700, "access_token": ""},
        PlatformType.FEISHU: {"app_id": "test", "app_secret": "test"},
        PlatformType.DINGDING: {"app_key": "test", "app_secret": "test"},
        PlatformType.TELEGRAM: {"bot_token": "test:test"},
        PlatformType.DISCORD: {"bot_token": "test.test.test", "guild_id": "123"},
    }
    adapter_map = {
        PlatformType.QQ_OFFICIAL: QQOfficialAdapter,
        PlatformType.ONEBOT: OneBotAdapter,
        PlatformType.FEISHU: FeishuAdapter,
        PlatformType.DINGDING: DingTalkAdapter,
        PlatformType.TELEGRAM: TelegramAdapter,
        PlatformType.DISCORD: DiscordAdapter,
    }
    results = []
    for ptype, adapter_cls in adapter_map.items():
        config = configs.get(ptype, {})
        ok = await test_adapter(adapter_cls, ptype, config)
        results.append((ptype.value, ok))
    print("\nSummary:")
    for name, ok in results:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
    if all(ok for _, ok in results):
        print("\nAll adapters tested successfully!")
    else:
        print("\nSome adapters failed.")

if __name__ == "__main__":
    asyncio.run(main())
