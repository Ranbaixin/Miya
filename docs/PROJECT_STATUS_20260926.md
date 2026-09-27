# 弥娅项目现状全景（2026-09-26 快照）

> **读者**：新接手的 agent / 开发者 / 运维者。
> **配套文档**：架构细节 `docs/MIYA_ARCHITECTURE.md`；开发规范 `docs/DEVELOP_GUIDE.md`；部署实操 `scripts/deploy/DEPLOY_RUNBOOK.md`；交接续作 `docs/HANDOFF_20260920.md`（含自检审计附录）。
> **敏感信息约定**：IP、端口拓扑、实例 ID、账号、API Key 一律不入 git——本地-only 文件 `docs/LOCAL_INFRA_PRIVATE.md`（已 gitignore），可提交文档内用占位符。
> **维护约定**：重大变更（模型切换、事故、架构迁移）后更新本文。

---

## 1. 项目一句话

弥娅（MIYA）是运行在云服务器上的 AI 虚拟化身：QQ 机器人形态接入，拥有持久记忆、情绪系统、主动聊天、44 个工具调用、多模态识图、**用户电脑使用数据感知**（2026-09-21 新增）。用户（然鑫）是唯一 superadmin。

**分支** `fix/v8-hardening`（v8 硬化线，未合 main）。**测试基线** 321 passed。**当前无活跃事故**。

---

## 2. 运行拓扑（含服务器连接，全貌）

```
[然鑫手机QQ] ←→ [NapCat 容器] --反向WS--> [弥娅 daemon :8095] ←→ [DeepSeek API]
                                                    ↑ SSH反向隧道(9443)
[然鑫电脑: PC Timer :8088] ─────────────────────────┘
```

### 2.1 三个节点

| 节点 | 位置 | 形态 | 说明 |
|---|---|---|---|
| **弥娅核心** | 云服务器（阿里云 ECS，实例 ID 见本地文档） | systemd `miya-daemon`，`/opt/miya`，uv 仅 runtime 组 | 主进程 + 管理 API :9800（127.0.0.1）；管理通道 workbench CLI |
| **NapCat** | 同服务器 docker | compose：`docker compose -f scripts/deploy/docker-compose.napcat.yml up -d` | QQ 协议端，反向 WS 客户端拨出连 8095；QQ 凭据在 docker volume；机器人小号 <BOT_QQ>（实名见本地文档） |
| **PC Timer** | 然鑫的 Windows 电脑 | `C:\Users\Ran-xin\pc-time-tracker`（独立项目 github.com/Ranbaixin/pc-time-tracker） | 前台窗口使用追踪，FastAPI :8088（127.0.0.1），54k+ 记录 |

### 2.2 连接链路（三条）

| 链路 | 方向 | 机制 | 状态 |
|---|---|---|---|
| QQ 消息 | 手机 ↔ NapCat ↔ 弥娅 | NapCat 反向 WS 拨出 `ws://127.0.0.1:8095`（服务端是弥娅，无需公网入站） | ✅ 稳定（9/12 恢复后零掉线） |
| **PC 使用数据** | 然鑫电脑 → 云端 | **SSH 反向隧道**：电脑 `tunnel_to_miya.cmd`（启动文件夹自启，断线 15s 重连）以受限账号 `tunnel` 拨出 `-R 127.0.0.1:9443:127.0.0.1:8088`；云端弥娅经 `http://127.0.0.1:9443/api/v1` 读 PC Timer | ✅ 全链路验证（26/09 修复装配断点后 6/6 工具可用） |
| AI 服务 | 弥娅 → DeepSeek | deepseek-flash（chat/vision，原生多模态 1M 上下文）+ deepseek-embedding | ✅ 识图 9/20 验收通过 |

### 2.3 安全红线（不变）

- 服务器安全组/ufw 只放 22；9800/8095/9443/6099 全部仅 127.0.0.1
- SSH 隧道用**专用受限账号**（`restrict,port-forwarding,permitlisten="127.0.0.1:9443"`——密钥泄露也只能转发这一条），密钥 `~/.ssh/id_ed25519_miyatunnel`（本机）
- `config/.env`（全部 API key）权限 600，**已 gitignore，绝不进 git**； NapCat 密码回退已停用（备份 `.env.password-backup`，原因见 runbook）

---

## 3. PC 使用数据链路（最新能力，2026-09-26 修复完成）

**数据流**：PC Timer（秒级前台窗口追踪，自动分类 开发/浏览/游戏/社交…+空闲检测）→ `/api/v1/agent/context`（中文摘要接口）→ 隧道 → 弥娅。

**三个消费点**：
1. **QQ 实时问答**：`mcp_pc_tracker_pc_context`（当日摘要+当前窗口）在 QQ_CORE_PACK 必带；`pc_daily`/`pc_processes` 在 desktop 扩展包（关键词：电脑/用了多久/使用时长/开机…）→ 问"我今天电脑用了多久"直接答
2. **每日作息沉淀**：23:30 自动把当日 text_summary 写入长期记忆（tags: pc_usage/作息；电脑离线跳过；`PC_DIGEST_*` 可配）→ 弥娅长期了解作息
3. **6 个工具**：context/daily/processes/current/insights/status

**装配链的教训**（2026-09-26 事故，两个断点）：①manifest 参数定义 dict 形态致 schema 构建崩，被 discover 外层 try/except 吞掉——**该服务之后的所有服务工具全部静默丢失**；②工具加进 CORE_TOOLS 但 QQ 走 pack 路由——配置对了不生效。均已修（per-service/per-tool 隔离 + 路由对齐），同类模式全项目自检见 HANDOFF 附录。

