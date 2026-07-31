#!/usr/bin/env python3
"""P9 Sprint 1 invariants gate — 只查 diff 新增的异常吞噬违规。

用法:
    uv run python scripts/check_new_swallowed.py            # 默认基准 HEAD~1
    uv run python scripts/check_new_swallowed.py <base_sha> # 指定基准（CI 传 PR base sha）

流程:
    1. 找出基准之后新增/复制/修改/重命名的 .py 文件
    2. 解析每个文件 diff 的「新增行」行号集合
    3. 临时禁用 per-file-ignores，对改动文件跑 ruff（S110/S112/BLE001/E722）
    4. 只保留落在新增行上的违规；存在则打印并 exit 1，否则 exit 0

设计意图:
    存量违规已被 pyproject.toml 的 [tool.ruff.lint.per-file-ignores] 一次性豁免，
    因此全仓 ruff 检查无法发现「已豁免文件新增的违规」。本脚本把检查范围收敛到
    diff 实际新增的行，堵住这个缺口（豁免表只减不增由本 gate 保证）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

# Windows 控制台默认 cp936，强制 UTF-8 输出，避免中文乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

RULES = "S110,S112,BLE001,E722"

# ruff 的 json 输出中 filename 字段是绝对路径（Windows 下为前斜杠）。
def _norm(path: str) -> str:
    return os.path.normcase(os.path.abspath(path)).replace("\\", "/")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


def changed_py_files(base: str) -> list[str]:
    """返回 base 与 HEAD 之间新增/修改的 .py 文件（仓库相对路径）。"""
    merge_base = _git("merge-base", base, "HEAD").strip()
    out = _git("diff", "--name-status", merge_base, "HEAD", "--diff-filter=ACMR")
    files = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[-1].endswith(".py"):
            files.append(parts[-1])
    return files


_HUNK = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def added_line_numbers(base: str, rel_path: str) -> set[int]:
    """解析 git diff -U0，返回新增行的新文件行号集合。"""
    merge_base = _git("merge-base", base, "HEAD").strip()
    out = _git("diff", "-U0", merge_base, "--", rel_path)
    added: set[int] = set()
    new_line: int | None = None
    for line in out.splitlines():
        m = _HUNK.match(line)
        if m:
            new_line = int(m.group(1))
            continue
        if new_line is None:
            continue  # diff 头行（diff --git / index / --- / +++）
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("\\"):
            continue  # "\\ No newline at end of file"
        if line.startswith("+"):
            added.add(new_line)
            new_line += 1
        elif line.startswith("-"):
            continue  # 仅旧文件行，不影响新文件行号
        else:
            new_line += 1  # 上下文行
    return added


def run_ruff(files: list[str]) -> list[dict]:
    """临时清空 per-file-ignores，对改动文件跑异常吞噬规则。"""
    if not files:
        return []
    proc = subprocess.run(
        [
            sys.executable, "-m", "ruff", "check", *files,
            "--select", RULES,
            "--config", "lint.per-file-ignores = {}",
            "--output-format=json",
        ],
        capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode not in (0, 1):
        # ruff 自身故障（如参数错误）时打印 stderr 并视为失败，避免静默放行
        print(proc.stderr, file=sys.stderr)
        sys.exit(proc.returncode or 1)
    return json.loads(proc.stdout) if proc.stdout.strip() else []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", nargs="?", default="HEAD~1",
                        help="diff 基准（commit sha 或 ref），默认 HEAD~1")
    args = parser.parse_args()

    files = changed_py_files(args.base)
    if not files:
        print("没有改动的 Python 文件，检查通过。")
        return 0

    added_by_file = {f: added_line_numbers(args.base, f) for f in files}
    violations = run_ruff(files)

    offending = []
    for v in violations:
        f = _norm(v["filename"])
        row = v["location"]["row"]
        # 归一化路径后与仓库文件匹配
        for rel in files:
            if _norm(rel) == f:
                key = rel
                break
        else:
            key = None
        if key is not None and row in added_by_file[key]:
            offending.append((key, row, v["code"], v["message"]))

    if offending:
        print(f"发现 {len(offending)} 处新增的异常吞噬违规（基准 {args.base}）：")
        for key, row, code, msg in sorted(offending):
            print(f"  {key}:{row}: {code} {msg}")
        print("请治理后重新提交（P9 三级分类：Level 1 上抛 / Level 2 记日志 / Level 3 noqa）。")
        return 1

    print(f"检查通过：{len(files)} 个改动文件，{len(violations)} 处存量违规均不在新增行。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
