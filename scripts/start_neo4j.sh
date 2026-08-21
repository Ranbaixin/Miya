#!/usr/bin/env bash
# 启动 Miya 知识图谱 Neo4j 容器（端口 17687:7687）
# 密码从 config/.env 的 NEO4J_PASSWORD 读取（不打印）
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/config/.env"

# 读取 .env 中的 NEO4J 配置
NEO4J_URI=$(grep -E '^NEO4J_URI=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d ' ')
NEO4J_USER=$(grep -E '^NEO4J_USER=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d ' ')
NEO4J_PASSWORD=$(grep -E '^NEO4J_PASSWORD=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d ' ')

if [ -z "$NEO4J_PASSWORD" ]; then
  echo "[neo4j] .env 未配置 NEO4J_PASSWORD"
  exit 1
fi

# 已存在则直接启动
if docker ps -a --format '{{.Names}}' | grep -q '^miya-neo4j$'; then
  docker start miya-neo4j
  echo "[neo4j] 容器 miya-neo4j 已启动"
  exit 0
fi

echo "[neo4j] 拉取并启动 neo4j:5 (port 17687)..."
docker run -d --name miya-neo4j   -p 17687:7687   -e "NEO4J_AUTH=$NEO4J_USER/$NEO4J_PASSWORD"   -e NEO4J_server_memory_heap_initial__size=256m   -e NEO4J_server_memory_heap_max__size=512m   -e NEO4J_server_memory_pagecache_size=256m   --restart unless-stopped   neo4j:5
echo "[neo4j] 容器已创建，等待健康..."
