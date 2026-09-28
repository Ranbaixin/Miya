import json

from core.pc_usage_digest import resolve_digest_user_id


def test_digest_owner_resolves_from_private_permissions(tmp_path, monkeypatch):
    monkeypatch.delenv("PC_DIGEST_USER_ID", raising=False)
    monkeypatch.delenv("QQ_SUPERADMIN_QQ", raising=False)
    config = tmp_path / "permissions.json"
    config.write_text(json.dumps({"superadmins": {"owner": {"ids": {"qq": ["123456789"]}}}}), encoding="utf-8")
    assert resolve_digest_user_id(config) == "123456789"


def test_digest_owner_prefers_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("PC_DIGEST_USER_ID", "987654321")
    assert resolve_digest_user_id(tmp_path / "missing.json") == "987654321"
