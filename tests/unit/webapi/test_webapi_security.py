"""Web API 安全修复回归测试 —— 2026-09 P0（SEC-1/SEC-2）。

- /api/config/file：敏感文件黑名单（.env 不可读）、路径边界（兄弟目录绕过被封）
- /api/tools/task_execute：shell=True 命令执行分支已移除（RCE 回归封堵）
- /api/tools/list：不再假成功（真实 ToolNet 注册表数据）
"""

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from core.web_api import WebAPI  # noqa: E402


@pytest.fixture(scope="module")
def client():
    web_api = WebAPI(None, None)
    app = FastAPI()
    app.include_router(web_api.router)
    return TestClient(app)


# ── /api/config/file（SEC-2）───────────────────────────────────────────

def test_config_file_can_read_normal_file(client):
    resp = client.get("/api/config/file", params={"path": "pyproject.toml"})
    assert resp.status_code == 200
    body = resp.json()
    assert "content" in body
    assert "[build-system]" in body["content"]


def test_config_file_blocks_env_file(client):
    """敏感文件黑名单：config/.env 含全部密钥，必须拒绝读取。"""
    resp = client.get("/api/config/file", params={"path": "config/.env"})
    body = resp.json()
    assert "content" not in body
    assert "error" in body


def test_config_file_blocks_path_traversal(client):
    resp = client.get("/api/config/file", params={"path": "../Miya2/secret.txt"})
    body = resp.json()
    assert "content" not in body


def test_config_file_blocks_sibling_prefix_dir(client):
    """原 startswith 前缀校验可被同前缀兄弟目录（../Miya2/...）绕过。"""
    resp = client.get("/api/config/file", params={"path": "../Ranxin-evil/x.txt"})
    body = resp.json()
    assert "content" not in body


# ── /api/tools/task_execute（SEC-1 RCE 回归）──────────────────────────

def test_task_execute_rejects_shell_command(client):
    resp = client.post("/api/tools/task_execute", json={"command": "echo pwned"})
    body = resp.json()
    assert body.get("success") is False
    assert "result" not in body


# ── /api/tools/list（假成功回归）───────────────────────────────────────

def test_tools_list_returns_real_registry(client):
    """ToolNet 注册表有真实工具时，列表不得返回空数组假成功。"""
    resp = client.get("/api/tools/list")
    body = resp.json()
    assert resp.status_code == 200
    # WebAPI(None, None) 未注入 decision_hub 时走 get_tool_registry 兜底，
    # 该注册表会真实加载基础工具（时间/用户信息等），因此 tools 非空
    assert body.get("success") is True
    assert body.get("total", 0) > 0
    assert isinstance(body.get("tools"), list)
    names = {t.get("name") for t in body["tools"]}
    assert any("time" in (n or "").lower() for n in names)
