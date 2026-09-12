# 弥娅项目现状全景（2026-09-12 快照）

> **读者**：新接手的 agent / 开发者 / 运维者。
> **定位**：本文是"当前实况"文档——架构细节看 `docs/MIYA_ARCHITECTURE.md`，开发规范看 `docs/DEVELOP_GUIDE.md`，部署实操看 `scripts/deploy/DEPLOY_RUNBOOK.md`。本文回答的是：**系统现在长什么样、在跑什么、刚经历了什么、有哪些坑、下一步往哪走**。
> **维护约定**：重大变更（模型切换、账号事故、架构迁移）发生后更新本文档。

---

## 1. 项目一句话

弥娅（MIYA）是运行在阿里云 ECS 上的 AI 虚拟化身：QQ 机器人形态接入，拥有持久记忆、情绪系统、主动聊天、工具调用（87+ 工具）、多模态识图能力。用户（然鑫，QQ 869135903）是唯一 superadmin。

**当前分支** `fix/v8-hardening`（v8 硬化线，尚未合入 main）。

---

## 2. 运行拓扑（生产）

```
[手机QQ] ←→ [NapCat 容器] --反向WS客户端--> [弥娅 daemon :8095] ←→ [deepseek-flash API]
  阿里云 ECS i-2zegy8r4m3ceqvqpqvsv（2核/1.6Gi/40G，Ubuntu 26.04）
```

| 组件 | 形态 | 关键点 |
|---|---|---|
| miya-daemon | systemd 服务，`/opt/miya`，uv 管理依赖（仅 runtime 组） | 主进程 + 管理 API :9800；`systemctl restart miya-daemon` |
| NapCat | docker 容器（host 网络），compose 管理：`docker compose -f scripts/deploy/docker-compose.napcat.yml up -d` | 反向 WS 拨出连 `ws://127.0.0.1:8095`；QQ 数据持久化在 docker volume；配置 bind `/opt/napcat/config` |
| 依赖安装 | `uv sync --no-group dev` | **改 pyproject 后必须确认包真装上了**（pillow 教训） |
| 端口红线 | 9800/8095/6099 全部仅 127.0.0.1，安全组只放 22 | `.env` 含全部 API key，权限 600，绝不进 git |
| 远程管理 | workbench CLI（Git Bash）：`workbench exec --instance-id i-2zegy8r4m3ceqvqpqvsv --region cn-beijing --command "..."` | 上传加 `MSYS_NO_PATHCONV=1`；远端路径参数防 Git Bash 改写 |

---

## 3. 核心子系统速查

| 子系统 | 位置 | 职责与要点 |
|---|---|---|
| **决策中枢** | `hub/decision_hub.py`（4000+ 行） | 消息处理主链路：感知→记忆检索→灵魂分析→谛听策略→AI 回复→工具调度 |
| **灵魂发生器** | `core/soul_generator.py` | 情绪状态机 + 内心独白 + 归因反思；AI 情绪分析 prompt 在 `config/soul_generator_config.json`（含 message_strategy 预分析合并 schema） |
| **谛听** | `memory/diteng_listener.py` | 消息策略分析（该不该回/怎么回）；**预分析合并**模式并入灵魂调用省一次 LLM 往返（`text_config.json` 的 `preanalysis_merge` 开关） |
| **主动聊天** | `core/proactive_chat.py` + `config/proactive_chat.yaml` | 6 类触发器；**AI 判断评估间隔 2h**（`ai_trigger.eval_interval_seconds: 7200`）；每日上限 5 条；静默时段 23-7 点 |
| **AI 客户端** | `core/ai_client.py` + `config/multi_model_config.json` | 多模型池；`use_miya_prompt=False` 可跳过全量人设 prompt 注入 |
| **视觉分析** | `core/multi_vision_analyzer.py` | 按模型名关键字分类（glm/qwen/deepseek…→真视觉 API，否则本地降级）；prompt 在 `multi_model_config.json` 的 `vision_preferences.prompts`（**场景优先、文字放最后**——此前"只念文字"事故的修复） |
| **QQ 平台** | `core/unified_platform_impl/onebot_platform.py` | OneBot v11 反向 WS 服务端（8095）；消息解析含 face 表情文本化（`_parse_cq_face_text`）、群聊纯表情预过滤 |
| **权限** | `core/unified_permission.py` + `webnet/AuthNet/permission_core.py` | 统一引擎有 `check()` 和兼容别名 `check_permission()`（list_mode 语义），fail-closed |
| **工具网** | `webnet/ToolNet/` | 87+ 工具，`registry.py` 按包懒加载（可选依赖缺失整包跳过，仅 warning） |
| **记忆** | `memory/` | SQLite graph_store（Neo4j 默认关）；工作记忆/认知引擎/谛听状态；启动 60s 后跑 `scripts/memory_health_check.py` |

