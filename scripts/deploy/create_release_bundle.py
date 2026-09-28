#!/usr/bin/env python3
"""Build a code-only deployment archive from the current working tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_PATHS = {"config/permissions.json", "config/qq_config.yaml", "docs/LOCAL_INFRA_PRIVATE.md"}
PRIVATE_DIRS = ("data/", "miya_frontend/data/")


def included_files(root: Path, server_only: bool = False) -> list[tuple[str, Path]]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        stdout=subprocess.PIPE,
        check=True,
    )
    files: list[tuple[str, Path]] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        name = os.fsdecode(raw).replace("\\", "/")
        parts = Path(name).parts
        if (name in PRIVATE_PATHS or name.startswith(PRIVATE_DIRS)
                or (server_only and name.startswith("miya_frontend/"))
                or any(part.startswith(".env") for part in parts)):
            continue
        path = root / name
        if not path.is_file():
            continue  # staged deletion
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Refusing path outside repository: {name}")
        files.append((name, path))
    return sorted(set(files))


def create_bundle(root: Path, output: Path, server_only: bool = False) -> dict:
    root = root.resolve()
    output = output.resolve()
    if output.is_relative_to(root):
        raise ValueError("Deployment archive must be outside the repository")
    output.parent.mkdir(parents=True, exist_ok=True)

    files = included_files(root, server_only=server_only)
    manifest = {
        "created_utc": datetime.now(UTC).isoformat(),
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "file_count": len(files),
        "server_only": server_only,
        "files": [name for name, _ in files],
    }
    with tarfile.open(output, "w:gz") as archive:
        for name, path in files:
            info = archive.gettarinfo(str(path), arcname=name)
            info.mode = 0o755 if name.endswith(".sh") else 0o644
            with path.open("rb") as source:
                archive.addfile(info, source)

    digest = hashlib.sha256()
    with output.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    manifest["sha256"] = digest.hexdigest()
    output.with_suffix(output.suffix + ".json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Destination .tar.gz outside the repository")
    parser.add_argument("--server-only", action="store_true", help="Exclude the desktop frontend from a cloud daemon deploy")
    args = parser.parse_args()
    result = create_bundle(REPO_ROOT, args.output, server_only=args.server_only)
    print(f"Created {args.output}: {result['file_count']} files, SHA-256 {result['sha256']}")
