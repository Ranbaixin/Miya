"""
WebAPI 路由 — 记忆 CRUD 与查询
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/stats")
async def memory_stats():
    return {"total": 0, "dialogue_count": 0, "short_term_count": 0, "long_term_count": 0}


@router.get("/list")
async def memory_list(limit: int = 20):
    return {"memories": [], "total": 0}


@router.get("/search")
async def memory_search(query: str = "", limit: int = 10):
    return {"results": [], "query": query}


@router.post("/add")
async def memory_add(content: str, user_id: str = "default", tags: list[str] | None = None):
    return {"memory_id": "", "content": content}
