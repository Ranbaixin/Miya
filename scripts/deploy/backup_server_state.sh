#!/usr/bin/env bash
# Live pre-deployment backup. Does not stop or change either running service.
set -euo pipefail
umask 077

if [[ $(id -u) -ne 0 ]]; then
  echo 'Run as root.' >&2
  exit 1
fi

name=${1:-$(date -u +%Y%m%dT%H%M%SZ)}
if [[ ! "$name" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
  echo 'Backup name must be a UTC timestamp such as 20260927T120000Z.' >&2
  exit 1
fi

root=/opt/miya-backups
destination="$root/$name"
if [[ -e "$destination" ]]; then
  echo "Backup already exists: $destination" >&2
  exit 1
fi
install -d -m 0700 "$root" "$destination" "$destination/sqlite" "$destination/systemd"

systemctl is-active miya-daemon.service > "$destination/miya-service-state.txt" || true
docker inspect napcat > "$destination/napcat-inspect.json"
image_id=$(docker inspect napcat --format '{{.Image}}')
docker image inspect "$image_id" > "$destination/napcat-image-inspect.json"
for unit in /etc/systemd/system/miya*.service /etc/systemd/system/miya*.timer; do
  [[ -f "$unit" ]] && cp -a "$unit" "$destination/systemd/"
done

# Code, config and the existing venv are the fast rollback path. Keep mutable
# data separate so SQLite can be backed up through its online backup API.
tar -C /opt/miya \
  --exclude='./data' --exclude='./logs' --exclude='./.git' \
  --exclude='./miya_frontend/node_modules' --exclude='./miya_frontend/dist' \
  -czf "$destination/miya-code-config-venv.tar.gz" .
tar -C /opt/miya \
  --exclude='*.db' --exclude='*.db-wal' --exclude='*.db-shm' \
  --exclude='*.sqlite' --exclude='*.sqlite-wal' --exclude='*.sqlite-shm' \
  --exclude='*.sqlite3' --exclude='*.sqlite3-wal' --exclude='*.sqlite3-shm' \
  -czf "$destination/miya-data-files.tar.gz" data logs

python3 - "$destination/sqlite" <<'PY'
import sqlite3
import sys
from pathlib import Path

source_root = Path('/opt/miya/data')
target_root = Path(sys.argv[1])
sources = sorted(p for p in source_root.rglob('*') if p.is_file() and p.suffix in {'.db', '.sqlite', '.sqlite3'})
for source in sources:
    target = target_root / source.relative_to(source_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=30) as original:
        with sqlite3.connect(target) as copy:
            original.backup(copy)
            result = copy.execute('PRAGMA integrity_check').fetchone()
            if result != ('ok',):
                raise RuntimeError(f'SQLite integrity check failed: {source}')
print(f'Backed up and checked {len(sources)} SQLite databases')
PY

tar -C /opt/napcat -czf "$destination/napcat-bind-data.tar.gz" .
qq_volume=$(docker inspect napcat --format '{{range .Mounts}}{{if eq .Destination "/app/.config/QQ"}}{{.Source}}{{end}}{{end}}')
case "$qq_volume" in
  /var/lib/docker/volumes/*/_data) ;;
  *) echo 'Unexpected or missing NapCat QQ volume path.' >&2; exit 1 ;;
esac
tar -C "$qq_volume" -czf "$destination/napcat-qq-volume.tar.gz" .
docker image save "$image_id" | gzip -1 > "$destination/napcat-image.tar.gz"

for archive in "$destination"/*.tar.gz; do
  tar -tzf "$archive" > /dev/null
done
(
  cd "$destination"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
  sha256sum --check --quiet SHA256SUMS
)
chmod -R go-rwx "$destination"
echo "Verified live backup: $destination"
