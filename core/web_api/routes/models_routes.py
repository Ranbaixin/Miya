"""
WebAPI 路由 — 模型池与调度
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/list")
async def models_list():
    return {"models": [], "default": ""}


@router.get("/status")
async def models_status():
    return {"available": 0, "current": ""}


@router.post("/select")
async def models_select(model: str = "", task_type: str = "chat"):
    return {"selected": model, "task_type": task_type}
