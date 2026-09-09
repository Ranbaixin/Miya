# 弥娅云部署 Runbook（阿里云 ECS 实操手册）

> 首次部署完成于 2026-09-08。目标机：阿里云 99元/年 e实例（2核 / 1.6Gi 可用 / 40G / Ubuntu 26.04）。
> 本机（Windows）通过 Workbench CLI 远程驱动：`workbench exec --instance-id <ID> --region cn-beijing --command "..."`。
> 服务器上：弥娅在 `/opt/miya`（systemd 服务 `miya-daemon`），NapCat 容器 `napcat`（host 网络），记忆数据在 `/opt/miya/data`。

## 一、首次部署（8 步）

1. **本机打包**（Git Bash，仓库根目录）：
   ```bash
   tar -czf "$TMP/miya_bundle.tar.gz" --exclude='./.venv' --exclude='./venv' --exclude='./logs' \
     --exclude='./.git' --exclude='./data/neo4j' --exclude='__pycache__' --exclude='./miya_frontend' \
     --exclude='./release' --exclude='node_modules' --exclude='./.pytest_cache' .
   ```
2. **服务器基线**：`bash scripts/deploy/server_setup.sh`（或经 workbench exec 分段执行）
3. **上传**（注意禁用 Git Bash 路径转换）：
   ```bash
   MSYS_NO_PATHCONV=1 workbench upload "$TMP/miya_bundle.tar.gz" /tmp/miya_bundle.tar.gz \
     --instance-id <ID> --region cn-beijing --force
   ```
4. **解压 + .env 加固**：解压到 `/opt/miya`；`.env` 里 `API_HOST=127.0.0.1`、追加随机 `MIYA_API_TOKEN`、注释 `NEO4J_PASSWORD`（无 Neo4j 自动降级）
5. **依赖**：`cd /opt/miya && uv sync --no-group dev`
6. **服务化**：`cp scripts/deploy/miya-daemon.service /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now miya-daemon`
7. **NapCat**：`bash scripts/deploy/napcat_setup.sh 1153409562` → 扫码 → 写反向 WS（见 napcat_setup.sh 尾部说明）→ `docker restart napcat`
8. **验证**：个人 QQ 给机器人发消息，`journalctl -u miya-daemon | grep 发送回复` 看到回复即完成

## 二、日常运维速查

| 操作 | 命令 |
|---|---|
| 服务状态 | `systemctl status miya-daemon` |
| 实时日志 | `journalctl -u miya-daemon -f` |
| 重启弥娅 | `systemctl restart miya-daemon` |
| NapCat 状态 | `docker ps` / `docker logs -f --tail 30 napcat` |
| 健康检查 | `curl 127.0.0.1:9800/api/v1/health` |
| 内存水位 | `free -h`（swap 用量 >50% 需警惕） |

## 三、版本更新流程

1. 本机改代码 → 打包（同第 1 步）
2. `MSYS_NO_PATHCONV=1 workbench upload <包> /tmp/b.tgz --instance-id <ID> --region cn-beijing --force`
3. 服务器：`systemctl stop miya-daemon && tar -xzf /tmp/b.tgz -C /opt/miya && cd /opt/miya && uv sync --no-group dev && systemctl start miya-daemon`
4. 数据目录 `data/` 会被覆盖——**只更新代码时打包要排除 data/**（加 `--exclude='./data'`）
5. **部署后必跑冒烟**（服务状态/健康端点/NapCat/错误签名扫描/记忆一致性）：
   `bash scripts/deploy/post_deploy_check.sh` —— 退出码非 0 = 存在 FAIL，修复后重试
6. 部署涉及依赖变更时（pyproject.toml 改动），必须确认 `uv sync --no-group dev` 真正装上
   （教训：pillow 在可选组导致服务器 PIL 缺失、QQ 多媒体工具整包静默加载失败）

## 三.5、每日自动自检（systemd timer）

```bash
cp scripts/deploy/miya-doctor.service scripts/deploy/miya-doctor.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now miya-doctor.timer
```

每天 04:00 自动跑 `doctor --runtime`（26h 窗口错误签名 / crash-loop / 健康端点 / 记忆一致性），
结果追加到 `/opt/miya/logs/doctor.log`；有 FAIL 时 systemd 标记 failed，用
`systemctl list-units --failed` 发现。本地手动跑：`make doctor`（全量 `python scripts/doctor.py --runtime`）

## 四、已知注意事项（部署实测发现）

- **run/main.py 曾硬编码 8000 端口绑 0.0.0.0**——已改为读 `API_HOST`（默认 127.0.0.1），别改回去
- **jinja2 / email-validator 是必需运行时依赖**（已进 pyproject；服务器上靠 `uv add` 补过）
- NapCat 反向 WS 必须配在 `onebot11_<QQ>.json` 的 `network.websocketClients`（messagePostFormat=array）；URL 用 `ws://127.0.0.1:8095/onebot/v11/ws`
- NapCat 容器重启后自动快速登录（凭据在 /opt/napcat 卷），无需重扫
- 服务器内存 1.6Gi：勿启用 Neo4j / 本地 embedding；swap 2G 已配
- Git Bash 下 workbench 的远端路径参数要加 `MSYS_NO_PATHCONV=1`，否则 `/tmp` 会被改写成本机路径

## 五、安全基线（红线）

- 安全组 + ufw 只放 22；8000/9800/8095/6099 全部仅 127.0.0.1 监听
- `.env` 含全部 API Key，权限 600，绝不进 git
- NapCat 用专用小号；WebUI(6099) 只经 SSH 隧道访问
