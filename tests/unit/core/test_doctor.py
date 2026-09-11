"""core/doctor.py 统一自检库回归测试。

覆盖：视觉模型能力校验（防 deepseek 误配复发）/ env_key / prompt 占位符双向 diff /
死键 grep 反验证 / 幽灵引用 / 配置解析 / 依赖探针 / 权限配置 / 契约同步。
"""

import json
import re
from pathlib import Path

import pytest

from core import doctor
from core.doctor import (
    FAIL,
    PASS,
    WARN,
    _extract_placeholders,
    _iter_dead_keys,
    _parse_env,
    check_config_parse,
    check_dead_config,
    check_dependencies,
    check_env,
    check_model_config,
    check_permissions,
    check_prompt_placeholders,
    has_failures,
    summarize,
)


def _statuses(finding) -> list:
    return [d.split("]")[0][1:] for d in finding.details if d.startswith("[")]


# ==================== C3 模型配置 ====================

def _write_model_config(tmp_path: Path, models: dict, active: str = "m1", env: dict = None):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "multi_model_config.json").write_text(
        json.dumps({"active": active, "models": models}, ensure_ascii=False), encoding="utf-8"
    )
    env_lines = "".join(f"{k}={v}\n" for k, v in (env or {}).items())
    (cfg_dir / ".env").write_text(env_lines, encoding="utf-8")
    return tmp_path


class TestModelConfig:
    def test_text_only_model_as_vision_fails(self, tmp_path):
        """无视觉关键字的名字配成 vision → 必须 FAIL（防'识图变瞎'复发）。

        注：deepseek 系名字已加入关键字表（V4.1 起其 API 全系原生多模态），
        历史事故模型名 deepseek-v4-flash 如今反而会被放行——这是有意的语义更新。
        """
        repo = _write_model_config(
            tmp_path,
            {"m1": {"name": "deepseek-v4-flash", "type": "vision", "base_url": "https://x/v1", "env_key": "ZHIPU_API_KEY"}},
            env={"ZHIPU_API_KEY": "sk-xxx"},
        )
        finding = check_model_config(repo)
        assert finding.status == PASS  # deepseek 全系已原生多模态

        # 真正无视觉能力的名字必须拦下
        repo2 = _write_model_config(
            tmp_path / "r2",
            {"m1": {"name": "some-text-only-model", "type": "vision", "base_url": "https://x/v1", "env_key": "ZHIPU_API_KEY"}},
            env={"ZHIPU_API_KEY": "sk-xxx"},
        )
        finding2 = check_model_config(repo2)
        assert finding2.status == FAIL
        assert any("SIMPLE_ANALYSIS" in d for d in finding2.details)

    def test_glm_vision_model_passes(self, tmp_path):
        repo = _write_model_config(
            tmp_path,
            {"m1": {"name": "glm-5.3-flash", "type": "vision", "base_url": "https://x/v1", "env_key": "ZHIPU_API_KEY"}},
            env={"ZHIPU_API_KEY": "sk-xxx"},
        )
        finding = check_model_config(repo)
        assert finding.status == PASS

    def test_missing_env_key_fails(self, tmp_path):
        """env_key 无值 → enabled=bool(api_key) 静默禁用 → FAIL。"""
        repo = _write_model_config(
            tmp_path,
            {"m1": {"name": "glm-5.3-flash", "type": "vision", "base_url": "https://x/v1", "env_key": "ZHIPU_API_KEY"}},
            env={},
        )
        finding = check_model_config(repo)
        assert any("ZHIPU_API_KEY" in d and "缺失" in d for d in finding.details)

    def test_dangling_active_fails(self, tmp_path):
        repo = _write_model_config(
            tmp_path,
            {"m1": {"name": "glm-5.3-flash", "type": "vision", "base_url": "https://x/v1"}},
            active="ghost",
            env={"ZHIPU_API_KEY": "k"},
        )
        finding = check_model_config(repo)
        assert any("ghost" in d for d in finding.details)

    def test_provider_name_as_type_warns(self, tmp_path):
        """example 配置里的 type=anthropic 异味 → WARN。"""
        repo = _write_model_config(
            tmp_path,
            {"m1": {"name": "claude-sonnet", "type": "anthropic", "base_url": "https://x/v1"}},
            env={"ZHIPU_API_KEY": "k"},
        )
        finding = check_model_config(repo)
        assert any("anthropic" in d for d in finding.details)

    def test_vision_keywords_sync_with_analyzer(self):
        """契约同步：doctor 的视觉关键字必须覆盖 multi_vision_analyzer 源码中的分类集合。"""
        source = Path(doctor.__file__).parent.joinpath("multi_vision_analyzer.py").read_text("utf-8")
        lists = re.findall(r'kw in model_name for kw in (\[[^\]]+\])', source)
        assert lists, "未在 analyzer 源码中找到视觉关键字列表（实现变了，同步契约）"
        analyzer_keywords = set()
        for lst in lists:
            analyzer_keywords |= set(re.findall(r'"(\w+)"', lst))
        assert analyzer_keywords <= set(doctor.VISION_MODEL_KEYWORDS), (
            f"analyzer 新增关键字 {analyzer_keywords - set(doctor.VISION_MODEL_KEYWORDS)} 未同步到 doctor 契约"
        )