**边界**：电脑关机 = 链路断（弥娅如实说"电脑不在线"）；数据流是"查询+每日快照"，无实时事件推送（久坐提醒需 v1.5 推送器，挂载点已探明）。

---

## 4. 运维保障体系（全部在岗）

| 防线 | 内容 | 状态 |
|---|---|---|
| doctor 统一自检 | 9 类检查（C1-C9），`python scripts/doctor.py --runtime`，FAIL→exit 1 | 每日 04:00 timer；CI config-guard；手动体检 FAIL=0 |
| 启动预检 | daemon 起动即查配置/模型/env，告警不阻断 | 每次重启生效 |
| 部署冒烟 | `scripts/deploy/post_deploy_check.sh`（部署后必跑，exit 0 才算完成） | 在岗 |
| 桥接/会话自愈 v2 | 每 5 分钟：WS 断开自动重启（日限 4 次）；QQ 踢会话检测（KickedOffLine）→ 需人工扫码时打 NEED_MANUAL_SCAN 标记 | 零触发=好事 |
| 错误回复闸门 | AI 报错回复不写入记忆/会话历史（防模型把报错当"自己说过的话"） | 9/16 上线，存量 27 条已清 |
| 工具配对保障 | ai_client 工具循环 tool_calls/tool 消息一一配对（DeepSeek 严格校验），`tests/unit/core/test_ai_client_tool_pairing.py` 守护 | 9/16 修复 |

**已知接受 WARN**（勿当 bug 修）：tts_config.json 未建（无 TTS）；matplotlib 缺失（1.6G 内存机既定决策）。

---

## 5. 模型与指令

**模型**：deepseek-flash 三通道（chat/vision/embedding，同一个 key）；vision max_tokens 4000、空描述重试+reasoning 兜底（9/20 修复）；回滚 `git revert 8786aaef`（ZHIPU_API_KEY 保留）。

**QQ 指令**（superadmin 全可用）：状态 / 形态（19 形态）/ 说话 / 余额（9/16 新增）/ 统计 / admin / faq / system / 语音·文本·tts / 唱歌族 / 记忆族 / 帮助·版本。三个已知坑：未知斜杠误入记忆搜索、/形态 写错名报错、唱歌子串误触（详见 9/19 对话清单）。

**PC 数据问答**：直接自然语言问（"我今天电脑用了多久/刚才在用什么"），无需指令。

---

## 6. 待办方向（在等什么）

| 方向 | 状态 | 等什么 |
|---|---|---|
| **PC Timer 稳定性** | 🔶 唯一活跃问题 | 9/21 两次静默死亡（根因未明，新日志机制 `[EXIT]` 标记下次留痕）；**用户待办：pc-time-tracker 24 文件修复改动未 commit** |
| SnowLuma 迁移 | 📋 排期待启动 | 养号已达标（8 天+零被踢）；前置=验收矩阵（10 个 NapCat 扩展 action 覆盖度）+ compose；**换端不解决风控** |
| Persona Profiler 新项目 | 📋 已规划待启动 | 独立仓库自适应问卷画像（计划要点在 9/13 对话，需落盘为 README）；Miya 内置画像管线由它承接 |
| registry 守卫加固 / 死配置清理 | 📋 审计工单 | HANDOFF 附录 §1-6（registry 六加载器无守卫=一崩全丢 68 工具、permissions/multi_model 死键、TOOL_PACKS 死工具名） |
| TTS（edge-tts 免费链） | 📋 可选 | 框架完整四缺装配；半天工作量；体验优先级用户未排 |
| QQ 体检命令 / /git 命令 | ❌ 已取消 | 见 HANDOFF §D 决策记录 |

---

## 7. 快速上手

```bash
# 远程（Git Bash；IP/实例 ID 见 docs/LOCAL_INFRA_PRIVATE.md）
workbench exec --instance-id <ID> --region cn-beijing --command "..."
MSYS_NO_PATHCONV=1 workbench upload "$(cygpath -w 本地)" 远端 --force

# 部署三件套
备份 → tar -xzf → （依赖变更 uv sync --no-group dev 并确认装上）→ restart → post_deploy_check.sh

# 本地
pytest tests/unit/ -q -p no:cacheprovider    # 321 passed 基线
python scripts/doctor.py --runtime           # FAIL=0 基线

# 排障入口
journalctl -u miya-daemon -f                 # 弥娅
docker logs -f napcat                        # QQ 侧
tail -f C:/Users/Ran-xin/pc-time-tracker/logs/autostart.log   # PC Timer（[EXIT] 标记=崩溃留痕）
```

**防坑四条**：①删"疑似死配置"前必须全仓 grep 反验证（动态键/json.dumps 枚举消费）；②外层 try/except 包批量循环=单点失败静默吞整批，新代码一律 per-item 隔离；③"配置声明面"≠"消费路由面"，加条目后验收必须穿透到"模型实际拿到的工具数量"（journalctl `开始聊天 (工具数量: N)`）；④health 200 ≠ 一切正常，桥接/会话以 `doctor --runtime` + `docker logs napcat` 为准。

---

## 8. 本地敏感信息索引（不入 git）

以下信息存于 `docs/LOCAL_INFRA_PRIVATE.md`（本地-only，gitignore 已覆盖）：服务器公网 IP、ECS 实例 ID、superadmin 与机器人 QQ 号全量、API Key 名单、SSH 密钥路径、workbench 命令完整参数。新对话需要这些信息时向用户索取或读该文件。
