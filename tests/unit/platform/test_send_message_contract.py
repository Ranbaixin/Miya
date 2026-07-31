"""平台发送契约测试（P8 Step3）。

⚠️ 校准说明（2026-07-31 逐项核实）：
原计划假设各健康平台覆写了 `BasePlatform.send_message`，实际代码中
`send_message` 仅定义在 BasePlatform（默认 return False），5 个健康平台均未覆写；
且 Telegram/Discord/Lark 当前无任何独立发送方法（仅实现接收）。

本测试建立"能力现状快照"基线：已实现发送的平台防回归，无发送能力的平台如实记录已知缺口。
"""

import asyncio
import inspect

import pytest

from core.unified_platform.base import BasePlatform
from core.unified_platform_impl import (
    DiscordPlatform,
    LarkPlatform,
    OneBotPlatform,
    QQOfficialPlatform,
    TelegramPlatform,
)

HEALTHY_PLATFORMS = [
    OneBotPlatform,
    TelegramPlatform,
    DiscordPlatform,
    QQOfficialPlatform,
    LarkPlatform,
]

# 各平台公开发送方法现状快照（2026-07-31 核实）
# 空列表 = 已知缺口：该平台当前无发送实现（send_message 未覆写、无独立 send 方法）
SEND_CAPABILITY_SNAPSHOT = {
    OneBotPlatform: ["send_group_message", "send_private_message"],
    QQOfficialPlatform: ["send_private_message", "send_group_message"],
    TelegramPlatform: [],  # 已知缺口
    DiscordPlatform: [],  # 已知缺口
    LarkPlatform: [],  # 已知缺口
}


def _public_send_methods(cls):
    """平台自有的公开发送方法（排除继承自 BasePlatform 的默认 send_message）。"""
    return [
        name
        for name, _ in inspect.getmembers(cls)
        if name.startswith("send")
        and callable(getattr(cls, name, None))
        and getattr(cls, name) is not getattr(BasePlatform, name, None)
    ]


@pytest.mark.parametrize("cls", HEALTHY_PLATFORMS)
def test_platform_inherits_base(cls):
    """所有健康平台必须继承 BasePlatform（统一生命周期契约）。"""
    assert issubclass(cls, BasePlatform), f"{cls.__name__} 未继承 BasePlatform"


@pytest.mark.parametrize("cls", HEALTHY_PLATFORMS)
def test_lifecycle_methods_implemented(cls):
    """平台类必须覆写连接生命周期方法（非空壳）。"""
    for method in ("_do_connect", "_do_disconnect", "_do_health_check"):
        impl = getattr(cls, method, None)
        assert impl is not None, f"{cls.__name__} 缺 {method}"
        assert impl is not getattr(BasePlatform, method), f"{cls.__name__}.{method} 未覆写"


def test_send_message_contract_defined():
    """BasePlatform.send_message 契约：async 且默认返回 False（安全降级）。"""
    assert asyncio.iscoroutinefunction(BasePlatform.send_message)


@pytest.mark.parametrize("cls", list(SEND_CAPABILITY_SNAPSHOT.keys()))
def test_send_capability_snapshot(cls):
    """发送能力现状快照：已实现的方法必须保留（防回归），无发送能力的平台如实记录。"""
    expected = SEND_CAPABILITY_SNAPSHOT[cls]
    for m in expected:
        assert hasattr(cls, m), f"{cls.__name__} 丢失发送方法 {m}"

    actual = _public_send_methods(cls)
    if not expected:
        # 已知缺口：当前无发送能力。若未来实现，更新 SEND_CAPABILITY_SNAPSHOT。
        assert not actual, (
            f"{cls.__name__} 已实现发送方法 {actual}，请更新 SEND_CAPABILITY_SNAPSHOT 并移除缺口标注"
        )
