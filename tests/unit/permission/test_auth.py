"""auth_security 安全模块测试（2026-08 加固验收）。"""
import pytest

from core.web_api import auth_security as asec


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """隔离 .env 读写：所有测试使用内存假 env，绝不触碰真实 config/.env。"""
    fake_env: dict = {}

    def fake_read():
        return dict(fake_env)

    def fake_write(updates):
        fake_env.update(updates)

    monkeypatch.setattr(asec, "_read_env", fake_read)
    monkeypatch.setattr(asec, "_write_env", fake_write)


def test_password_hash_verify():
    p = asec.generate_random_password()
    h = asec.hash_password(p)
    assert h.startswith("scrypt$")
    assert asec.verify_password(p, h)
    assert not asec.verify_password("wrong", h)


def test_verify_password_bad_format_fail_closed():
    assert not asec.verify_password("x", "not-a-hash")
    assert not asec.verify_password("x", "")
    assert not asec.verify_password("x", "md5$12345")


def test_jwt_roundtrip():
    tok = asec.create_token("admin")
    assert asec.verify_token(tok) == "admin"


def test_jwt_garbage_fail_closed():
    assert asec.verify_token("") is None
    assert asec.verify_token("short") is None
    assert asec.verify_token("garbage-token-value-1234567890") is None
    # 过期 token：签发后手动过期（伪造 exp 过去）
    import jwt as pyjwt

    expired = pyjwt.encode(
        {"sub": "admin", "exp": 1}, asec._jwt_secret(), algorithm="HS256"
    )
    assert asec.verify_token(expired) is None


def test_verify_admin_login_no_creds_fail_closed():
    assert asec.verify_admin_login("admin", "anything") is False


def test_verify_admin_login_mock():
    asec._write_env({"MIYA_ADMIN_USERNAME": "admin", "MIYA_ADMIN_PASSWORD_HASH": asec.hash_password("secret123")})
    assert asec.verify_admin_login("admin", "secret123")
    assert not asec.verify_admin_login("admin", "wrong")
    assert not asec.verify_admin_login("evil", "secret123")


def test_no_hardcoded_passwords_in_auth_module():
    """回归：auth.py 中不得再出现硬编码口令。"""
    import pathlib

    auth_py = pathlib.Path(__file__).parent.parent.parent.parent / "core" / "web_api" / "auth.py"
    text = auth_py.read_text(encoding="utf-8")
    assert "valid_passwords" not in text
    assert "21232f297a57a5a743894a0e4a801fc3" not in text  # "admin" 的 MD5
