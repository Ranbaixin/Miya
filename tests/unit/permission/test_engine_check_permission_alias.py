"""权限引擎 check_permission 兼容别名回归测试（链路修复 Fix 1）。

修复前：UnifiedPermissionEngine 没有 check_permission 方法，PermissionCore 委托时
抛 AttributeError，被 registry 的 fail-closed 捕获 → QQ 私聊/普通群员所有工具调用被拒。
修复后：引擎提供 check_permission 兼容别名（list_mode=True 返回详情串，否则委托 check）。
"""

import json

import pytest

from core.unified_permission import UnifiedPermissionEngine


@pytest.fixture
def engine(tmp_path):
    """独立配置的权限引擎：超管 qq_869135903，QQ 平台默认 Default 组。"""
    cfg = {
        "version": "1.0.0",
        "superadmins": {
            "869135903": {"name": "然鑫", "ids": {"qq": ["869135903"]}},
        },
        "permission_groups": {
            "Default": {"permissions": ["tool.time", "tool.web_search"]},
        },
        "platform_defaults": {"qq": ["Default"]},
        "users": [],
        "command_permissions": {"enabled": False, "commands": {}},
        "special_rules": {"super_admin_whitelist": []},
    }
    path = tmp_path / "permissions.json"
    path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    return UnifiedPermissionEngine(config_path=str(path))


class TestEngineCheckPermissionAlias:
    def test_alias_superadmin_allowed(self, engine):
        """超管经别名校验任意权限 → 放行。"""
        assert engine.check_permission("qq_869135903", "tool.anything") is True

    def test_alias_unknown_user_fail_closed(self, engine):
        """未知用户检查 Default 组之外的权限 → 拒绝（fail-closed 保持）。"""
        assert engine.check_permission("qq_999999", "tool.other_tool", context={"platform": "qq"}) is False

    def test_alias_platform_default_group_applies(self, engine):
        """未知用户带上 platform 上下文 → 落 platform_defaults.qq → Default 组内的权限放行。"""
        assert engine.check_permission("qq_999999", "tool.web_search", context={"platform": "qq"}) is True

    def test_alias_list_mode_returns_detail_string(self, engine):
        """list_mode=True 返回权限详情串而非 bool（对齐 PermissionCore 传统模式约定）。"""
        result = engine.check_permission("qq_999999", "tool.time", context={"platform": "qq"}, list_mode=True)
        assert isinstance(result, str)
        assert "权限组" in result
        assert "tool.time" in result

    def test_alias_empty_user_denied(self, engine):
        """空 user_id → 拒绝。"""
        assert engine.check_permission("", "tool.time") is False


class TestPermissionCoreDelegation:
    """PermissionCore（统一配置模式）委托引擎的完整链路。"""

    def test_delegation_no_attribute_error(self, monkeypatch, engine):
        """修复点：委托调用不再 AttributeError（此前异常被 fail-closed 吞掉 → 全拒）。"""
        import core.unified_permission as up_mod

        monkeypatch.setattr(up_mod, "get_permission_engine", lambda: engine)
        from webnet.AuthNet.permission_core import PermissionCore

        core = PermissionCore(use_unified_config=True)
        assert core.check_permission("qq_869135903", "tool.x") is True
        assert core.check_permission("qq_999999", "tool.x", context={"platform": "qq"}) is False

    def test_delegation_list_mode(self, monkeypatch, engine):
        import core.unified_permission as up_mod

        monkeypatch.setattr(up_mod, "get_permission_engine", lambda: engine)
        from webnet.AuthNet.permission_core import PermissionCore

        core = PermissionCore(use_unified_config=True)
        result = core.check_permission(
            "qq_999999", "tool.time", context={"platform": "qq"}, list_mode=True
        )
        assert isinstance(result, str)
        assert "权限组" in result
