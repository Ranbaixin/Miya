import asyncio
import sys
import logging
sys.path.insert(0, '.')

# Disable excessive logging
logging.basicConfig(level=logging.WARNING)

from core.platform_extended import get_platform_registry
from core.platforms_config import get_default_platforms

async def test_platform_connectivity():
    """Test connectivity to all configured platforms"""
    print("=== MIYA Platform Connectivity Test ===")
    print()
    
    # Get platform registry and default configurations
    registry = get_platform_registry()
    default_configs = get_default_platforms()
    
    # Test results
    results = []
    
    for platform_type, adapter_class in registry._adapters.items():
        config = default_configs.get(platform_type.value, {})
        # Ensure the platform is enabled for testing
        if not config.get("enabled", True):
            results.append((platform_type.value, "SKIPPED (disabled)", False))
            continue
            
        # Create adapter instance with test config
        try:
            # For testing, we'll use minimal configs - in reality these would need real credentials
            test_config = config.copy()
            
            # Add dummy credentials where needed for initialization
            if platform_type.value in ["feishu", "dingtalk"]:
                test_config.update({
                    "app_id": "test_app_id",
                    "app_secret": "test_app_secret"
                })
            elif platform_type.value == "discord":
                test_config.update({
                    "bot_token": "test_token.test_test"
                })
            elif platform_type.value == "telegram":
                test_config.update({
                    "bot_token": "123456:TEST_TOKEN"
                })
            elif platform_type.value == "slack":
                test_config.update({
                    "bot_token": "xoxb-test-token"
                })
            elif platform_type.value == "line":
                test_config.update({
                    "channel_access_token": "test_token"
                })
            elif platform_type.value == "wechat_work":
                test_config.update({
                    "corp_id": "test_corp",
                    "corp_secret": "test_secret",
                    "agent_id": "test_agent"
                })
            # QQ and Telegram adapters in platform_extended don't need special config beyond enabled
            
            # Initialize adapter
            adapter = adapter_class(test_config)
            
            # Try to initialize if the method exists
            if hasattr(adapter, 'initialize'):
                init_result = await adapter.initialize(test_config)
                if not init_result:
                    results.append((platform_type.value, "INIT_FAILED", False))
                    continue
                    
            # Try to connect if the method exists
            if hasattr(adapter, 'connect'):
                connect_result = await adapter.connect()
                if connect_result:
                    results.append((platform_type.value, "CONNECTED", True))
                else:
                    results.append((platform_type.value, "CONNECT_FAILED", False))
            else:
                # If no connect method, assume initialized means ready
                results.append((platform_type.value, "INITIALIZED", True))
                
        except Exception as e:
            results.append((platform_type.value, f"ERROR: {str(e)[:50]}", False))
    
    # Print results
    print(f"{'Platform':<15} {'Status':<20} {'Result'}")
    print("-" * 50)
    for platform, status, success in results:
        if success:
            result_symbol = "[PASS]"
        elif "SKIPPED" in status:
            result_symbol = "[SKIP]"
        else:
            result_symbol = "[FAIL]"
        print(f"{platform:<15} {status:<20} {result_symbol}")
    
    print()
    passed = sum(1 for _, _, s in results if s and not "SKIPPED" in str(_))
    total = len([r for r in results if not "SKIPPED" in str(r[0])])
    print(f"Passed: {passed}/{total} platforms")
    
    if passed == total:
        print("SUCCESS: All configured platform adapters initialized successfully!")
    else:
        print("WARNING: Some platform adapters failed to initialize. Please check configuration and network connectivity.")
    
    print()
    print("Note: This test only verifies that adapters can be initialized and establish basic connections.")
    print("Actual usage requires valid API credentials and network access permissions.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(test_platform_connectivity())
    sys.exit(0 if success else 1)
