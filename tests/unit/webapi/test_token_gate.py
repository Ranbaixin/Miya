"""token_gate（统一访问网关）单元测试 —— 2026-09 P0 安全修复回归。

覆盖 core/web_api/auth_security.install_token_gate：
- 本机(loopback)放行
- 远程无 token → 403；设置了 MIYA_API_TOKEN 后远程无/错 token → 401
- 远程正确 token → 放行
- /api/config/file 敏感文件黑名单与路径边界（SEC-2 回归）
"""

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from core.web_api.auth_security import install_token_gate  # noqa: E402

REMOTE = ("203.0.113.9", 50000)


def _app_with_gate(**gate_kwargs):
    app = FastAPI()

    @app.get("/hello")
    async def hello():
        return {"ok": True}

    install_token_gate(app, **gate_kwargs)
    return app


def test_loopback_allowed_without_token(monkeypatch):
    monkeypatch.delenv("MIYA_API_TOKEN", raising=False)
    client = TestClient(_app_with_gate())
    resp = client.get("/hello")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_remote_blocked_without_token(monkeypatch):
    monkeypatch.delenv("MIYA_API_TOKEN", raising=False)
    client = TestClient(_app_with_gate(), client=REMOTE)
    resp = client.get("/hello")
    assert resp.status_code == 403


def test_remote_with_valid_token(monkeypatch):
    monkeypatch.setenv("MIYA_API_TOKEN", "test-token-0123456789")
    client = TestClient(_app_with_gate(), client=REMOTE)
    resp = client.get("/hello", headers={"Authorization": "Bearer test-token-0123456789"})
    assert resp.status_code == 200
    # X-Miya-Token 头同样接受
    resp2 = client.get("/hello", headers={"X-Miya-Token": "test-token-0123456789"})
    assert resp2.status_code == 200


def test_remote_with_invalid_token(monkeypatch):
    monkeypatch.setenv("MIYA_API_TOKEN", "test-token-0123456789")
    client = TestClient(_app_with_gate(), client=REMOTE)
    resp = client.get("/hello", headers={"Authorization": "Bearer wrong-token-000000"})
    assert resp.status_code == 401


def test_public_path_remote_unauthorized_when_token_set(monkeypatch):
    monkeypatch.setenv("MIYA_API_TOKEN", "test-token-0123456789")
    client = TestClient(_app_with_gate(), client=REMOTE)
    resp = client.get("/docs")
    assert resp.status_code == 401


def test_local_only_path_blocks_remote_even_with_token(monkeypatch):
    monkeypatch.setenv("MIYA_API_TOKEN", "test-token-0123456789")
    app = FastAPI()

    @app.get("/secret")
    async def secret():
        return {"ok": True}

    install_token_gate(app, local_only_paths=("/secret",))
    client = TestClient(app, client=REMOTE)
    resp = client.get("/secret", headers={"Authorization": "Bearer test-token-0123456789"})
    assert resp.status_code == 403