# ==================== C4 prompt 占位符 ====================

class TestPromptPlaceholders:
    def _write(self, tmp_path, soul_prompt=None, proactive=None):
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir(exist_ok=True)
        if soul_prompt is not None:
            (cfg_dir / "soul_generator_config.json").write_text(
                json.dumps({"AI_EMOTION_ANALYSIS_PROMPT": soul_prompt}, ensure_ascii=False), encoding="utf-8"
            )
        if proactive is not None:
            try:
                import yaml
            except ImportError:
                pytest.skip("PyYAML not available")
            (cfg_dir / "proactive_chat.yaml").write_text(
                yaml.dump({"proactive_chat": proactive}, allow_unicode=True), encoding="utf-8"
            )
        return tmp_path

    def test_extra_placeholder_fails(self, tmp_path):
        """模板含代码不注入的占位符 → 字面 {xxx} 残留进 prompt → FAIL。"""
        prompt = "消息：{message} 心情：{mood_of_now}"
        repo = self._write(tmp_path, soul_prompt=prompt)
        finding = check_prompt_placeholders(repo)
        assert any("mood_of_now" in d and d.startswith("[FAIL]") for d in finding.details)

    def test_missing_placeholder_warns(self, tmp_path):
        """模板缺少契约占位符 → 对应上下文丢失 → WARN。"""
        prompt = "消息：{message}"  # 缺 user_info 等 6 个
        repo = self._write(tmp_path, soul_prompt=prompt)
        finding = check_prompt_placeholders(repo)
        assert any("user_info" in d and d.startswith("[WARN]") for d in finding.details)

    def test_proactive_extra_placeholder_fails(self, tmp_path):
        """format(**ctx) 模板 KeyError 会静默回退裸模板 → 多余占位符必须 FAIL。"""
        proactive = {
            "check_in": {"system_prompt": "【{persona}】闲置 {idle_duration}，备注 {nonexistent_key}"},
        }
        repo = self._write(tmp_path, proactive=proactive)
        finding = check_prompt_placeholders(repo)
        assert any("nonexistent_key" in d for d in finding.details)

    def test_valid_templates_pass(self, tmp_path):
        prompt = "消息：{message} 对方：{user_info} 之前：{previous_emotion} {form_style} {conversation_context} {memory_context} {owner_instruction}"
        repo = self._write(tmp_path, soul_prompt=prompt)
        finding = check_prompt_placeholders(repo)
        assert finding.status == PASS

    def test_extract_placeholders_skips_json_examples(self):
        """JSON 示例块里的 "key": {...} 不应被当作占位符。"""
        text = '你好 {message}\n示例：\n{\n  "emotions": [],\n  "inner_thought": "x"\n}'
        assert _extract_placeholders(text) == {"message"}


# ==================== C1 死配置 / 幽灵引用 ====================

class TestDeadConfig:
    def test_zero_hit_key_reported(self, tmp_path):
        """配置键全仓 0 消费 → 死键 WARN；有消费的键不报。"""
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "diteng_strategy_config.json").write_text(
            json.dumps({"comment": "x", "enabled": True, "DEAD_KEY_ZZZ": 1, "timeout": 30}), encoding="utf-8"
        )
        src = tmp_path / "memory"
        src.mkdir()
        (src / "consumer.py").write_text('config.get("timeout", 10)\n', encoding="utf-8")
        finding = check_dead_config(tmp_path)
        assert any("DEAD_KEY_ZZZ" in d for d in finding.details)
        assert not any("timeout" in d and "死键" in d for d in finding.details)

    def test_nested_dead_key_reported(self, tmp_path):
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "proactive_chat.yaml").write_text(
            "proactive_chat:\n  ai_trigger:\n    enabled: true\n    sensitivity: high\n",
            encoding="utf-8",
        )
        src = tmp_path / "core"
        src.mkdir()
        (src / "c.py").write_text('x = "ai_trigger"\n', encoding="utf-8")
        finding = check_dead_config(tmp_path)
        assert any("sensitivity" in d for d in finding.details)

    def test_ghost_reference_fails(self, tmp_path):
        """代码读取但配置不存在的键 → FAIL（静默回退默认值）。"""
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "text_config.json").write_text(json.dumps({"version": "1.0"}), encoding="utf-8")
        finding = check_dead_config(tmp_path)
        assert any("strategy_defaults" in d for d in finding.details)
        assert finding.status == FAIL

    def test_iter_dead_keys_depth_zero(self, tmp_path):
        """text_config 类文件只扫顶层（depth=0），嵌套键不产生噪音。"""
        node = {"top_dead": 1, "top_alive": {"nested_dead": 2}}
        src = tmp_path / "core"
        src.mkdir()
        (src / "c.py").write_text('x = "top_alive"\n', encoding="utf-8")
        dead = _iter_dead_keys(node, "", set(), tmp_path, max_depth=0)
        assert dead == ["top_dead"]


