#!/usr/bin/env bash
# One-time migration for running miya-daemon as an unprivileged system user.
# Run as root after stopping miya-daemon; safe to repeat after code deployments.
set -euo pipefail

APP_ROOT=/opt/miya
SERVICE_USER=miya

if [[ $(id -u) -ne 0 ]]; then
  echo 'Run as root.' >&2
  exit 1
fi
if systemctl is-active --quiet miya-daemon.service; then
  echo 'Stop miya-daemon.service before changing file ownership.' >&2
  exit 1
fi
if [[ ! -x "$APP_ROOT/.venv/bin/python" ]]; then
  echo "Missing executable $APP_ROOT/.venv/bin/python; run uv sync first." >&2
  exit 1
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home-dir /var/lib/miya --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0700 /var/lib/miya /var/cache/miya

# Older deployments placed uv's Python under /root, which the service user
# cannot traverse even when .venv/bin/python is executable.
if ! runuser -u "$SERVICE_USER" -- test -x "$APP_ROOT/.venv/bin/python"; then
  export UV_PYTHON_INSTALL_DIR=/usr/local/share/uv/python
  uv python install --no-bin 3.11
  shared_python=$(uv python find --managed-python --no-project --resolve-links 3.11)
  case "$shared_python" in
    "$UV_PYTHON_INSTALL_DIR"/*) ;;
    *) echo "Unexpected shared Python path: $shared_python" >&2; exit 1 ;;
  esac
  cd "$APP_ROOT"
  uv sync --python "$shared_python" --no-group dev
  runuser -u "$SERVICE_USER" -- test -x "$APP_ROOT/.venv/bin/python"
fi

# Code and the virtual environment stay owned by the deploy account. Only
# runtime state, logs and live configuration need write access by the daemon.
for relative in data logs .miya .memory config; do
  target="$APP_ROOT/$relative"
  if [[ -L "$target" ]]; then
    echo "Refusing symlinked runtime directory: $target" >&2
    exit 1
  fi
  install -d "$target"
  chown -R "$SERVICE_USER:$SERVICE_USER" "$target"
  find "$target" -type d -exec chmod 0700 {} +
  find "$target" -type f -exec chmod go-rwx {} +
done

if [[ -f "$APP_ROOT/.env" ]]; then
  if [[ -L "$APP_ROOT/.env" ]]; then
    echo 'Refusing symlinked .env' >&2
    exit 1
  fi
  chown "$SERVICE_USER:$SERVICE_USER" "$APP_ROOT/.env"
  chmod 0600 "$APP_ROOT/.env"
fi

cd "$APP_ROOT"
runuser -u "$SERVICE_USER" -- "$APP_ROOT/.venv/bin/python" -c \
  'from pathlib import Path; root=Path("/opt/miya"); assert all((root / p).is_dir() for p in ("data", "logs", "config")); import core.doctor'
echo 'Miya service user prepared. Install the unit and start miya-daemon.service.'
