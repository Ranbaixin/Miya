#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provider 体系测试脚本

测试新集成的 Provider 功能
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_provider_entities():
    """测试实体类"""
    print("\n" + "=" * 50)
    print("测试 Provider 实体类")
    print("=" * 50)

    from core.provider.entities import (
        ProviderType,
        ProviderStatus,
        TokenUsage,
        LLMResponse,
    )

    print(f"✓ ProviderType: {list(ProviderType)}")
    print(f"✓ ProviderStatus: {list(ProviderStatus)}")

    usage = TokenUsage(input_tokens=100, output_tokens=200)
    print(f"✓ TokenUsage: {usage.total_tokens}")

    response = LLMResponse(
        role="assistant",
        completion_text="Hello!",
        tools_call_name=["tool1"],
        tools_call_args=[{"arg1": "value1"}],
    )
    print(f"✓ LLMResponse: {response}")
    print("实体类测试通过!")


async def test_provider_registration():
    """测试 Provider 注册"""
    print("\n" + "=" * 50)
    print("测试 Provider 注册装饰器")
    print("=" * 50)

    from core.provider import register_provider, provider_cls_map, ProviderType

    print(f"已注册的 Provider 数量: {len(provider_cls_map)}")
    print(f"Provider 类型: {list(provider_cls_map.keys())}")
    print("注册装饰器测试通过!")


async def test_provider_manager():
    """测试 Provider 管理器"""
    print("\n" + "=" * 50)
    print("测试 Provider 管理器")
    print("=" * 50)

    from core.provider import get_provider_manager, ProviderType

    pm = get_provider_manager()
    print(f"✓ ProviderManager 单例: {pm is not None}")

    config = {
        "providers": [
            {
                "id": "test_openai",
                "type": "openai_chat_completion",
                "model": "gpt-4o-mini",
                "keys": ["test-key-123"],
                "api_base": "https://api.openai.com/v1",
                "enable": True,
            }
        ],
        "provider_settings": {
            "default_provider_id": "test_openai",
            "circuit_breaker_threshold": 5,
        },
    }

    await pm.initialize(config)
    print(f"✓ 已加载 Provider 数量: {len(pm.provider_insts)}")

    provider = pm.get_using_provider(ProviderType.CHAT_COMPLETION)
    print(f"✓ 获取当前 Provider: {provider.get_id() if provider else 'None'}")

    print("ProviderManager 测试通过!")


async def test_key_rotation():
    """测试 Key 轮换机制"""
    print("\n" + "=" * 50)
    print("测试 Key 轮换机制")
    print("=" * 50)

    from core.provider.sources.openai_source import OpenAIProvider

    config = {
        "id": "test_key_rotation",
        "model": "gpt-4o-mini",
        "keys": ["key1", "key2", "key3"],
        "api_base": "https://api.openai.com/v1",
    }

    provider = OpenAIProvider(config, {})

    print(f"✓ API Keys: {provider.api_keys}")

    key1 = provider.get_current_key()
    print(f"✓ 获取 Key 1: {key1}")

    key2 = provider.get_current_key()
    print(f"✓ 获取 Key 2: {key2}")

    provider.mark_key_unavailable("key1")
    print(f"✓ 标记 key1 不可用")

    key3 = provider.get_current_key()
    print(f"✓ 获取 Key 3 (跳过 key1): {key3}")

    provider.reset_keys()
    print(f"✓ 重置所有 Keys")

    print("Key 轮换测试通过!")


async def test_circuit_breaker():
    """测试熔断器"""
    print("\n" + "=" * 50)
    print("测试熔断器机制")
    print("=" * 50)

    from core.provider.sources.openai_source import OpenAIProvider

    config = {
        "id": "test_circuit",
        "model": "gpt-4o-mini",
        "keys": ["key1"],
        "api_base": "https://api.openai.com/v1",
    }

    provider = OpenAIProvider(config, {})
    provider._circuit_breaker_threshold = 3

    print(f"✓ 初始熔断状态: {provider.is_circuit_open}")

    for i in range(3):
        provider.record_failure()
        print(f"✓ 记录失败 #{i + 1}, 熔断打开: {provider.is_circuit_open}")

    provider.record_success()
    print(f"✓ 记录成功, 熔断状态重置: {provider.is_circuit_open}")

    print("熔断器测试通过!")


async def test_model_pool_integration():
    """测试 ModelPool 集成"""
    print("\n" + "=" * 50)
    print("测试 ModelPool Provider 集成")
    print("=" * 50)

    from core.model_pool_manager import get_model_pool

    pool = get_model_pool()
    print(f"✓ ModelPool 单例: {pool is not None}")
    print(f"✓ 已加载模型: {len(pool.get_all())}")

    available = pool.get_available_models()
    print(f"✓ 可用模型列表: {available[:5]}...")

    status = pool.get_provider_status()
    print(f"✓ Provider 状态: {status}")

    print("ModelPool 集成测试通过!")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("弥娅 Provider 体系测试")
    print("=" * 60)

    try:
        await test_provider_entities()
        await test_provider_registration()
        await test_key_rotation()
        await test_circuit_breaker()
        await test_provider_manager()
        await test_model_pool_integration()

        print("\n" + "=" * 60)
        print("所有测试通过!")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
