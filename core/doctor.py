"""
Miya 统一自检库 — 全项目配置/依赖/运行时体检（防"带病不自知"复发）

设计原则：
1. 纯标准库实现（不 import 项目内模块），可被 daemon 启动预检、CLI、CI、systemd timer 复用
2. 每项检查输出 Finding（PASS/WARN/FAIL/SKIP），FAIL 决定退出码非零
3. 所有"删除/修复"类结论必须经全仓 grep 反验证，禁止凭单一来源断言（防止误杀活配置）

检查项：
  C1 死配置检测（grep 反验证 + 幽灵引用）
  C2 配置可解析性（json/yaml 语法 + 必需文件存在）
  C3 模型配置校验（type 合法值 / 视觉模型能力关键字 / env_key 非空 / active 指向存在）
  C4 prompt 占位符校验（模板占位符与代码注入键双向 diff）
  C5 依赖完整性探针（子进程 import 测试）
  C6 环境变量校验（.env 存在 + 必需键非空）
  C7 权限配置校验（superadmins / Default 组）
  C8 运行时诊断（--runtime：健康端点 + journalctl 错误签名 + crash-loop）
  C9 记忆一致性（--runtime：复用 scripts/check_memory_consistency.py）
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
SKIP = "SKIP"

# grep 反验证的源码目录（不含 tests/ —— 测试引用不算运行时消费）
SOURCE_DIRS = ("core", "hub", "memory", "webnet", "utils", "run", "plugins", "scripts")


@dataclass
class Finding:
    """单项检查结果"""

    check_id: str
    title: str
    status: str = PASS
    details: list = field(default_factory=list)
    fix_hints: list = field(default_factory=list)

    def add(self, status: str, detail: str, fix_hint: str = ""):
        if status in (FAIL, WARN):
            self.details.append(f"[{status}] {detail}")
            if fix_hint:
                self.fix_hints.append(fix_hint)
            if status == FAIL or self.status != FAIL:
                self.status = status if self.status != FAIL else FAIL
        else:
            self.details.append(detail)


# ==================== 契约表（配置语义的权威声明，随代码维护） ====================

# C3：视觉模型能力关键字 —— 必须与 core/multi_vision_analyzer.py 的分类集合一致
# （不一致时模型会被误判为 SIMPLE_ANALYSIS 落入本地降级，即"识图变瞎"事故的根源）
VISION_MODEL_KEYWORDS = ("glm", "qwen", "internvl", "llava", "kimi", "moonshot")

# C3：multi_model_config.models[].type 合法值（ModelType 枚举 + 实际使用的默认 "chat"）
ALLOWED_MODEL_TYPES = {"chat", "text", "vision", "ocr", "embedding", "multimodal", "safety"}

# C4：soul_generator 的 AI_EMOTION_ANALYSIS_PROMPT 注入键（soul_generator.py replace 链）
SOUL_PROMPT_PLACEHOLDERS = {
    "message",
    "user_info",
    "previous_emotion",
    "form_style",
    "conversation_context",
    "memory_context",
    "owner_instruction",
}

# C4：proactive_chat.yaml 各触发器 system_prompt 的注入键（format(**ctx) 模式；
# persona/memory 对所有触发器注入，其余为触发器专属）
PROACTIVE_PROMPT_CONTRACT = {
    "context_trigger": {"persona", "memory", "expectation"},
    "emotion_perception": {"persona", "memory", "emotion"},
    "keyword_trigger": {"persona", "memory", "keywords"},
    "time_awareness": {"persona", "memory", "time_period"},
    "check_in": {"persona", "memory", "idle_duration"},
}

# C4：text_config.json 的 system_prompts.default_system_prompt 注入键
DEFAULT_SYSTEM_PROMPT_PLACEHOLDERS = {"owner_name", "status_prompt", "emotion_reasoning_prompt", "soul_state"}

# C1：参与死键扫描的配置文件（键名 grep 反验证模式）与递归深度
# （text_config 嵌套键多为文案级、经点号路径动态消费，只扫顶层；yaml/json 扫两层）
DEADKEY_SCAN_FILES = (
    ("soul_generator_config.json", 1),
    ("diteng_strategy_config.json", 1),
    ("text_config.json", 0),
    ("proactive_chat.yaml", 1),
)

# C1：结构性通用键豁免（这些键被代码按结构消费，键名本身不出现在源码中）
DEADKEY_STRUCTURE_WHITELIST = {
    "proactive_chat.yaml": {
        "enabled",
        "platforms",
        "system_prompt",
        "use_ai",
        "keywords",
        "responses",
        "messages",
        "topics",
        "greeting_keywords",
        "time_slots",
        "check_interval",
        "expectations",
        "emotion_keywords",
        "emotion_responses",
        "response_strategies",
        "intent_types",
        "reply_styles",
        "judge_rules",
        "max_responses_per_turn",
        "default_max_messages",
    },
    "text_config.json": {"version", "description"},
    "soul_generator_config.json": {
        "comment",
        "AI_ANALYSIS_ENABLED",
        # 动态键消费节：soul_generator.py 泛型遍历 / .get(rel_key) 取键，嵌套键 grep 不可见
        "MESSAGE_EMOTION_TRIGGERS",
        "RELATIONSHIP_EMOTION_EFFECTS",
        "RELATIONSHIP_LABELS",
    },
    "diteng_strategy_config.json": {
        "comment",
        "enabled",
        # 枚举映射节：嵌套键经 json.dumps 序列化进 LLM 判断 prompt（grep 不可见），禁止递归扫描
        "response_strategies",
        "intent_types",
        "reply_styles",
    },
}

# C1：幽灵引用 —— 代码读取但配置中可能不存在的键（文件 → 配置内点号路径 → 消费者）
GHOST_REF_CHECKS = (
    ("text_config.json", "strategy_defaults", "memory/diteng_listener.py get_memory_section('strategy_defaults')"),
    ("text_config.json", "proactive_chat.scene", "core/proactive_chat.py _load_text_config('scene.*')（实际路径 proactive_chat.scene）"),
    ("text_config.json", "proactive_chat.default_prompts", "core/proactive_chat.py _default_ai_prompt"),
    ("text_config.json", "soul_generator", "core/soul_generator.py owner_instruction / form_inner_thought_hint / json_format_constraint"),
    ("text_config.json", "system_prompts", "core/prompt_manager.py default_system_prompt"),
)

# C5：依赖探针（import 名 → pip 包名提示）
DEPENDENCY_PROBES = {
    "PIL": "pillow（QQ 多媒体工具链依赖，缺失即整包加载失败）",
    "chardet": "chardet（qq_file_reader 依赖）",
    "jieba": "jieba",
    "apscheduler": "apscheduler",
    "httpx": "httpx",
    "openai": "openai",
    "tiktoken": "tiktoken",
    "tenacity": "tenacity",
    "yaml": "PyYAML（proactive_chat/personalities 配置加载）",
    "aiohttp": "aiohttp",
    "bs4": "beautifulsoup4",
    "requests": "requests",
    "dotenv": "python-dotenv",
}

# C6：必需环境变量（值 → 缺失严重级；ZHIPU_API_KEY 缺失 = 模型池全禁用 → AI 降级）
REQUIRED_ENV_KEYS = {
    "ZHIPU_API_KEY": FAIL,
    "QQ_ONEBOT_WS_URL": WARN,
    "QQ_BOT_QQ": WARN,
    "QQ_SUPERADMIN_QQ": WARN,
    "MIYA_JWT_SECRET": WARN,
    "TAVILY_API_KEY": WARN,
}

# C8：journalctl 错误签名（pattern, 阈值, 级别, 说明）
# 注：matplotlib 为内存优化决策的已知缺失（viz 可选组），负向断言排除，由"加载\S*工具失败"WARN 承接
RUNTIME_ERROR_SIGNATURES = (
    (r"No module named '(?!matplotlib')", 1, FAIL, "依赖缺失（工具包加载失败/启动崩溃根源）"),
    (r"ModuleNotFoundError", 1, FAIL, "模块缺失"),
    (r"加载\S*工具失败", 1, WARN, "工具包加载失败（可选依赖缺失降级）"),
    (r"权限检查异常", 1, FAIL, "权限引擎异常（fail-closed 全拒）"),
    (r"permission_check_unavailable", 1, WARN, "权限检查不可用降级响应"),
    (r"回退独立谛听", 3, WARN, "预分析合并回退（透传/schema 断裂）"),
    (r"分析超时，使用默认策略", 3, WARN, "谛听策略超时"),
    (r"守护进程异常", 1, FAIL, "守护进程启动异常"),
)

# C8：crash-loop 判定（窗口内 systemd 重启次数）
CRASH_LOOP_THRESHOLD = 3


# ==================== 工具函数 ====================

def _load_json(path: Path) -> Any:
    return json.loads(path.read_text("utf-8"))


def _parse_env(path: Path) -> dict:
    """极简 .env 解析（KEY=VALUE，忽略注释/空行），不依赖 python-dotenv"""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _grep_source_count(key: str, repo_root: Path) -> int:
    """全仓源码 grep 键名出现次数（词边界，排除 tests/）"""
    pattern = re.compile(rf"\b{re.escape(key)}\b")
    count = 0
    for src_dir in SOURCE_DIRS:
        base = repo_root / src_dir
        if not base.exists():
            continue
        for py in base.rglob("*.py"):
            try:
                count += len(pattern.findall(py.read_text("utf-8", errors="replace")))
            except OSError:
                continue
    return count


def _extract_placeholders(text: str) -> set:
    """提取模板中的 {placeholder}（排除 {{ }} 转义与 JSON 示例中的常见冲突）"""
    text = re.sub(r"\{\{.*?\}\}", "", text)
    return set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", text))


# ==================== C1 死配置检测 ====================

def check_dead_config(repo_root: Path = REPO_ROOT) -> Finding:
    """死配置键检测：配置中的键经全仓 grep 反验证，0 消费 → WARN 死键候选"""
    finding = Finding("C1", "死配置检测（grep 反验证）")
    config_dir = repo_root / "config"

    for filename, max_depth in DEADKEY_SCAN_FILES:
        path = config_dir / filename
        if not path.exists():
            finding.add(WARN, f"{filename} 不存在，跳过死键扫描")
            continue
        try:
            data = _load_json(path) if filename.endswith(".json") else _load_yaml(path)
        except Exception as e:  # noqa: BLE001 — 解析失败由 C2 报告
            finding.add(WARN, f"{filename} 解析失败（{e}），跳过死键扫描")
            continue

        whitelist = DEADKEY_STRUCTURE_WHITELIST.get(filename, set())
        # proactive_chat.yaml 有根包裹键 proactive_chat:，解包后再扫（否则嵌套死键深度不够）
        if isinstance(data, dict) and len(data) == 1 and "proactive_chat" in data:
            data = data["proactive_chat"]
        dead_keys = _iter_dead_keys(data, "", whitelist, repo_root, max_depth=max_depth)
        for key_path in dead_keys:
            finding.add(
                WARN,
                f"{filename} 死键（全仓 0 消费）: {key_path}",
                f"确认无预留用途后从 {filename} 删除，或将该键接线到消费代码",
            )

    # 幽灵引用：代码读取但配置缺失（点号路径下钻）
    for filename, key_path, consumer in GHOST_REF_CHECKS:
        path = config_dir / filename
        if not path.exists():
            continue
        try:
            data = _load_json(path) if filename.endswith(".json") else _load_yaml(path)
        except Exception:  # noqa: BLE001 — 解析失败由 C2 报告
            continue
        node = data
        for part in key_path.split("."):
            if not isinstance(node, dict) or part not in node:
                node = None
                break
            node = node[part]
        if node is None:
            finding.add(
                FAIL,
                f"幽灵引用: {consumer} 读取 {filename} 的 '{key_path}'，但配置中不存在（静默回退默认值）",
                f"在 {filename} 中补充 '{key_path}' 配置，或修正代码读取路径",
            )

    if not finding.details:
        finding.add(PASS, "未发现死配置键或幽灵引用")
    return finding


def _iter_dead_keys(node: Any, prefix: str, whitelist: set, repo_root: Path, depth: int = 0, max_depth: int = 1) -> list:
    """递归收集 0 消费键（深度受 max_depth 限制：0=仅顶层，1=顶层+一层嵌套）"""
    dead = []
    if not isinstance(node, dict) or depth > max_depth:
        return dead
    for key, value in node.items():
        if key.startswith("comment") or key in whitelist:
            continue
        key_path = f"{prefix}.{key}" if prefix else key
        if _grep_source_count(key, repo_root) == 0:
            dead.append(key_path)
        elif isinstance(value, dict):
            dead.extend(_iter_dead_keys(value, key_path, whitelist, repo_root, depth + 1, max_depth))
    return dead


def _load_yaml(path: Path) -> Any:
    import yaml

    return yaml.safe_load(path.read_text("utf-8"))


# ==================== C2 配置可解析性 ====================

REQUIRED_CONFIG_FILES = (
    "multi_model_config.json",
    "soul_generator_config.json",
    "diteng_strategy_config.json",
    "text_config.json",
    "proactive_chat.yaml",
    "permissions.json",
    "qq_config.yaml",
)


def check_config_parse(repo_root: Path = REPO_ROOT) -> Finding:
    """全部配置文件语法可解析 + 必需文件存在"""
    finding = Finding("C2", "配置可解析性")
    config_dir = repo_root / "config"

    for filename in REQUIRED_CONFIG_FILES:
        path = config_dir / filename
        if not path.exists():
            finding.add(FAIL, f"必需配置缺失: config/{filename}", "恢复该配置文件（git checkout 或参照 example）")
            continue
        try:
            if filename.endswith(".json"):
                _load_json(path)
            else:
                _load_yaml(path)
        except Exception as e:  # noqa: BLE001 — 语法错误必须报告
            finding.add(FAIL, f"配置语法错误: config/{filename}: {e}", "修复语法错误（json/yaml 校验器）")

    # 可选但推荐
    for optional in ("tts_config.json", ".env"):
        if not (config_dir / optional).exists():
            example = config_dir / f"{optional}.example"
            hint = f"参照 {example.name} 创建" if example.exists() else "从备份恢复"
            finding.add(WARN, f"推荐配置缺失: config/{optional}（{hint}）")

    # 扫描全部 json/yaml 语法
    for pattern in ("*.json", "*.yaml"):
        for path in config_dir.glob(pattern):
            if path.name.endswith(".example") or path.name.startswith("."):
                continue
            try:
                if path.suffix == ".json":
                    _load_json(path)
                else:
                    _load_yaml(path)
            except Exception as e:  # noqa: BLE001 — 语法错误必须报告
                finding.add(FAIL, f"配置语法错误: {path.name}: {e}", "修复语法错误")

    if not finding.details:
        finding.add(PASS, f"config/ 下全部配置可解析，必需文件齐全")
    return finding


# ==================== C3 模型配置校验 ====================

def check_model_config(repo_root: Path = REPO_ROOT) -> Finding:
    """多模型配置语义校验：视觉模型能力、env_key、active 指向"""
    finding = Finding("C3", "模型配置校验")
    path = repo_root / "config" / "multi_model_config.json"
    if not path.exists():
        finding.add(FAIL, "multi_model_config.json 不存在")
        return finding

    try:
        cfg = _load_json(path)
    except Exception as e:  # noqa: BLE001 — 语法错误由 C2 报告
        finding.add(FAIL, f"解析失败: {e}")
        return finding

    models = cfg.get("models", {})
    env = _parse_env(repo_root / "config" / ".env")
    active = cfg.get("active")

    if active and active not in models:
        finding.add(FAIL, f"active='{active}' 不在 models 中", "修正 active 指向或补齐模型定义")

    for model_id, model in models.items():
        if not isinstance(model, dict):
            continue
        name = model.get("name", "")
        model_type = model.get("type", "chat")

        if model_type not in ALLOWED_MODEL_TYPES:
            finding.add(
                WARN,
                f"模型 {model_id}: type='{model_type}' 不在合法值 {sorted(ALLOWED_MODEL_TYPES)}（provider 名误用作 type？）",
                "改为 chat/text/vision/ocr/embedding/multimodal/safety 之一",
            )

        if model_type == "vision":
            name_lower = name.lower()
            if not any(kw in name_lower for kw in VISION_MODEL_KEYWORDS):
                finding.add(
                    FAIL,
                    f"视觉模型 {model_id} (name={name}) 不含视觉能力关键字 {VISION_MODEL_KEYWORDS}，"
                    "将被 multi_vision_analyzer 判为 SIMPLE_ANALYSIS（本地降级 = 识图失效）",
                    "换成多模态模型（如 glm-4v*/glm-5*/qwen-vl 系列）",
                )

        env_key = model.get("env_key", "")
        if env_key and not env.get(env_key):
            finding.add(
                FAIL,
                f"模型 {model_id} 的 env_key='{env_key}' 在 config/.env 中缺失或为空（enabled=bool(api_key) → 模型被静默禁用）",
                f"在 config/.env 中配置 {env_key}",
            )

        if not model.get("base_url"):
            finding.add(FAIL, f"模型 {model_id} 缺少 base_url（加载器会直接跳过）")

    if not finding.details:
        finding.add(PASS, f"模型配置语义正常（{len(models)} 个模型，active={active}）")
    return finding


# ==================== C4 prompt 占位符校验 ====================

def check_prompt_placeholders(repo_root: Path = REPO_ROOT) -> Finding:
    """模板占位符与代码注入键双向 diff：缺注入键 → 残留 {xxx} 进 prompt；多注入键 → 上下文丢失"""
    finding = Finding("C4", "prompt 占位符校验")
    config_dir = repo_root / "config"

    # 1) soul_generator 的 replace 链模板
    soul_path = config_dir / "soul_generator_config.json"
    if soul_path.exists():
        try:
            prompt = _load_json(soul_path).get("AI_EMOTION_ANALYSIS_PROMPT", "")
            tokens = _extract_placeholders(prompt)
            missing = SOUL_PROMPT_PLACEHOLDERS - tokens
            extra = tokens - SOUL_PROMPT_PLACEHOLDERS
            if missing:
                finding.add(
                    WARN,
                    f"AI_EMOTION_ANALYSIS_PROMPT 缺少注入占位符: {sorted(missing)}（对应上下文将丢失）",
                    "在模板中补回 {key} 占位符",
                )
            if extra:
                finding.add(
                    FAIL,
                    f"AI_EMOTION_ANALYSIS_PROMPT 含未注入占位符: {sorted(extra)}（字面 {extra} 会残留在最终 prompt）",
                    "删除该占位符或在 soul_generator.py replace 链中补注入",
                )
        except Exception as e:  # noqa: BLE001 — 解析失败由 C2 报告
            finding.add(WARN, f"soul_generator_config.json 解析失败（{e}），跳过 C4 检查")

    # 2) proactive_chat.yaml 的 format 模板
    pc_path = config_dir / "proactive_chat.yaml"
    if pc_path.exists():
        try:
            data = (_load_yaml(pc_path) or {}).get("proactive_chat", {})
            for section, expected in PROACTIVE_PROMPT_CONTRACT.items():
                template = (data.get(section) or {}).get("system_prompt", "")
                if not template:
                    continue
                tokens = _extract_placeholders(template)
                extra = tokens - expected
                if extra:
                    finding.add(
                        FAIL,
                        f"proactive_chat.yaml {section}.system_prompt 含未注入占位符: {sorted(extra)}"
                        "（format KeyError 会静默回退裸模板）",
                        f"删除占位符或在 proactive_chat.py 注入键中补充",
                    )
        except Exception as e:  # noqa: BLE001 — yaml 缺失时跳过
            finding.add(WARN, f"proactive_chat.yaml 解析失败（{e}），跳过该文件 C4 检查")

    # 3) text_config 的 default_system_prompt
    tc_path = config_dir / "text_config.json"
    if tc_path.exists():
        try:
            template = (_load_json(tc_path).get("system_prompts") or {}).get("default_system_prompt", "")
            if template:
                tokens = _extract_placeholders(template)
                known = DEFAULT_SYSTEM_PROMPT_PLACEHOLDERS | {"owner_name"}
                extra = tokens - known
                if extra:
                    finding.add(
                        WARN,
                        f"default_system_prompt 含额外占位符: {sorted(extra)}（确认 prompt_manager 是否注入）",
                        "补注入或删除占位符",
                    )
        except Exception as e:  # noqa: BLE001 — 解析失败由 C2 报告
            finding.add(WARN, f"text_config.json 解析失败（{e}），跳过该文件 C4 检查")

    if not finding.details:
        finding.add(PASS, "全部 prompt 模板占位符与注入键匹配")
    return finding


# ==================== C5 依赖探针 ====================

def check_dependencies(probes: Optional[dict] = None) -> Finding:
    """子进程 import 探针：与运行环境隔离，缺失依赖逐个报告"""
    finding = Finding("C5", "依赖完整性探针")
    probes = probes or DEPENDENCY_PROBES
    probe_script = (
        "import json, importlib\n"
        f"probes = {json.dumps(list(probes.keys()))}\n"
        "result = {}\n"
        "for name in probes:\n"
        "    try:\n"
        "        importlib.import_module(name)\n"
        "        result[name] = ''\n"
        "    except Exception as e:\n"
        "        result[name] = str(e)\n"
        "print(json.dumps(result))\n"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", probe_script],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(REPO_ROOT),
        )
        result = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        finding.add(WARN, f"依赖探针执行失败: {e}")
        return finding

    missing = {name: err for name, err in result.items() if err}
    if missing:
        for name, err in missing.items():
            finding.add(
                FAIL,
                f"依赖缺失: import {name} 失败（{err}）",
                f"安装: uv pip install {probes[name].split('（')[0]}，并确认在 runtime 依赖组中",
            )
    else:
        finding.add(PASS, f"全部 {len(probes)} 个关键依赖可导入")
    return finding


# ==================== C6 环境变量校验 ====================

def check_env(repo_root: Path = REPO_ROOT) -> Finding:
    finding = Finding("C6", "环境变量校验")
    env_path = repo_root / "config" / ".env"
    if not env_path.exists():
        finding.add(FAIL, "config/.env 不存在（API key 全缺 → AI 静默降级）", "从 .env.example 恢复并填入密钥")
        return finding
    env = _parse_env(env_path)
    for key, severity in REQUIRED_ENV_KEYS.items():
        if not env.get(key):
            finding.add(
                severity,
                f".env 缺少 {key}" + ("（模型池将全部禁用 → AI 降级假活）" if severity == FAIL else ""),
                f"在 config/.env 中配置 {key}",
            )
    if not finding.details:
        finding.add(PASS, f".env 存在，{len(REQUIRED_ENV_KEYS)} 个必需键齐全")
    return finding


# ==================== C7 权限配置校验 ====================

def check_permissions(repo_root: Path = REPO_ROOT) -> Finding:
    finding = Finding("C7", "权限配置校验")
    path = repo_root / "config" / "permissions.json"
    if not path.exists():
        finding.add(FAIL, "permissions.json 不存在（fail-closed 全拒）", "从 git 恢复")
        return finding
    try:
        cfg = _load_json(path)
    except Exception as e:  # noqa: BLE001 — 语法错误由 C2 报告
        finding.add(FAIL, f"解析失败: {e}")
        return finding

    superadmins = cfg.get("superadmins", {})
    if not superadmins:
        finding.add(FAIL, "superadmins 为空（无超管，所有者将被 fail-closed 拒绝）", "配置 superadmins.ids")
    groups = cfg.get("permission_groups", {})
    if "Default" not in groups:
        finding.add(WARN, "permission_groups 缺少 Default 组（未知用户将无任何权限）", "补充 Default 组")
    if not isinstance(cfg.get("users", []), list):
        finding.add(WARN, "users 不是列表（权限引擎按列表遍历）")

    if not finding.details:
        finding.add(PASS, f"权限配置正常（{len(superadmins)} 个超管，{len(groups)} 个权限组）")
    return finding


# ==================== C8 运行时诊断 ====================

def check_runtime(
    since: str = "10 minutes ago",
    health_url: str = "http://127.0.0.1:9800/api/v1/health",
    repo_root: Path = REPO_ROOT,
) -> Finding:
    """运行时诊断：健康端点 + journalctl 错误签名 + crash-loop（需 systemd 环境）"""
    finding = Finding("C8", "运行时诊断")

    # 1) 健康端点
    try:
        with urllib.request.urlopen(health_url, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if resp.status == 200:
            degraded = (
                ((body.get("daemon_status") or {}).get("degraded") or {}).get("ai_client"),
                body.get("degraded", {}).get("ai_client") if isinstance(body.get("degraded"), dict) else None,
            )
            if any(degraded):
                finding.add(FAIL, "健康端点报告 degraded.ai_client=true（AI 已降级假活）", "检查 API key 与模型池")
            else:
                finding.details.append(f"健康端点 200（status={body.get('status', 'ok')}）")
        else:
            finding.add(FAIL, f"健康端点 HTTP {resp.status}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        finding.add(FAIL, f"健康端点不可达（{health_url}）: {e}", "确认服务运行与端口")

    # 2) journalctl 错误签名（仅 systemd 环境）
    if not shutil.which("journalctl"):
        finding.add(SKIP, "非 systemd 环境，跳过日志扫描")
        return finding

    try:
        proc = subprocess.run(
            ["journalctl", "-u", "miya-daemon", "--since", since, "--no-pager", "-o", "short-iso"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        log_lines = proc.stdout.splitlines()
    except (subprocess.TimeoutExpired, OSError) as e:
        finding.add(WARN, f"journalctl 读取失败: {e}")
        return finding

    text = "\n".join(log_lines)
    for pattern, threshold, severity, desc in RUNTIME_ERROR_SIGNATURES:
        hits = re.findall(pattern, text)
        if len(hits) >= threshold:
            sample = hits[0] if isinstance(hits[0], str) else ""
            finding.add(
                severity,
                f"日志签名 '{pattern}' 命中 {len(hits)} 次（阈值 {threshold}）— {desc}，样例: {sample[:60]}",
                "定位对应日志上下文并修复",
            )

    # 3) crash-loop：窗口内 systemd 重启次数
    restarts = text.count("Started miya-daemon.service")
    if restarts >= CRASH_LOOP_THRESHOLD:
        finding.add(
            FAIL,
            f"crash-loop 疑似: 窗口 '{since}' 内服务重启 {restarts} 次（阈值 {CRASH_LOOP_THRESHOLD}）",
            "检查启动期日志的守护进程异常",
        )

    # 4) NapCat 反向 WS 桥接：服务运行中但连接断开 = 消息黑洞（NapCat 客户端弃连后
    #    弥娅侧仅监听仍显示 online，此断裂曾 11 小时无人发现）。
    #    判定依据是最后一个事件：断开在最后 = 当前断裂（FAIL）；连接在最后 = 正常
    disconnect_positions = [m.start() for m in re.finditer(r"NapCat 断开", text)]
    connect_positions = [m.start() for m in re.finditer(r"NapCat 已连接", text)]
    if disconnect_positions and (not connect_positions or disconnect_positions[-1] > connect_positions[-1]):
        finding.add(
            FAIL,
            f"NapCat 反向 WS 断开（最后事件为断开，窗口 '{since}'）——当前消息无法到达，尝试 docker restart napcat",
            "重启 NapCat 容器恢复反向 WS 桥接",
        )
    elif connect_positions:
        finding.details.append(f"NapCat 桥接正常（窗口内最近一次连接位于断开之后或无断开记录）")
    # 无任何连接/断开记录：可能是纯空闲窗口，不判定

    if not [d for d in finding.details if d.startswith("[")]:
        finding.add(PASS, f"运行时正常（{len(log_lines)} 行日志扫描无超阈值错误签名）")
    return finding


# ==================== C9 记忆一致性 ====================

def check_memory(fix: bool = False, repo_root: Path = REPO_ROOT) -> Finding:
    """复用 scripts/check_memory_consistency.py（--fix 传递自校正）"""
    finding = Finding("C9", "记忆一致性")
    script = repo_root / "scripts" / "check_memory_consistency.py"
    if not script.exists():
        finding.add(SKIP, "scripts/check_memory_consistency.py 不存在，跳过")
        return finding
    cmd = [sys.executable, str(script)]
    if fix:
        cmd.append("--fix")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(repo_root))
    except (subprocess.TimeoutExpired, OSError) as e:
        finding.add(WARN, f"记忆一致性检查执行失败: {e}")
        return finding
    if proc.returncode == 0:
        finding.details.append("记忆双库一致" + ("（已自校正）" if fix else ""))
    else:
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-5:]
        finding.add(FAIL, f"记忆一致性检查失败（exit={proc.returncode}）: {' | '.join(tail)}", "运行 --fix 或按脚本输出修复")
    return finding


# ==================== 聚合入口 ====================

def run_static_checks(repo_root: Path = REPO_ROOT) -> list:
    """静态检查（C1-C7），CI / 本地 / 启动预检可用"""
    return [
        check_dead_config(repo_root),
        check_config_parse(repo_root),
        check_model_config(repo_root),
        check_prompt_placeholders(repo_root),
        check_dependencies(),
        check_env(repo_root),
        check_permissions(repo_root),
    ]


def run_preflight(repo_root: Path = REPO_ROOT) -> list:
    """启动预检快速子集（daemon 启动早期调用，告警不阻断）"""
    return [
        check_config_parse(repo_root),
        check_model_config(repo_root),
        check_env(repo_root),
    ]


def summarize(findings: list) -> dict:
    counts = {PASS: 0, WARN: 0, FAIL: 0, SKIP: 0}
    for f in findings:
        counts[f.status] = counts.get(f.status, 0) + 1
    return counts


def has_failures(findings: list) -> bool:
    return any(f.status == FAIL for f in findings)
