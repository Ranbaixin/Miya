#!/usr/bin/env python3
"""
Miya 静态导入可达性分析 —— 删除裁决器。

用法:
  python scripts/import_graph.py --write-baseline    # 建基线
  python scripts/import_graph.py --check             # 每批删除后跑，exit != 0 即拦截
  python scripts/import_graph.py --unreachable       # 列出候选死模块
  python scripts/import_graph.py --shadowed          # 列出同名遮蔽

设计要点:
  - ast.walk 进入 try 块 / 函数体 / 循环体 —— 藏在深处的 import 也会被收集
  - resolve() 复刻 CPython FileFinder 顺序：包(目录 __init__.py) 优先于同名模块(.py)
  - 硬引用: import / from-import / importlib.import_module(常量)
  - 软引用: 匹配本地模块命名规则的字符串常量 (仅 warn)
"""

# -*- coding: utf-8 -*-
import ast
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = ROOT / "scripts" / ".import_baseline.json"

# 只扫描这些顶层包下的 import
LOCAL_TOPS = {"core", "hub", "memory", "webnet", "mlink", "run", "config",
              "utils", "mcpserver", "plugins", "astrbot"}

# 模块可达性扫描起点
ROOTS = [
    "run.daemon",
    "run.main",
    "core.management_api",
    "core.miya_daemon",
    "core.web_api",
    "core.web_api.miya_api",
    "core.unified_platform",
    "core.unified_platform_impl",
    "core.gestalt_controller",
    "hub.decision_hub",
    "mlink.mlink_core",
    "memory.core",
    "webnet",
    "config.settings",
    "config.platforms_config",
]


def _parse_spec_hiddenimports(spec_path: Path) -> List[str]:
    """从 Miya.spec 提取 hiddenimports 列表 (作为额外 ROOTS)。"""
    if not spec_path.exists():
        return []
    imports = []
    in_hidden = False
    for line in spec_path.read_text("utf-8").splitlines():
        stripped = line.strip()
        if "hiddenimports=[" in stripped:
            in_hidden = True
            continue
        if in_hidden:
            if "]," in stripped or stripped == "],":
                break
            # 提取 'xxx' 或 "xxx"
            for q in ('"', "'"):
                if q in stripped:
                    seg = stripped.split(q)[1]
                    if "." in seg:
                        imports.append(seg)
    return imports


