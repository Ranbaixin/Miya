#!/usr/bin/env bash
# 弥娅服务器基线 + 运行时安装（Ubuntu 24/26 LTS，阿里云 ECS 实测 26.04）
# 用法: bash server_setup.sh   （root 运行）
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=== 1. 系统更新 ==="
apt-get update -qq
apt-get upgrade -y -qq

echo "=== 2. 2G swap（1.6Gi 可用内存的硬要求）==="
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap -q /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
swapon --show

echo "=== 3. 基础工具 ==="
apt-get install -y -qq git curl ufw tmux htop

echo "=== 4. 防火墙：只放 SSH（Web 端口一律 127.0.0.1）==="
mkdir -p /opt/miya/logs
ufw default deny incoming
ufw allow 22/tcp
ufw --force enable

echo "=== 5. uv + Python 3.11（走 npmmirror 下载、阿里云 pypi 源）==="
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
export UV_PYTHON_INSTALL_MIRROR=https://registry.npmmirror.com/-/binary/python-build-standalone
uv python install 3.11
mkdir -p /root/.config/uv
cat > /root/.config/uv/uv.toml <<'EOF'
[[index]]
url = "https://mirrors.aliyun.com/pypi/simple/"
default = true
EOF

echo "=== 6. Docker（get.docker.com 被墙时走阿里云源）==="
if ! command -v docker >/dev/null; then
  if curl -fsSL --max-time 20 https://get.docker.com -o /tmp/getdocker.sh 2>/dev/null; then
    sh /tmp/getdocker.sh
  else
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    CODENAME=$(lsb_release -cs)
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $CODENAME stable" > /etc/apt/sources.list.d/docker.list
    apt-get update -qq || sed -i "s/$CODENAME/noble/" /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io
  fi
fi
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{"registry-mirrors":["https://docker.m.daocloud.io","https://docker.1ms.run"]}
EOF
systemctl enable --now docker
systemctl restart docker
docker --version
uv --version
uv python find 3.11
echo "BASELINE_DONE"
