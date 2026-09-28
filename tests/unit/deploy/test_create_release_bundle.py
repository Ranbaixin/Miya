"""A server bundle must not carry local accounts or runtime state."""

from __future__ import annotations

import hashlib
import subprocess
import tarfile
from pathlib import Path

from scripts.deploy.create_release_bundle import create_bundle


def test_server_bundle_includes_new_code_but_excludes_private_state(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    contents = {
        "core/app.py": "print('ready')\n",
        "config/permissions.json": "private account\n",
        "config/qq_config.yaml": "private account\n",
        "config/.env": "secret\n",
        "data/memory.json": "private memory\n",
        "miya_frontend/src/App.vue": "desktop only\n",
        "docs/LOCAL_INFRA_PRIVATE.md": "private infrastructure\n",
    }
    for name, content in contents.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"],
        cwd=repo,
        check=True,
    )
    new_script = repo / "scripts/deploy/prepare_miya_user.sh"
    new_script.parent.mkdir(parents=True)
    new_script.write_text("#!/bin/sh\n", encoding="utf-8")

    output = tmp_path / "server.tar.gz"
    manifest = create_bundle(repo, output, server_only=True)
    with tarfile.open(output, "r:gz") as archive:
        names = archive.getnames()
        assert names == ["core/app.py", "scripts/deploy/prepare_miya_user.sh"]
        assert archive.getmember("scripts/deploy/prepare_miya_user.sh").mode == 0o755
    assert manifest["file_count"] == 2
    assert manifest["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
