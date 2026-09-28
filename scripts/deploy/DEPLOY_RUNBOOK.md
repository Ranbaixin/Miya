# 弥娅云部署 Runbook（阿里云 ECS 实操手册）

> 首次部署完成于 2026-09-08。目标机：阿里云 99元/年 e实例（2核 / 1.6Gi 可用 / 40G / Ubuntu 26.04）。
> 本机（Windows）通过 Workbench CLI 远程驱动：`workbench exec --instance-id <ID> --region cn-beijing --command "..."`。
> 服务器上：弥娅在 `/opt/miya`（systemd 服务 `miya-daemon`），NapCat 容器 `napcat`（host 网络），记忆数据在 `/opt/miya/data`。

> 本机私有配置 `config/permissions.json`、`config/qq_config.yaml` 从对应 `.example` 复制后填写；两者已不由 Git 跟踪。代码部署包**不含**这两份配置、`.env` 或运行数据。首次部署需经单独的私有通道配置，后续更新保留服务器现有文件。

## 一、首次部署（8 步）

1. **本机打包**（仓库根目录；输出路径需在仓库外）：
   ```bash
   python scripts/deploy/create_release_bundle.py /tmp/miya-server.tar.gz --server-only
   ```
   打包器从当前 Git 索引与未忽略的新文件取代码，排除私有配置、`data/` 和桌面端资源，并生成带 SHA-256 的同名 `.json` 清单。
2. **服务器基线**：`bash scripts/deploy/server_setup.sh`（或经 workbench exec 分段执行）
3. **上传**（注意禁用 Git Bash 路径转换）：
   ```bash
   MSYS_NO_PATHCONV=1 workbench upload /tmp/miya-server.tar.gz /opt/miya-staging/<UTC>/miya-server.tar.gz \
     --instance-id <ID> --region cn-beijing --force
   ```
4. **解压 + 私有配置**：解压到 `/opt/miya`；首次部署在服务器上单独写入私有配置。`.env` 里 `API_HOST=127.0.0.1`、追加随机 `MIYA_API_TOKEN`、注释 `NEO4J_PASSWORD`（无 Neo4j 自动降级）
5. **依赖**：`cd /opt/miya && uv sync --no-group dev`
6. **服务化**：先运行 `bash scripts/deploy/prepare_miya_user.sh`，再执行 `cp scripts/deploy/miya-daemon.service /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now miya-daemon`。服务以专用 `miya` 用户运行，运行数据、日志和配置由该用户持有，代码与虚拟环境仍由部署账号持有。
7. **NapCat**：`bash scripts/deploy/napcat_setup.sh <BOT_QQ>` → 扫码 → 写反向 WS（见 napcat_setup.sh 尾部说明）→ `docker restart napcat`
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

1. 本机改代码 → 用 `create_release_bundle.py --server-only` 打包；确认清单中的 SHA-256 和文件数。
2. 服务器先运行 `bash scripts/deploy/backup_server_state.sh`，确认 `/opt/miya-backups/<UTC>/SHA256SUMS` 校验通过。此为在线备份：SQLite 用在线备份 API，NapCat 数据卷在容器运行时复制；恢复 NapCat 数据卷前必须停容器。
3. 上传包和清单到 `/opt/miya-staging/<UTC>/`，在服务器核对 SHA-256、文件清单及私有路径排除结果。Workbench 上传经 OSS 中转，因此部署包不能包含账号配置或运行数据。
4. 服务器：`systemctl stop miya-daemon && tar -xzf /opt/miya-staging/<UTC>/miya-server.tar.gz -C /opt/miya && cd /opt/miya && uv sync --no-group dev && bash scripts/deploy/prepare_miya_user.sh && cp scripts/deploy/miya-daemon.service /etc/systemd/system/ && systemctl daemon-reload && systemctl start miya-daemon`。打包器已排除 `data/` 和私有配置，现有数据不会被解压覆盖。
5. **部署后必跑冒烟**（服务状态/健康端点/NapCat/错误签名扫描/记忆一致性）：
   `bash scripts/deploy/post_deploy_check.sh` —— 退出码非 0 = 存在 FAIL，修复后重试
6. 部署涉及依赖变更时（pyproject.toml 改动），必须确认 `uv sync --no-group dev` 真正装上
   （教训：pillow 在可选组导致服务器 PIL 缺失、QQ 多媒体工具整包静默加载失败）

从旧 root 服务迁移时，先停止服务，再运行 `prepare_miya_user.sh`；脚本会拒绝在服务仍运行时修改所有权。启动后用 `systemctl show miya-daemon -p User -p Group`、`systemctl status miya-daemon` 和健康端点确认。若启动失败，先读 `journalctl -u miya-daemon -n 100` 查找未覆盖的写入目录，修正该目录所有权后重试，不要临时把服务切回 root。
旧环境的 `.venv/bin/python` 可能指向 `/root/.local/share/uv/python`，专用用户无法访问；迁移脚本会把 Python 安装到 `/usr/local/share/uv/python` 并重新同步虚拟环境。该步骤需要网络和额外磁盘空间，运行前应确认服务可停机维护。