class ImportGraph:
    def __init__(self):
        self._file_index: Dict[str, Path] = {}        # dotted -> absolute path
        self._shadowed: Dict[str, Tuple[Path, Path]] = {}  # name -> (pkg_path, mod_path)
        self._build_file_index()

    # ── file index ──────────────────────────────────────────────

    def _build_file_index(self):
        """扫描磁盘，建立 模块名 → 文件路径 的映射。

        关键: 先扫描包(目录 __init__.py)，后扫描单文件模块(.py)。
        同名时包优先（复刻 CPython FileFinder 行为），
        并将被遮蔽的 .py 记入 _shadowed。
        """
        pkg_seen: Set[str] = set()

        for pyfile in sorted(ROOT.rglob("*.py")):
            rel = pyfile.relative_to(ROOT)
            parts = list(rel.parts)
            # 跳过非本地包的目录
            if parts[0] not in LOCAL_TOPS and not any(p in LOCAL_TOPS for p in parts[:3]):
                continue
            # 跳过 venv / node_modules / .git / __pycache__
            if any(s in parts for s in ("venv", "node_modules", ".git", "__pycache__",
                                         "site-packages", "dist-packages")):
                continue

            if parts[-1] == "__init__.py":
                # 包: a/b/__init__.py → a.b
                dotted = ".".join(parts[:-1])
                pkg_seen.add(dotted)
                self._file_index[dotted] = pyfile
            else:
                # 单文件模块: a/b/c.py → a.b.c
                dotted = ".".join(parts[:-1] + [parts[-1][:-3]])  # strip .py
                if dotted in pkg_seen:
                    # 同名包已占据这个命名空间 → 此模块被遮蔽
                    self._shadowed[dotted] = (self._file_index[dotted], pyfile)
                    continue
                # 如果同名 .py 先于包被索引 (不存在此情况，因为 sorted 保证 pkg 先扫)
                self._file_index[dotted] = pyfile

    def resolve(self, dotted: str) -> Optional[Path]:
        """复刻 CPython 导入解析: 返回磁盘路径或 None。"""
        if dotted in self._file_index:
            return self._file_index[dotted]

        # 尝试作为包导入: foo.bar → foo/bar/__init__.py
        parts = dotted.split(".")
        pkg_path = ROOT / "/".join(parts) / "__init__.py"
        if pkg_path.exists():
            return pkg_path
        # 尝试作为模块导入: foo.bar → foo/bar.py
        mod_path = ROOT / ("/".join(parts) + ".py")
        if mod_path.exists():
            return mod_path
        return None

    # ── scanning ─────────────────────────────────────────────────

    def scan_file(self, filepath: Path) -> Tuple[Set[str], Set[str]]:
        """AST 扫描单个 .py 文件，返回 (硬引用集合, 软引用集合)。

        硬引用: import / from-import / importlib.import_module(字面量)
        软引用: 匹配 ^(core|hub|webnet|memory|mlink|config)\\.[\\w.]+$ 的字符串常量
        """
        hard: Set[str] = set()
        soft: Set[str] = set()

        try:
            tree = ast.parse(filepath.read_text("utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            return hard, soft

        for node in ast.walk(tree):  # walk 进入所有子节点 (含 try/函数体)
            # from X import Y
            if isinstance(node, ast.ImportFrom):
                if node.module is not None and node.level == 0:
                    hard.add(node.module)

            # import X
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    hard.add(alias.name)

            # importlib.import_module("xxx") / __import__("xxx")
            elif (isinstance(node, ast.Call) and
                  isinstance(node.func, ast.Attribute) and
                  node.func.attr in ("import_module",)):
                if node.args and isinstance(node.args[0], ast.Constant):
                    if isinstance(node.args[0].value, str):
                        hard.add(node.args[0].value)

            # 字符串常量 —— 可能包含模块引用
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                v = node.value
                if v.count(".") >= 1 and any(
                    v.startswith(top + ".") for top in LOCAL_TOPS
                ):
                    # 只匹配合理的模块命名 (不含空格/换行/特殊字符)
                    if " " not in v and "\n" not in v and len(v) < 120:
                        soft.add(v)

        return hard, soft

    # ── reachability ─────────────────────────────────────────────

    def reachable_from(self, roots: List[str]) -> Set[str]:
        """BFS 从 roots 出发，返回可达的本地模块名集合。"""
        queue = list(roots)
        visited: Set[str] = set()
        hard_dangling: Set[str] = set()

        while queue:
            name = queue.pop(0)
            if name in visited:
                continue

            path = self.resolve(name)
            if path is None:
                # 检查是不是外部包 —— 只要顶层不在 LOCAL_TOPS 里就算外部
                top = name.split(".")[0]
                if top in LOCAL_TOPS:
                    hard_dangling.add(name)
                visited.add(name)
                continue

            visited.add(name)
            hard, _soft = self.scan_file(path)

            for h in hard:
                # 只追踪本地包内的引用 (外部包不需要文件存在)
                top = h.split(".")[0]
                if top in LOCAL_TOPS and h not in visited:
                    queue.append(h)

        return visited, hard_dangling

    # ── reports ──────────────────────────────────────────────────

    def all_on_disk(self) -> Set[str]:
        """返回磁盘上所有本地模块名。"""
        return set(self._file_index.keys())

    def unreachable(self, roots: List[str] = None) -> Set[str]:
        """返回 ROOTS 不可达的本地模块。"""
        if roots is None:
            roots = ROOTS
        reached, _ = self.reachable_from(roots)
        return self.all_on_disk() - reached

    # ── CLI ──────────────────────────────────────────────────────

    def cmd_write_baseline(self):
        reached, dangling = self.reachable_from(ROOTS)
        if dangling:
            print("[WARN]  基线发现悬空引用:")
            for d in sorted(dangling):
                print(f"  {d}")
            print()

        spec = _parse_spec_hiddenimports(ROOT / "Miya.spec")
        data = {
            "reachable": sorted(reached),
            "count": len(reached),
            "dangling": sorted(dangling),
            "shadowed": {k: [str(p) for p in v] for k, v in sorted(self._shadowed.items())},
            "spec_hiddenimports": spec,
        }
        BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
        print(f"基线已写入 {BASELINE_FILE}")
        print(f"  可达: {len(reached)} | 悬空: {len(dangling)} | 遮蔽: {len(self._shadowed)} | spec hiddenimports: {len(spec)}")
        if self._shadowed:
            print("\n[WARN]  同名遮蔽:")
            for name, (pkg, mod) in sorted(self._shadowed.items()):
                print(f"  {name}: 包 {pkg} 遮蔽了模块 {mod}")

    def cmd_check(self) -> int:
        """返回 exit code: 0=通过, 1=基线缺失, 2=悬空引用, 3=可达集漂移, 4=遮蔽变更"""
        if not BASELINE_FILE.exists():
            print("[FAIL] 基线文件不存在，请先运行 --write-baseline")
            return 1

        baseline = json.loads(BASELINE_FILE.read_text("utf-8"))

        reached, dangling = self.reachable_from(ROOTS)
        errors = 0

        # 1) 悬空引用 —— 只报新增的 (基线里已记录的是存量问题)
        old_dangling = set(baseline.get("dangling", []))
        new_dangling = dangling - old_dangling
        if new_dangling:
            print(f"[FAIL] 新增 {len(new_dangling)} 个悬空引用:")
            for d in sorted(new_dangling):
                print(f"  {d}")
            errors += 1
        elif dangling:
            print(f"[INFO] 现存 {len(dangling)} 个悬空引用 (与基线一致)")

        # 2) 可达集缩小 (被误删了)
        bset = set(baseline["reachable"])
        lost = bset - reached
        if lost:
            print(f"[FAIL] 可达集缩小 {len(lost)} 项 (可能误删了模块):")
            for m in sorted(lost)[:20]:
                print(f"  {m}")
            if len(lost) > 20:
                print(f"  ... 还有 {len(lost)-20} 项")
            errors += 1

        # 3) 可达集扩大 (意外接线了)
        gained = reached - bset
        if gained:
            print(f"[WARN]  可达集扩大 {len(gained)} 项 (新增依赖):")
            for m in sorted(gained)[:20]:
                print(f"  {m}")
            if len(gained) > 20:
                print(f"  ... 还有 {len(gained)-20} 项")
            # 扩大不算硬错误，只 warn

        # 4) 同名遮蔽变更
        old_shadowed = set(baseline.get("shadowed", {}).keys())
        new_shadowed = set(self._shadowed.keys())
        if old_shadowed != new_shadowed:
            gone = old_shadowed - new_shadowed
            added = new_shadowed - old_shadowed
            if gone:
                print(f"[WARN]  遮蔽消失 {len(gone)} 处: {', '.join(sorted(gone))}")
            if added:
                print(f"[FAIL] 新增遮蔽 {len(added)} 处: {', '.join(sorted(added))}")
                errors += 1

        if errors == 0:
            print(f"[OK] 导入图通过: {len(reached)} 可达, 0 悬空, 遮蔽 {len(self._shadowed)} 处")
        return 2 if errors > 0 else 0

    def cmd_unreachable(self):
        unreach = self.unreachable(ROOTS)
        if not unreach:
            print("所有本地模块均可达。")
            return
        # 只显示有意义的 (排除 tests, scripts, build_release 等非库代码)
        filtered = {m for m in unreach
                    if m.split(".")[0] in LOCAL_TOPS
                    and not m.startswith("tests.")
                    and m not in ("build_release",)}
        print(f"不可达模块: {len(filtered)} 个")
        for m in sorted(filtered):
            p = self.resolve(m)
            if p:
                try:
                    lines = len(p.read_text("utf-8").splitlines())
                    print(f"  {m:60s} {lines:>6d} 行  {p}")
                except Exception:
                    print(f"  {m}")

    def cmd_shadowed(self):
        if not self._shadowed:
            print("无同名遮蔽。")
            return
        for name, (pkg, mod) in sorted(self._shadowed.items()):
            print(f"  {name}")
            print(f"    包(优先):  {pkg}")
            print(f"    模块(遮蔽): {mod}")


def main():
    parser = argparse.ArgumentParser(description="Miya 静态导入可达性分析")
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--unreachable", action="store_true")
    parser.add_argument("--shadowed", action="store_true")
    args = parser.parse_args()

    g = ImportGraph()

    if args.write_baseline:
        g.cmd_write_baseline()
    elif args.check:
        sys.exit(g.cmd_check())
    elif args.unreachable:
        g.cmd_unreachable()
    elif args.shadowed:
        g.cmd_shadowed()
    else:
        # 默认: 打印统计
        reached, dangling = g.reachable_from(ROOTS)
        all_mods = g.all_on_disk()
        print(f"磁盘模块: {len(all_mods)}")
        print(f"可达模块: {len(reached)}")
        print(f"不可达:   {len(all_mods - reached)}")
        print(f"悬空引用: {len(dangling)}")
        print(f"同名遮蔽: {len(g._shadowed)}")
        if g._shadowed:
            for name in sorted(g._shadowed):
                print(f"  ⚠ {name} 被包遮蔽")


if __name__ == "__main__":
    main()
