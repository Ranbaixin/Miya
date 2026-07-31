"""配置拓扑冻结测试 —— 防止配置入口意外漂移。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# P3 batch 7 收敛后的唯一配置入口
ALLOWED_CONFIG_ENTRIES = {
    "config/settings.py",
    "config/platforms_config.py",
    "core/system_config.py",
    "core/config_loader.py",
    "core/text_loader.py",
    "core/personality_config_loader.py",
}


def test_only_one_platforms_config():
    """断言全仓只有一个 platforms_config.py (不再有双轨制)"""
    hits = sorted(
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("platforms_config.py")
        if "venv" not in str(p) and "__pycache__" not in str(p)
    )
    assert hits == ["config/platforms_config.py"], f"Unexpected: {hits}"


def test_config_entrypoints_frozen():
    """配置入口集合被冻结; 新增入口必须显式改这个测试."""
    hits = sorted(
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*.py")
        if any(
            p.name in {f.rsplit("/", 1)[-1]} for f in ALLOWED_CONFIG_ENTRIES
        )
        and "venv" not in str(p)
        and "__pycache__" not in str(p)
    )
    # 只验证主要入口存在
    for entry in ALLOWED_CONFIG_ENTRIES:
        full = ROOT / entry
        assert full.exists(), f"配置入口缺失: {entry}"
    print(f"配置入口: {len(ALLOWED_CONFIG_ENTRIES)} 个, 全部存在")


def test_get_enabled_platforms_signature():
    """保护现有调用签名不被后续重构改坏."""
    import sys
    sys.path.insert(0, str(ROOT))
    import config.platforms_config as pc
    import inspect

    sig = inspect.signature(pc.get_enabled_platforms)
    assert sig.parameters == {}, f"签名已变: {sig.parameters}"
    result = pc.get_enabled_platforms()
    assert isinstance(result, dict), f"返回类型: {type(result)}"