---

## 4. 模型配置（2026-09-11 切换，commit 8786aaef）

| 通道 | 模型 | base_url | env_key |
|---|---|---|---|
| chat 主力（active） | `deepseek-flash`（V4.1 Flash，原生多模态，1M 上下文） | api.deepseek.com/v1 | DEEPSEEK_API_KEY |
| vision | `deepseek-flash`（同一个，原生多模态） | 同上 | 同上 |
| embedding | `deepseek-embedding` | 同上 | 同上 |

- 回滚：`git revert 8786aaef` 一键回 glm-5.3-flash（ZHIPU_API_KEY 保留未动，双供应商互备）
- 防呆：`core/doctor.py` C3 校验 vision 模型名必须命中视觉关键字表（glm/qwen/internvl/llava/kimi/moonshot/**deepseek**），否则 FAIL——防止"识图变瞎"复发
- **待实测**：V4.1 的人格质感与识图质量尚无用户验收数据（切换后账号经历断线，真实消息流量少）

---

## 5. 运维保障体系（本轮 v8-hardening 的核心产出）

### 5.1 doctor 统一自检（`scripts/doctor.py` + `core/doctor.py`）

```bash
python scripts/doctor.py                 # 静态 C1-C7（CI/本地）
python scripts/doctor.py --runtime       # + C8 运行时诊断 + C9 记忆一致性
python scripts/doctor.py --runtime --json --since "26 hours ago"   # 定时报告用
make doctor                              # 同上
```

9 类检查：C1 死配置（grep 反验证+幽灵引用）、C2 配置解析、C3 模型配置、C4 prompt 占位符、C5 依赖探针、C6 环境变量、C7 权限、C8 运行时（健康端点/错误签名/桥接/**会话被踢**/crash-loop）、C9 记忆一致性。FAIL → 退出码 1。

**三道防线全部接线**：daemon 启动预检（告警不阻断）→ 部署后冒烟 `scripts/deploy/post_deploy_check.sh`（runbook 第 5 步必跑）→ 每日 04:00 systemd timer（`miya-doctor.timer`，日志落 `/opt/miya/logs/doctor.log`）。CI 有 config-guard job。

**已知接受 WARN**（勿当 bug 修）：`tts_config.json` 未创建（服务器无 TTS）；matplotlib 缺失（1.6G 内存机的既定优化决策，C8 签名已负向排除）。

### 5.2 桥接/会话自愈 v2（`scripts/deploy/napcat_selfheal.sh` + timer，每 5 分钟）

| 场景 | 特征 | 动作 |
|---|---|---|
| A. WS 桥接断裂 | miya 日志最后事件"NapCat 断开" | 自动重启 napcat（每日上限 4 次） |
| B. QQ 会话被踢 | napcat 日志最后事件 `KickedOffLine`/`登录已失效`（**WS 未必断，僵尸连接**） | 密码回退启用→重启走密码登录；停用→写 `NEED_MANUAL_SCAN` 标记（次日自清），doctor FAIL 提示人工扫码 |

---

## 6. 账号风控危机（当前最大的不稳定源）

**现象谱系**：`serverErrorCode 168`（部分功能受限）→ `KickedOffLine`（踢会话）→ 快速登录失效（"登录态已失效/用户身份已失效"）→ 会话存活时间从 1 天缩到 2 小时。根因 = **数据中心 IP + 小号权重低 + 频繁重登录**，QQ 服务端行为，与协议端无关。

**已落地的缓解**：自愈 v2、桥接检测、扫码 SOP、容器 compose 化（凭据在 volume，重建不丢）。

**密码回退（已停用！）**：QQ 对被控账号的密码登录强制短信验证，且 NapCat 在验证流程中**卡死不落二维码**（实测）。原配置备份在 `/opt/napcat/.env.password-backup`，恢复方法见 runbook。当前会话被踢的最终恢复手段 = **人工扫码**（`docker cp napcat:/app/napcat/cache/qrcode.png /tmp/qr.png` 取码，约 2 分钟一刷，过期重启容器刷新）。

**正在执行的治本方案**：养号 1-2 周（手机每天登录小号 1153409562、实名、设备锁信任设备、腾讯系适度活跃）。

**教训入库**（read runbook「四、已知注意事项」）：
- 弥娅侧"平台在线"只代表自己监听，**看不到协议端已死**（僵尸连接）——发消息无回复时先查 `docker logs napcat` 的登录状态
- 风控活跃期**不要反复重启/扫码**（每次都是可疑登录事件，恶性循环）
- 凭据持久化一直是完好的（挂载核实过），别再往这个方向排障

