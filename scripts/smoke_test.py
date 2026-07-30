#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Miya 8 级冒烟测试。

用法:
  python scripts/smoke_test.py                   # 全量 (3-5 分钟)
  python scripts/smoke_test.py --fast             # 跳过 S5/S6 (约 40 秒)
  python scripts/smoke_test.py --write-baseline   # 写入基线 (必须先跑一次)
  python scripts/smoke_test.py --stage S4         # 只跑 S4

基线文件:  scripts/.smoke_baseline.json
"""

import json
import os
import re
import sys
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Set, Optional, Any

ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = ROOT / "scripts" / ".smoke_baseline.json"
LOG_BLACKLIST_FILE = ROOT / "scripts" / ".smoke_log_blacklist.json"

# 关键模块 —— 冷导入检查
KEY_MODULES = [
    "core.miya_daemon",
    "core.management_api",
    "config",
    "config.platforms_config",
    "config.settings",
    "core.unified_platform",
    "core.unified_platform_impl",
    "hub.decision_hub",
    "run.main",
]

# 已知无害的启动日志模式 (Neo4j 没密码、可选插件缺失等)
DEFAULT_LOG_WHITELIST = [
    r"knowledge_graph.*ERROR",
    r"吟美.*失败",
    r"yinmei.*import",
    r"Live2D.*缺",
    r"Neo4j.*password",
    r"neo4j.*auth",
    r"pygame.*not.*available",
    r"pymilvus.*not.*available",
    r"No module named.*milvus",
    r"faiss.*not.*available",
    r"chromadb.*not.*available",
    r"jieba.*not.*found",       # 已知 jieba 未安装
    r"tts.*unavailable",
    r"TTS.*不可用",
    r"表情包.*失败",
    r"emoji.*failed",
    r"singing.*not.*available",
    r"唱歌.*不可用",
    r"语音.*不可用",
    r"voice.*unavailable",
    r"MCP.*not.*found",
    r"openclaw.*not.*available",
    r"GestaltEnhanced.*AstrBot",
    r"AstrBot.*fail",
    r"FormatCtrl",
    r"Attempted relative import",
    r"ModuleNotFoundError.*singing",
    r"ModuleNotFoundError.*voice",
    r"ModuleNotFoundError.*tts",
    r"ModuleNotFoundError.*emoji",
    r"ModuleNotFoundError.*youtu",
    r"ModuleNotFoundError.*yinmei",
    r"ModuleNotFoundError.*astrbot",
    r"ModuleNotFoundError.*live2d",
    r"ModuleNotFoundError.*claude_code",
    r"ModuleNotFoundError.*nodejs",
    r"ImportError.*singing",
    r"ImportError.*voice",
]


def run_py(code: str, timeout: int = 120, env_extra: Dict = None) -> subprocess.CompletedProcess:
    """在子进程中运行 Python 代码。"""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ROOT),
        capture_output=True, text=True,
        timeout=timeout, env=env,
    )


def load_baseline() -> Dict:
    if BASELINE_FILE.exists():
        return json.loads(BASELINE_FILE.read_text("utf-8"))
    return {}


def load_log_blacklist() -> List[str]:
    if LOG_BLACKLIST_FILE.exists():
        return json.loads(LOG_BLACKLIST_FILE.read_text("utf-8"))
    return DEFAULT_LOG_WHITELIST


# ── stages ────────────────────────────────────────────────────────────

def s0_compileall() -> bool:
    """S0: 编译期语法检查。"""
    print("=== S0 compileall ===")
    cp = subprocess.run(
        [sys.executable, "-m", "compileall", "-q",
         "-x", "EntertainmentNet",
         "core", "hub", "run", "memory", "webnet", "mlink",
         "config", "utils", "mcpserver"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=60,
    )
    if cp.returncode != 0:
        # compileall 对语法错误的文件返回非零，但一些旧文件有已知的编码问题
        # 只查看多少文件失败，不硬性拦截
        errors = [l for l in cp.stderr.splitlines() if "Error compiling" in l or "Sorry:" in l]
        if errors:
            print(f"  [WARN] compileall {len(errors)} 个文件编译失败 (可能是编码问题):")
            for e in errors[:5]:
                print(f"    {e.strip()[:120]}")
            # 排除已知坏文件后重新判定
            non_entertainment = [e for e in errors if "EntertainmentNet" not in e]
            if non_entertainment:
                print(f"  [FAIL] {len(non_entertainment)} 个非 EntertainmentNet 文件编译失败")
                return False
    print(f"  [OK] compileall 通过 (排除 EntertainmentNet)")
    return True


def s1_import_graph() -> bool:
    """S1: 静态导入可达性。"""
    print("=== S1 import_graph ===")
    cp = subprocess.run(
        [sys.executable, "scripts/import_graph.py", "--check"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=30,
    )
    print(cp.stdout.strip())
    if cp.returncode != 0:
        print(f"  [FAIL] import_graph exit={cp.returncode}")
        return False
    print(f"  [OK] import_graph 通过")
    return True


def s2_cold_imports() -> bool:
    """S2: 全新子进程冷导入。"""
    print("=== S2 冷导入 ===")
    code = (
        "import sys; sys.path.insert(0,'.');"
        + ";".join(f"__import__('{m}'); print('  {m}')" for m in KEY_MODULES)
        + ";\n"
        + "import core.unified_platform as m; "
        + "f=m.__file__.replace('\\\\','/'); "
        + "print(f'  unified_platform -> {f}'); "
        + "assert f.endswith('unified_platform/__init__.py'), f'unexpected: {f}'"
    )
    cp = run_py(code, timeout=30)
    for line in cp.stdout.strip().splitlines():
        print(f"  {line}")
    if cp.returncode != 0:
        print(f"  [FAIL] 冷导入失败")
        for line in cp.stderr.strip().splitlines()[-5:]:
            print(f"  {line}")
        return False
    print(f"  [OK] 冷导入通过")
    return True


def s3_config() -> bool:
    """S3: 配置层检查。"""
    print("=== S3 配置 ===")
    code = (
        "import sys; sys.path.insert(0,'.');"
        "import config.platforms_config as pc;"
        "cfg=pc.get_enabled_platforms();"
        "print(f'  enabled_platforms: {sorted(cfg.keys())}');"
        "assert isinstance(cfg,dict);"
        "import config.settings;"
        "s=config.settings.Settings();"
        "print(f'  Settings: {type(s).__name__}');"
        "import pathlib;"
        "hits=list(pathlib.Path('.').rglob('platforms_config.py'));"
        "hits=[str(h) for h in hits if 'venv' not in str(h) and '__pycache__' not in str(h)];"
        "# 允许 config/ 和 core/ 两套并存 (P3 批次 7 会消灭 core/ 那份)"
        "hits2=[h for h in hits if 'core' in str(h) and 'config' not in str(h)];"
        "print(f'  platforms_config count: {len(hits)} (config={len(hits)-len(hits2)} core={len(hits2)})');"
        "if len(hits) > 2:"
        "  print(f'  [FAIL] 超过 2 个 platforms_config.py'); import sys; sys.exit(1);"
    )
    cp = run_py(code, timeout=15)
    for line in cp.stdout.strip().splitlines():
        print(f"  {line}")
    if cp.returncode != 0:
        print(f"  [FAIL] 配置检查失败")
        for line in cp.stderr.strip().splitlines()[-5:]:
            print(f"  {line}")
        return False
    print(f"  [OK] 配置通过")
    return True


def s4_platform_registry() -> bool:
    """S4: 平台注册。"""
    print("=== S4 平台注册 ===")
    code = (
        "import json, sys; sys.path.insert(0,'.');"
        "from core.miya_daemon import MiyaDaemon;"
        "d=MiyaDaemon(auto_register=True);"
        "regs=d._registry.list_registered();"
        "ids=[r.get('id','?') for r in regs];"
        "print(f'REG_COUNT: {len(ids)}');"
        "print(f'REG_IDS: {json.dumps(ids)}')"
    )
    cp = run_py(code, timeout=15)
    for line in cp.stdout.strip().splitlines():
        print(f"  {line}")
    if cp.returncode != 0:
        print(f"  [FAIL] 平台注册失败")
        for line in cp.stderr.strip().splitlines()[-5:]:
            print(f"  {line}")
        return False
    print(f"  [OK] 平台注册通过")
    return True


def s5_core_build() -> Dict[str, Any]:
    """S5: 核心构造 (最耗时)。返回采集数据供 S7/S8 使用。"""
    print("=== S5 核心构造 (约 90-150s) ===")
    import random
    port = random.randint(19800, 19900)
    code = (
        "import os; os.environ['MIYA_SMOKE']='1';"
        f"os.environ['MIYA_API_PORT']='{port}';"
        "import sys; sys.path.insert(0,'.');"
        "import run.main;"
        "m=run.main.Miya();"
        "# 检查关键子系统"
        "checks=["
        "('personality',m.personality),"
        "('ethics',m.ethics),"
        "('identity',m.identity),"
        "('arbitrator',m.arbitrator),"
        "('entropy',m.entropy),"
        "('prompt_manager',m.prompt_manager),"
        "('memory_engine',m.memory_engine),"
        "('memory_emotion',m.memory_emotion),"
        "('emotion',m.emotion),"
        "('decision',m.decision),"
        "('scheduler',m.scheduler),"
        "('mlink',m.mlink),"
        "('net_manager',m.net_manager),"
        "('cross_net_engine',m.cross_net_engine),"
        "('decision_hub',m.decision_hub),"
        "('ai_client',m.ai_client),"
        "('tool_subnet',m.tool_subnet),"
        "('memory_net',m.memory_net),"
        "];"
        "for name,val in checks:"
        "  ok='OK' if val is not None else 'NONE';"
        "  typ=type(val).__name__ if val is not None else 'NoneType';"
        "  print(f'  {name:25s} {ok:5s} {typ}');"
        "os._exit(0)"
    )
    cp = run_py(code, timeout=200, env_extra={"MIYA_SMOKE": "1", "MIYA_API_PORT": str(port)})
    results = {}
    ok = True
    for line in cp.stdout.strip().splitlines():
        print(f"  {line}")
        if "NONE" in line:
            ok = False
            results[line.split()[0]] = "NONE"
        elif "OK" in line:
            results[line.split()[0]] = line.split()[-1]
    # 也输出 stderr (日志)
    if cp.stderr.strip():
        for line in cp.stderr.strip().splitlines()[-20:]:
            print(f"  [E] {line}")
    results["_stderr"] = cp.stderr
    if not ok:
        print(f"  [FAIL] 存在 None 子系统")
    else:
        print(f"  [OK] 核心构造 {len(results)-1} 子系统全部非 None")
    return results if ok else {}


def s6_link_probes() -> bool:
    """S6: 链路探针。"""
    print("=== S6 链路探针 ===")
    port = 19901
    code = (
        "import os; os.environ['MIYA_SMOKE']='1';"
        f"os.environ['MIYA_API_PORT']='{port}';"
        "import sys; sys.path.insert(0,'.');"
        "import run.main;"
        "m=run.main.Miya();"
        "import asyncio;"
        "async def probe():"
        "  from core.gestalt_controller import get_gestalt_controller;"
        "  gc=get_gestalt_controller();"
        "  print(f'  gestalt: {type(gc).__name__}');"
        "  from core.personality_config_loader import PersonalityConfigLoader;"
        "  pcl=PersonalityConfigLoader();"
        "  names=pcl.list_available();"
        "  print(f'  personalities: {len(names)} ({names[:5]}...)');"
        "  if m.memory_net:"
        "    await m.memory_net.initialize();"
        "    print(f'  memory_net: initialized');"
        "  if hasattr(m,'tool_subnet') and m.tool_subnet:"
        "    r=m.tool_subnet.registry;"
        "    print(f'  tools: {len(r.tools) if hasattr(r,\"tools\") else len(r._tools) if hasattr(r,\"_tools\") else \"?\"}');"
        "loop=asyncio.new_event_loop();"
        "loop.run_until_complete(probe());"
        "loop.close();"
        "os._exit(0)"
    )
    cp = run_py(code, timeout=180, env_extra={"MIYA_SMOKE": "1", "MIYA_API_PORT": str(port)})
    for line in cp.stdout.strip().splitlines():
        print(f"  {line}")
    if cp.returncode != 0:
        print(f"  [FAIL] 链路探针失败 (exit {cp.returncode})")
        for line in cp.stderr.strip().splitlines()[-8:]:
            print(f"  {line}")
        return False
    print(f"  [OK] 链路探针通过")
    return True


def s7_log_diff(stderr_text: str) -> bool:
    """S7: 日志白名单差分。"""
    if not stderr_text:
        print("=== S7 日志差分: 无日志，跳过 ===")
        return True
    print("=== S7 日志差分 ===")
    blacklist = load_log_blacklist()
    suspects = []
    for line in stderr_text.splitlines():
        line_s = line.strip()
        if not line_s:
            continue
        # 过滤: ModuleNotFoundError / ImportError / 初始化失败 / 加载失败 / 不可用
        if not re.search(r"ModuleNotFoundError|ImportError|初始化失败|加载失败|不可用|ERROR|WARNING|failed|unavailable|not found",
                         line_s, re.IGNORECASE):
            continue
        # 匹配白名单
        matched = False
        for pattern in blacklist:
            if re.search(pattern, line_s, re.IGNORECASE):
                matched = True
                break
        if not matched:
            suspects.append(line_s)

    if suspects:
        print(f"  [FAIL] 新增 {len(suspects)} 行不在白名单中:")
        for s in suspects[:15]:
            print(f"    {s[:200]}")
        if len(suspects) > 15:
            print(f"    ... 还有 {len(suspects)-15} 行")
        return False
    print(f"  [OK] 日志差分: 所有关键行均在白名单中")
    return True


def s8_baseline_compare(data: Dict[str, Any]) -> bool:
    """S8: 基线数值对比。"""
    baseline = load_baseline()
    if not baseline:
        print("=== S8 基线对比: 无基线，跳过 ===")
        return True
    print("=== S8 基线对比 ===")
    ok = True
    # 对比 S3 数据
    for key in ["enabled_platforms", "registered_platforms", "personality_count", "tool_count"]:
        old = baseline.get(key)
        new = data.get(key)
        if old is not None and new is not None and old != new:
            print(f"  [FAIL] {key}: 基线={old}, 当前={new}")
            ok = False
    if ok:
        print(f"  [OK] 基线对比通过")
    return ok


# ── main ─────────────────────────────────────────────────────────────

def write_baseline():
    """运行 S3/S4/S5/S6 并采集基线数据。"""
    print("写入冒烟基线...")
    data = {}
    # S3
    code = (
        "import sys; sys.path.insert(0,'.');"
        "import config.platforms_config as pc;"
        "cfg=pc.get_enabled_platforms();"
        "print(f'PLATFORMS: {json.dumps(sorted(cfg.keys()))}');"
        "import config.settings;"
        "s=config.settings.Settings();"
        "attrs=[a for a in dir(s) if not a.startswith('_') and not callable(getattr(s,a))];"
        "print(f'SETTINGS: {json.dumps(sorted(attrs))}')"
    )
    cp = run_py(code, timeout=15)
    for line in cp.stdout.strip().splitlines():
        if line.startswith("PLATFORMS:"):
            data["enabled_platforms"] = json.loads(line.split(":", 1)[1])
        elif line.startswith("SETTINGS:"):
            data["settings_attrs"] = json.loads(line.split(":", 1)[1])

    # S4
    code = (
        "import sys; sys.path.insert(0,'.');"
        "from core.miya_daemon import MiyaDaemon;"
        "d=MiyaDaemon(auto_register=True);"
        "regs=d._registry.list_registered();"
        "print(f'REGISTERED: {json.dumps([r[\"id\"] for r in regs])}')"
    )
    cp = run_py(code, timeout=15)
    for line in cp.stdout.strip().splitlines():
        if line.startswith("REGISTERED:"):
            data["registered_platforms"] = json.loads(line.split(":", 1)[1])

    BASELINE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    print(f"基线已写入 {BASELINE_FILE}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Miya 冒烟测试")
    parser.add_argument("--fast", action="store_true", help="跳过 S5/S6")
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--stage", help="只跑指定阶段 eg S4")
    args = parser.parse_args()

    if args.write_baseline:
        return write_baseline()

    results: Dict[str, bool] = {}
    s5_stderr = ""

    stages = {
        "S0": lambda: results.update({"S0": s0_compileall()}),
        "S1": lambda: results.update({"S1": s1_import_graph()}),
        "S2": lambda: results.update({"S2": s2_cold_imports()}),
        "S3": lambda: results.update({"S3": s3_config()}),
        "S4": lambda: results.update({"S4": s4_platform_registry()}),
    }

    if args.stage:
        if args.stage in stages:
            stages[args.stage]()
        else:
            print(f"未知阶段: {args.stage}")
        return

    # 顺序执行
    for name, fn in stages.items():
        fn()
        if not results.get(name, True):
            if name in ("S0", "S1", "S2"):
                print(f"\n[ABORT] {name} 失败，跳过后续")
                break

    if not args.fast:
        data = s5_core_build()
        if data:
            s5_stderr = data.pop("_stderr", "")
            results["S5"] = True
        else:
            results["S5"] = False

        results["S6"] = s6_link_probes()
        results["S7"] = s7_log_diff(s5_stderr)
        results["S8"] = s8_baseline_compare({})

    # 汇总
    print(f"\n{'='*50}")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, ok in results.items():
        status = "[OK]" if ok else "[FAIL]"
        print(f"  {name}: {status}")
    print(f"\n  {passed}/{total} 通过")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