**回滚**：保持服务停止，先在备份目录运行 `sha256sum --check SHA256SUMS`；解压 `miya-code-config-venv.tar.gz` 和 `miya-data-files.tar.gz` 到 `/opt/miya`，将 `sqlite/` 下的数据库复制回 `data/` 对应路径（先移开旧 `.db-wal`/`.db-shm`），恢复 `systemd/miya-daemon.service` 后 `systemctl daemon-reload && systemctl start miya-daemon`，再跑 `post_deploy_check.sh`。NapCat 只有在本次变更触及时才需要停容器并恢复它的挂载数据与镜像。备份目录仅 root 可读。

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
- NapCat 容器重启后自动快速登录（凭据在 /opt/napcat 卷），无需重扫——**但凭据可能过期**
  （2026-09-10 事故：快速登录失效 + QQ 风控 168，桥接断裂 11 小时无人察觉）。处理顺序：
  `docker restart napcat` → 二维码扫码（约 2 分钟一刷，及时取用）→ 风控拦截时先在手机 QQ
  解除限制再扫。**建议给 NapCat 配置 `NAPCAT_QUICK_PASSWORD`/`NAPCAT_QUICK_PASSWORD_MD5`
  环境变量作密码回退**，摆脱对扫码的依赖
- **桥接/会话双断裂场景对照**（自愈 v2 分而治之，每 5 分钟自动检测）：

  | 场景 | 特征 | 自愈动作 |
  |---|---|---|
  | A. WS 桥接断裂 | miya 日志最后事件为"NapCat 断开"，凭据多半仍有效 | 自动 `docker restart napcat`（每日上限 4 次） |
  | B. QQ 会话被踢 | napcat 日志出现 `KickedOffLine`/`登录已失效`，**WS 未必断开**（僵尸连接，消息已死） | 密码回退启用 → 重启走密码登录；停用 → 写 `NEED_MANUAL_SCAN` 标记（/var/lib/napcat_manual_scan_flag，次日自动清），doctor 报 FAIL 提示人工扫码 |

  ⚠️ **密码回退的实测限制**：被风控盯上的账号走密码登录会**强制短信验证**，且 NapCat 在验证流程中会卡死不落二维码（2026-09-11 实测）——因此当前密码回退处于停用状态（原配置备份在 `/opt/napcat/.env.password-backup`）。恢复方法：`mv /opt/napcat/.env.password-backup /opt/napcat/.env && docker compose -f scripts/deploy/docker-compose.napcat.yml up -d --force-recreate`，且需先打通 WebUI(5099) SSH 隧道完成短信验证
  - B 场景的最终恢复手段就是人工扫码：`docker cp napcat:/app/napcat/cache/qrcode.png /tmp/qr.png` 取最新码（约 2 分钟一刷，过期重启容器刷新）
- **桥接自愈**：miya-napcat-selfheal.timer 每 5 分钟检测断裂并自动 `docker restart napcat`
  （每日上限 2 次，状态在 /var/lib/napcat_selfheal_state；日志 logs/napcat_selfheal.log）。
  注意：仅对"WS 断开但凭据有效"的断裂有效；凭据被服务端作废（"登录态已失效"）时重启无效，
  必须重新扫码
- **容器标准配置改用 compose**：`scripts/deploy/docker-compose.napcat.yml`（cd /opt/napcat &&
  docker compose up -d）。QQ 凭据在 docker volume（external，已复用原卷），重建容器不丢登录态。
  现在 compose 的镜像固定为已运行版本的 digest；首次使用新版 compose 前，先在 `/opt/napcat/.env` 填写 `NAPCAT_ACCOUNT` 和现有数据卷名 `NAPCAT_QQ_VOLUME`（可通过 `docker inspect napcat` 查询）。在 `/opt/napcat` 目录运行 `docker compose config` 核对卷和账号配置后再重建。
  `NAPCAT_UID`/`NAPCAT_GID` 默认是 10001；该镜像启动脚本会将 `/app` 中的挂载数据改为此所有者，再用 `gosu napcat` 启动 QQ。重建后用 `docker exec napcat ps -eo user,pid,comm` 检查 QQ 进程用户；启动脚本本身仍以 root 运行，容器 host 网络也仍需单独评估。
  密码回退：在 /opt/napcat/.env 配 `NAPCAT_QUICK_PASSWORD_MD5`（echo -n "密码" | md5sum），
  凭据被风控作废时可自动密码登录，摆脱扫码依赖；.env chmod 600 不进 git

## 四.5、QQ 小号风控应对（2026-09 实战沉淀）

现象谱系：serverErrorCode 168（"部分功能使用受限"）、"登录态已失效"、会话数小时后 sendMsg
超时/进消息停止——均为 QQ 服务端风控踢会话，数据中心 IP + 低权重小号是主要诱因。

**账号养号清单（用户执行，最有效）**：
1. 手机 QQ 每天登录小号，保持真实使用
2. 完成实名认证；开启设备锁并信任常用设备
3. QQ 安全中心（aq.qq.com）检查并清除异常记录
4. 腾讯系产品（QQ音乐等）适度活跃；与几个好友日常互动
5. 坚持 1-2 周，权重上来后风控频率显著下降

**升级路线（若养号后仍频繁被控）**：
- NapCat 迁家宽：反向 WS 客户端可跑在任何能上网的设备，出站连接云上 miya 的 8095
  （tailscale/frp 隧道 + token 鉴权），IP 信誉从数据中心变家庭宽带
- 替代通道：QQ 官方机器人 API（bot.qq.com，零风控，但主动私聊/群能力受限，交互缩水）
- 服务器内存 1.6Gi：勿启用 Neo4j / 本地 embedding；swap 2G 已配
- Git Bash 下 workbench 的远端路径参数要加 `MSYS_NO_PATHCONV=1`，否则 `/tmp` 会被改写成本机路径

## 五、安全基线（红线）

- 安全组 + ufw 只放 22；8000/9800/8095/6099 全部仅 127.0.0.1 监听
- `.env` 含全部 API Key，权限 600，绝不进 git
- NapCat 用专用小号；WebUI(6099) 只经 SSH 隧道访问