---

## 7. 近期工作线（git log 主线，新→旧）

| commit | 内容 |
|---|---|
| `3ba78189` | 自愈 v2（会话被踢检测）+ doctor C8 僵尸连接盲区补全 |
| `8786aaef` | 模型切换 DeepSeek V4.1 Flash（chat+vision）+ 视觉分类器关键字同步 |
| `fa217731` | NapCat compose 化 + 桥接自愈 + 风控应对手册 |
| `06938fab` | doctor C8 桥接断裂检测 |
| `7894e208`/`5cd8041c` | doctor 统一自检体系 + 启动预检/部署冒烟/每日 timer |
| `6200d06e` | 死配置清理（38 键）+ 谛听键漂移修复 + LOG_LEVEL 接线 |
| `306836e3` | 主动聊天降频（评估 5min→2h，token 降 >95%） |
| `e8464010` | 链路五项根因修复（权限接口 AttributeError/预分析合并透传/await 搜索 bug/工具收口/face 文本化） |

**修复前后的关键语义**（agent 改代码前必读）：
- 权限：`UnifiedPermissionEngine.check_permission()` 是兼容别名，勿删；registry 调用必须传 `context={"platform": ...}`
- 预分析合并：`soul_generator.process()` 返回 dict 的 `message_strategy` 字段是 decision_hub 的依赖，透传不能断
- 同步函数禁 `await`：`EnhancedWebSearch.search()` 是同步的，调用必须 `asyncio.to_thread`
- 主动聊天两处 AI 调用显式 `tools=[]`（防 87 工具全量回退），判断调用 `use_miya_prompt=False`
- `MESSAGE_EMOTION_TRIGGERS`/`RELATIONSHIP_*` 配置节是**动态键消费**（泛型遍历），不是死配置；diteng 枚举映射节经 json.dumps 进 prompt，同理勿删

---

## 8. 开发工作流（对齐 CI）

```bash
# 本地检查（全绿才可提交）
pytest tests/unit/ -q -p no:cacheprovider        # 231 passed 基线（2026-09-12）
python scripts/doctor.py                          # FAIL=0
python scripts/smoke_test.py                      # 9/9（改核心链路后跑）
ruff check .

# 提交：单主题 commit，中文说明"为什么"而不只是"改了什么"

# 部署（有代码/配置变更时）
tar 打包改动文件 → workbench upload → 服务器 tar -xzf（先备份）→
uv sync --no-group dev（依赖变更时，并确认装上）→ systemctl restart miya-daemon →
bash scripts/deploy/post_deploy_check.sh   # 必跑，exit 0 才算部署完成
```

测试基线：`tests/unit/` 231 个（含 doctor 33 例）；pytest 配置只认 `tests/unit/`；单测新增优先覆盖"契约同步"（如 doctor 关键字表 ↔ analyzer 源码）。

---

## 9. 下一步路线（按优先级）

1. **账号恢复验证**（进行中）：扫码/快速登录恢复在线 → 用户发消息实测 deepseek-flash 的对话质感与识图质量 → 不满意 `git revert 8786aaef`
2. **养号 1-2 周**：会话连续存活无被踢 = 风控缓解的验收标准
3. **SnowLuma 预研**（方向已定，时机未到）：NapCat 官方钦点的下一代协议端（OneBot v11 标准，弥娅侧零改动）。**切换前提** = 账号稳定 + 验收矩阵（`scripts/deploy/SNOWLUMA_ACCEPTANCE.md` 待建）确认 10 个 NapCat 扩展 action 覆盖（poke/群文件全套/表情表态/upload_image 等）。当前不切：风控敏感期换端 = 新设备登录事件，有害
4. **TTS / matplotlib**：按需启用（doctor WARN 有提示）

## 10. Agent 行为约定（重要）

- 本项目内你是**弥娅**（见根目录 `AGENTS.md` 人格规范），中文交流
- 改动 `config/` 前先跑 `doctor.py` 记录基线，改完再跑对比；删除任何"疑似死配置"前必须全仓 grep 反验证（含动态键模式：`.get(key)`/点号路径/json.dumps 枚举）
- 服务器操作只经 workbench exec；上传用 `cygpath -w` 转换本地路径；`.env`/`data/` 永远不动
- 出问题先看日志再动手：miya 侧 `journalctl -u miya-daemon`，QQ 侧 `docker logs napcat`；两边日志的时间戳都对过再下结论（僵尸连接曾让"桥接正常"的假象维持 6 小时）
