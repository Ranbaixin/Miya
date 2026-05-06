"""AutoPipeline & Skills 热重载测试"""

import asyncio
import json
import time
from pathlib import Path

import pytest


# ============================================================================
# AutoPipeline 测试
# ============================================================================


@pytest.mark.asyncio
async def test_auto_pipeline_register_and_match():
    """测试规则注册和匹配"""
    from skills.auto_pipeline import AutoPipelineRegistry, AutoPipelineRule

    registry = AutoPipelineRegistry()

    processed = []
    registry.register(
        AutoPipelineRule(
            name="test-rule",
            detect=lambda msg: "BV" in msg,
            process=lambda msg: processed.append(msg),
            priority=10,
        )
    )

    results = await registry.process_message("看看这个 BV1xx4y1W7uZ 视频")
    assert len(results) > 0
    assert results[0][0] == "test-rule"


@pytest.mark.asyncio
async def test_auto_pipeline_disabled_rule():
    """测试禁用规则不触发"""
    from skills.auto_pipeline import AutoPipelineRegistry, AutoPipelineRule

    registry = AutoPipelineRegistry()
    registry.register(
        AutoPipelineRule(
            name="disabled-rule",
            detect=lambda msg: True,
            process=lambda msg: "processed",
            enabled=False,
        )
    )

    results = await registry.process_message("任意消息")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_auto_pipeline_priority_order():
    """测试按优先级顺序执行"""
    from skills.auto_pipeline import AutoPipelineRegistry, AutoPipelineRule

    registry = AutoPipelineRegistry()
    order = []

    registry.register(
        AutoPipelineRule(
            name="low",
            detect=lambda m: True,
            process=lambda m: order.append("low"),
            priority=20,
        )
    )
    registry.register(
        AutoPipelineRule(
            name="high",
            detect=lambda m: True,
            process=lambda m: order.append("high"),
            priority=5,
        )
    )

    results = await registry.process_message("test")
    assert len(results) >= 2
    assert results[0][0] == "high"


@pytest.mark.asyncio
async def test_auto_pipeline_list_rules():
    """测试列出规则"""
    from skills.auto_pipeline import AutoPipelineRegistry, AutoPipelineRule

    registry = AutoPipelineRegistry()
    registry.register(
        AutoPipelineRule(
            name="r1",
            detect=lambda m: True,
            process=lambda m: None,
            priority=10,
        )
    )
    registry.register(
        AutoPipelineRule(
            name="r2",
            detect=lambda m: True,
            process=lambda m: None,
            priority=5,
        )
    )

    rules = registry.list_rules()
    assert len(rules) == 2
    assert rules[0]["name"] == "r2"  # 优先级高的在前


# ============================================================================
# HotReload 测试
# ============================================================================


@pytest.mark.asyncio
async def test_hot_reload_detect_change(temp_dir):
    """测试热重载检测文件变更"""
    from skills.hot_reload import HotReloadWatcher

    watch_dir = temp_dir / "skills"
    watch_dir.mkdir(parents=True, exist_ok=True)

    changed = []

    def on_reload():
        changed.append(True)

    watcher = HotReloadWatcher(
        watch_dirs=[str(watch_dir)],
        on_reload=on_reload,
        interval=0.1,
        debounce=0.05,
    )
    watcher.start()

    # 延迟后写入一个文件触发变更
    await asyncio.sleep(0.15)
    (watch_dir / "test_skill.py").write_text("# test skill\n")

    await asyncio.sleep(0.4)
    await watcher.stop()

    assert len(changed) >= 1


@pytest.mark.asyncio
async def test_hot_reload_no_change(temp_dir):
    """测试无变更时不触发"""
    from skills.hot_reload import HotReloadWatcher

    watch_dir = temp_dir / "skills"
    watch_dir.mkdir(parents=True, exist_ok=True)
    (watch_dir / "existing.py").write_text("# existing\n")
    await asyncio.sleep(0.05)

    changed = []

    watcher = HotReloadWatcher(
        watch_dirs=[str(watch_dir)],
        on_reload=lambda: changed.append(True),
        interval=0.1,
        debounce=0.05,
    )
    watcher.start()

    await asyncio.sleep(0.3)
    await watcher.stop()

    assert len(changed) == 0


# ============================================================================
# Agent Intro Generator 测试
# ============================================================================


@pytest.mark.asyncio
async def test_intro_generator_hash(temp_dir, mock_llm_func):
    """测试 hash 变更检测"""
    from skills.intro_generator import AgentIntroGenerator

    agents_dir = temp_dir / "agents" / "test_agent"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "config.json").write_text(
        json.dumps({"name": "测试Agent", "description": "用于测试的Agent"})
    )
    (agents_dir / "handler.py").write_text("def handle(): pass\n")

    gen = AgentIntroGenerator(
        agents_dir=temp_dir / "agents",
        cache_path=temp_dir / "cache.json",
        call_llm=mock_llm_func,
    )
    gen.load_cache()

    assert gen.needs_generation("test_agent") is True

    await gen.generate("test_agent")
    gen.save_cache()

    # 再次检查，不应该需要重新生成
    assert gen.needs_generation("test_agent") is False
