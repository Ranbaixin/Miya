"""权限检查 fail-closed 回归测试（P8 Step4，P1 fail-closed 修复的安全网）。"""
import json

import pytest

from webnet.ToolNet.tools.auth.check_permission import CheckPermissionTool


@pytest.mark.asyncio
async def test_check_permission_denies_unknown_user():
    """未知用户 → 默认拒绝（fail-closed）。"""
    result = json.loads(
        await CheckPermissionTool().execute(
            {"user_id": "qq_nonexistent", "permission": "tool.web_search"}, {}
        )
    )
    assert result["allowed"] is False
    assert result["success"] is False


@pytest.mark.asyncio
async def test_check_permission_returns_structured_error():
    """权限服务不可用 → 返回结构化错误，不抛异常。"""
    result = json.loads(
        await CheckPermissionTool().execute(
            {"user_id": "qq_123", "permission": "agent.execute"}, {}
        )
    )
    assert "error" in result
    assert result["error"] == "permission_check_unavailable"


@pytest.mark.asyncio
async def test_check_permission_denies_empty_args():
    """无参数 → 默认拒绝，绝不放行（fail-closed 核心语义）。"""
    result = json.loads(await CheckPermissionTool().execute({}, {}))
    assert result["allowed"] is False
