"""PC 使用作息每日沉淀任务

每晚经 pc_tracker 桥（SSH 反向隧道 127.0.0.1:9443 → 家里电脑 8088）
拉取当日电脑使用摘要（text_summary），写入长期记忆（tags: pc_usage/作息），
让弥娅跨会话了解然鑫的电脑作息。桥不可达（电脑离线）时跳过当日，不影响主服务。

配置（环境变量）：
  PC_DIGEST_ENABLED  默认 true
  PC_DIGEST_HOUR     默认 23（点）
  PC_DIGEST_MINUTE   默认 30（分）
  PC_DIGEST_USER_ID  可选；默认从私有 permissions.json 的 QQ 超管读取
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("pc_usage_digest")

_task: asyncio.Task | None = None


def resolve_digest_user_id(config_path: Path | None = None) -> str | None:
    """Resolve the owner without embedding a personal account ID in source."""
    for key in ("PC_DIGEST_USER_ID", "QQ_SUPERADMIN_QQ"):
        value = os.getenv(key, "").strip()
        if value:
            return value

    path = config_path or Path(__file__).resolve().parent.parent / "config" / "permissions.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for info in config.get("superadmins", {}).values():
        for user_id in info.get("ids", {}).get("qq", []):
            if str(user_id).isdigit():
                return str(user_id)
    return None


async def _fetch_text_summary() -> str | None:
    from mcpserver.pc_tracker.service import get_pc_tracker_service

    service = get_pc_tracker_service()
    if not await service.health_check():
        return None
    return await service.get_text_summary()


async def digest_once() -> bool:
    """执行一次沉淀。成功写入返回 True；桥不可达/无摘要返回 False。"""
    from memory import store_important

    user_id = resolve_digest_user_id()
    if not user_id:
        logger.warning("[PC作息] 未配置所有者 QQ，跳过当日摘要")
        return False

    summary = await _fetch_text_summary()
    if not summary:
        logger.info("[PC作息] 桥不可达或无当日摘要，今日跳过")
        return False
    await store_important(
        f"[电脑作息] {summary}",
        user_id=user_id,
        tags=["pc_usage", "作息"],
        priority=0.5,
        metadata={"source": "pc_usage_digest", "date": datetime.now().strftime("%Y-%m-%d")},
    )
    logger.info(f"[PC作息] 当日摘要已写入长期记忆（{len(summary)} 字）")
    return True


def _next_run(now: datetime) -> datetime:
    hour = int(os.getenv("PC_DIGEST_HOUR", "23"))
    minute = int(os.getenv("PC_DIGEST_MINUTE", "30"))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


async def _loop():
    hour = int(os.getenv("PC_DIGEST_HOUR", "23"))
    minute = int(os.getenv("PC_DIGEST_MINUTE", "30"))
    logger.info(f"[PC作息] 每日沉淀任务已启动（每日 {hour:02d}:{minute:02d}，桥断线自动跳过）")
    while True:
        wait = (_next_run(datetime.now()) - datetime.now()).total_seconds()
        logger.debug(f"[PC作息] 距下次沉淀 {wait:.0f}s")
        await asyncio.sleep(max(wait, 1))
        try:
            await digest_once()
        except Exception as e:  # noqa: BLE001 — 沉淀失败不影响主服务
            logger.warning(f"[PC作息] 沉淀异常（不影响主服务）: {e}")


def start_daily_digest():
    """启动每日沉淀后台任务（幂等；失败返回 None）"""
    global _task
    if _task and not _task.done():
        return _task
    if os.getenv("PC_DIGEST_ENABLED", "true").lower() not in ("1", "true", "yes"):
        logger.info("[PC作息] 已通过 PC_DIGEST_ENABLED 停用")
        return None
    _task = asyncio.create_task(_loop(), name="pc_usage_digest")
    return _task