# ==================== C2/C5/C6/C7 ====================

class TestConfigParse:
    def test_syntax_error_fails(self, tmp_path):
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "text_config.json").write_text("{broken json", encoding="utf-8")
        finding = check_config_parse(tmp_path)
        assert finding.status == FAIL

    def test_missing_required_fails(self, tmp_path):
        (tmp_path / "config").mkdir()
        finding = check_config_parse(tmp_path)
        assert any("multi_model_config.json" in d for d in finding.details)


class TestDependencies:
    def test_missing_package_fails(self):
        finding = check_dependencies(probes={"no_such_pkg_zzz_doctor": "no-such-pkg-zzz"})
        assert finding.status == FAIL

    def test_real_package_passes(self):
        finding = check_dependencies(probes={"json": "stdlib"})
        assert finding.status == PASS


class TestEnv:
    def test_missing_env_file_fails(self, tmp_path):
        (tmp_path / "config").mkdir()
        finding = check_env(tmp_path)
        assert finding.status == FAIL

    def test_missing_zhipu_key_fails(self, tmp_path):
        cfg = tmp_path / "config"
        cfg.mkdir()
        (cfg / ".env").write_text("QQ_BOT_QQ=123\n", encoding="utf-8")
        finding = check_env(tmp_path)
        assert any("ZHIPU_API_KEY" in d for d in finding.details)

    def test_all_present_passes(self, tmp_path):
        cfg = tmp_path / "config"
        cfg.mkdir()
        keys = "\n".join(f"{k}=v\n" for k in doctor.REQUIRED_ENV_KEYS)
        (cfg / ".env").write_text(keys, encoding="utf-8")
        finding = check_env(tmp_path)
        assert finding.status == PASS

    def test_parse_env_handles_quotes_and_comments(self, tmp_path):
        p = tmp_path / "x.env"
        p.write_text('# c\nA=1\nB="two"\nC=three\n\n', encoding="utf-8")
        env = _parse_env(p)
        assert env == {"A": "1", "B": "two", "C": "three"}


class TestPermissions:
    def test_empty_superadmins_fails(self, tmp_path):
        cfg = tmp_path / "config"
        cfg.mkdir()
        (cfg / "permissions.json").write_text(json.dumps({"superadmins": {}, "permission_groups": {}}), encoding="utf-8")
        finding = check_permissions(tmp_path)
        assert finding.status == FAIL

    def test_valid_permissions_pass(self, tmp_path):
        cfg = tmp_path / "config"
        cfg.mkdir()
        (cfg / "permissions.json").write_text(
            json.dumps({"superadmins": {"869135903": {"ids": {"qq": ["869135903"]}}}, "permission_groups": {"Default": {"permissions": []}}}),
            encoding="utf-8",
        )
        finding = check_permissions(tmp_path)
        assert finding.status == PASS


class TestRuntimeSignatures:
    def test_matplotlib_accepted_state_not_failed(self):
        """已知接受状态：matplotlib 缺失（viz 可选组内存优化）不得触发 No module named FAIL。"""
        sample = "加载可视化工具失败: No module named 'matplotlib'"
        pattern = doctor.RUNTIME_ERROR_SIGNATURES[0][0]
        assert not re.search(pattern, sample)

    def test_real_missing_dependency_still_fails(self):
        """真实依赖缺失（PIL 等）仍必须命中 FAIL 签名。"""
        pattern = doctor.RUNTIME_ERROR_SIGNATURES[0][0]
        assert re.search(pattern, "加载QQ多媒体工具失败: No module named 'PIL'")
        assert re.search(pattern, "No module named 'chardet'")

    def test_signature_table_non_empty(self):
        assert len(doctor.RUNTIME_ERROR_SIGNATURES) >= 8


# ==================== 聚合 ====================

class TestAggregate:
    def test_summarize_and_has_failures(self):
        f1 = doctor.Finding("C1", "t1", PASS)
        f2 = doctor.Finding("C2", "t2", FAIL)
        assert summarize([f1, f2]) == {"PASS": 1, "WARN": 0, "FAIL": 1, "SKIP": 0}
        assert has_failures([f1, f2]) is True
        assert has_failures([f1]) is False
