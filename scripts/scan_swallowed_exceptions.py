#!/usr/bin/env python3
"""P9 Sprint 4 — 扫描被吞异常的「危险站点」（AST 启发式评分）。

用法:
    uv run python scripts/scan_swallowed_exceptions.py [--min-score 8] [--paths core/]

原理:
    用 AST 遍历目标目录的所有 .py 文件，对每个 try/except 处理器打分，分数反映
    被吞操作的严重性：
      写操作 +5   （open(w)/.write(/.save(/db insert/update/delete）
      网络调用 +3 （requests/aiohttp/httpx/urllib/http://）
      权限判定 +4 （is_superadmin/check_permission/authorize/access_control）
      空 pass  +2   （except 体只有 pass —— 静默吞没）
      裸 except +2  （bare except）

    总分 >= --min-score（默认 8）的站点打印出来，作为「必须上抛或加日志」的候选。
    Sprint 4 验收标准：`--min-score 8` 输出为空。
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# Windows 控制台强制 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

WRITE_OPS = (
    "write", "writelines", "save", "update", "insert", "delete", "upsert",
    "remove", "append", "dump", "commit", "unlink",
)
NETWORK_MARKERS = (
    "requests.", "aiohttp", "httpx", "urllib", "urlopen", "http://", "https://",
)
PERMISSION_MARKERS = (
    "is_superadmin", "is_staff", "check_permission", "authorize", "has_permission",
    "access_control", "verify_token",
)


def _score_try(try_src: str, handler: ast.ExceptHandler) -> int:
    """对一个 except 处理器打分：try 体中被保护的操作 + except 体的吞没方式。"""
    score = 0
    for op in WRITE_OPS:
        if f".{op}(" in try_src or f" {op}(" in try_src or f"{op}=(" in try_src:
            score += 5
            break
    if any(m in try_src for m in NETWORK_MARKERS):
        score += 3
    if any(m in try_src for m in PERMISSION_MARKERS):
        score += 4

    body = handler.body
    if len(body) == 1 and isinstance(body[0], ast.Pass) or not body:
        score += 2
    if handler.type is None:
        score += 2
    return score


def _iter_py_files(paths: list[str]):
    for p in paths:
        root = Path(p)
        if root.is_file():
            if root.suffix == ".py":
                yield root
        elif root.is_dir():
            yield from root.rglob("*.py")


def scan(paths: list[str], min_score: int) -> int:
    hits = 0
    for file in _iter_py_files(paths):
        try:
            source = file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            try_src = ast.get_source_segment(source, node) or ""
            for handler in node.handlers:
                # 跳过显式处理的站点：
                #  - continue 跳条 / return 带结果（不是静默吞没）
                #  - handler 已有 # noqa 注释（Sprint 2/3 已治理的边界站点）
                handler_src = ast.get_source_segment(source, handler) or ""
                if any(isinstance(st, (ast.Continue, ast.Return)) for st in handler.body):
                    continue
                if "# noqa" in handler_src:
                    continue
                s = _score_try(try_src, handler)
                if s >= min_score:
                    rel = file.as_posix()
                    kind = "裸except" if handler.type is None else ast.unparse(handler.type)
                    print(f"{rel}:{handler.lineno}  score={s}  catch={kind}")
                    hits += 1
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-score", type=int, default=8, help="打印阈值（默认 8）")
    parser.add_argument("--paths", nargs="*", default=["core/"], help="扫描目录/文件")
    args = parser.parse_args()

    hits = scan(args.paths, args.min_score)
    print(f"\n发现 {hits} 个危险站点（score >= {args.min_score}）")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
