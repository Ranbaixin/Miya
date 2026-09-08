# 弥娅部署可行性实测报告（2026-09-08）

> 分支：`fix/v8-hardening`（HEAD: 17593768）· 测试环境：Windows 11 开发机 · Python 3.11.14 / .venv（runtime+dev）
> 结论：**开发机全流程跑通；2核2G/3M/40G 阿里云 99 元机"可部署"为基于开发机实测的资源推算，尚未在真实云服务器上验证**。数据边界见下。

> ⚠️ **数据边界声明（2026-09-08 晚补充）**：本报告所有"实测"数字（RSS/启动耗时/对话延迟/单测/冒烟）均来自 **Windows 11 开发机**，其中部分链路（OneBot）为模拟 NapCat。尚未在任何真实 Linux 云服务器上运行过；"部署资源总账"一节是推算值。首次服务器部署后应立即实测 RSS/启动耗时并与本报告对照。
>
> **2026-09-08 晚间二轮验收（记忆类人化 + 内存优化 + 图谱 SQLite 化）**：同机复测 daemon
> 空载 RSS **217MB → 55MB**，真实对话后 **100MB**；161/161 单测、smoke 5/5、优雅停机 exit 0
> 全过。详见文末「六、二轮验收记录」。

## 一、全流程测试结果

| 阶段 | 内容 | 结果 |
|---|---|---|
| P1 单元回归 | `pytest tests/unit/ -q` | ✅ 132/132 通过（18s），含新增的校准/稳定画像/SQLite标签/上下文截断测试 |
| P2 冒烟 | `scripts/smoke_test.py --fast` | ✅ 5/5（compileall/导入图/冷导入/配置/平台注册） |
| P3 headless 启动 | `run/daemon.py --api-port 9800` | ✅ 就绪 **14s**；9800/8000/8095 三端口健康；aiocqhttp online、0 错误 |
| P4 端到端对话 | `POST 8000/api/chat`（真实 LLM） | ✅ 16s 返回带人格回复；deepseek-v4-flash 预算路由生效 |
| P5 OneBot 链路 | 模拟 NapCat（反向 WS） | ✅ 拍一拍（即时文字+表情包+AI 情感回复）与私聊文本（send_msg 回复帧）全通 |
| P6 优雅停机 | `POST 9800/api/v1/daemon/shutdown` | ✅ 进程 exit 0，端口全部释放（审计 F-1/F-5 悬挂问题未复现） |

### 日志锚点命中（本次提交新链路验证）
- `[预算] 首请求` S4 分段预算：✅（见问题 2）
- `[稳定画像] 白名单命中 N 条，双轨去重后 M 条`：✅（新用户 0 条，隐私逻辑正常）
- `[校准] deepseek-v4-flash 估算 N → 实际 M 已记录`：✅
- `[认知引擎] 检索到 N 条相关记忆（MMR去重后）`：✅
- `[记忆管理器] 收到消息` / `[智能记忆检索]` / `[灵魂记忆]`：✅

## 二、实测数据（部署判定依据；全部为 Windows 开发机数据，非云服务器）

| 指标 | 实测值（本机） | 说明 |
|---|---|---|
| daemon 就绪耗时 | **14s**（Windows） | 远低于审计记录的 ~60s；systemd TimeoutStartSec=300 仍建议保留 |
| 空载 RSS | 一轮 **217MB** → 二轮 **55MB** | 2026-09 晚间优化后复测（pandas/顶层重依赖懒加载 + SQLite 缓存收敛） |
| 对话后内存 | 一轮 RSS 71~217MB → 二轮 **~100MB** | 二轮为首条消息后（LLM 客户端加载 +45MB 一次性）；commit 含虚拟内存上界，2G 服务器看 RSS，留 swap 兜底即可 |
| 首条消息延迟 | ~16s（含记忆检索+预算日志+LLM） | 后续同会话更快（协作引擎处理 1.3s 级） |
| 消息流量 | 文本 KB 级 | 3M 带宽无压力 |
| 依赖体积 | .venv 515MB（runtime+dev） | 2026-09 起 `uv sync` 默认仅 runtime 组（更小）；测试/开发用 `uv sync --group dev`；**勿用 requirements.txt（拉 CUDA torch）** |
| 数据体积 | data/ 不含 neo4j 约 110MB | neo4j 目录 517MB（514MB 事务日志，真实图数据 <1MB）可归档后删除（图谱已 SQLite 化） |

### 部署资源总账（2核2G / 3M / 40G）—— ⚠️ 推算值，非服务器实测
| 组件 | 内存（推算） | 磁盘（推算） |
|---|---|---|
| Ubuntu 22.04/Debian 12 + 阿里云 agent | ~250MB | ~4GB |
| Docker daemon | ~100MB | ~0.3GB |
| NapCat 容器（host 网络，反向 WS→127.0.0.1:8095） | ~200-400MB | ~1.5GB 镜像 |
| 弥娅 daemon（uv sync，默认 runtime 组） | ~60-150MB（二轮实测 55MB 空载 / 100MB 对话后） | 源码+venv ~0.6GB |
| 数据（迁移 config/ + data/，不带 neo4j） | — | ~0.15GB |
| **合计** | **~0.8-1.2GB / 2GB** | **~7GB / 40GB** |

标配动作：2G swap、防火墙只放行 22、8000/9800 改绑 127.0.0.1（当前默认 0.0.0.0）、设 `MIYA_API_TOKEN`、logrotate、`mkdir logs`（全新环境首启 F-28）。

## 三、本次测试发现的问题

1. **[已修复 2026-09 晚] 知识图谱异步协议错误**：原 `core/knowledge_graph.py` 把同步 neo4j Session 用于 `async with`，每次查询抛异常被吞返回空（"写得起、查不出"）。现已默认改走 **SQLite graph_store**（`memory/graph_store.py`，建在 miya_memory.db 的 kg_* 表），五元组写入与关键词/实体查询全链路可用；Neo4j 仅在 `MIYA_USE_NEO4J=1` 时启用双写。
2. **[中] S4 首请求预算超限**：system prompt ~14.9k tokens，首请求 total ~17.3-17.9k > 13k 预算线。Step 8 的分段日志正是为此服务——建议瘦身 system prompt 或调预算。
3. **[低] `AIOCQHTTP_CONFIG` 缺 `bot_qq` 键**（config/platforms_config.py:325-334）：平台靠事件 `self_id` 识别自己。真实 NapCat 无影响；建议加 `"bot_qq": _env("QQ_BOT_QQ")` 增强健壮性。⚠️ 排障提示：自造 OneBot 事件时 user_id 不能等于 self_id，否则被"自身消息过滤"（onebot_platform.py:586）静默丢弃。
4. **[低] token 估算偏大 ~2.4x**（估算 18412 → 实际 7683）：校准闭环正在记录，后续可用校准系数修正预算。
5. **[既有，公网部署红线] 8000 端口无鉴权 RCE（SEC-1）+ .env 可读（SEC-2）+ 9800 WS 绕过（SEC-4）**：防火墙 + 绑 127.0.0.1 + token，三者缺一不可。
6. **[既有] 日志无轮转**：按天建文件永不删除，上 logrotate。

## 四、可选项预计表

| 可选项 | 内存 | 磁盘 | 带宽/费用 | 建议 |
|---|---|---|---|---|
| 知识图谱 GRAG | **0（默认 SQLite graph_store，进程内）** | 数据在 miya_memory.db | LLM 五元组提取按需 | 默认即用；Neo4j（+0.8~1GB）仅 `MIYA_USE_NEO4J=1` 时启用，2G 机不推荐 |
| 本地 embedding（torch+MiniLM） | +0.7~0.9GB | +2~2.5GB（CPU torch ~1.8G+模型 ~0.5G） | 首次加载 10-30s | 不推荐本地；**云端 embedding API**（SiliconFlow/智谱，按量 ~0.001 元/千token）零内存 |
| Redis | +30-50MB | ~50MB | 无 | 不装（代码有 Mock 路径，非必选） |
| Milvus | +2GB+ | +2GB+ | 无 | 排除 |
| Ops Center HUD 面板 | 0（静态文件由 8000 托管） | 已预构建 dist | 外网访问需反代+鉴权 | 本机/隧道访问零成本；不开公网 |
| TTS 语音（edge-tts） | ≈0（云端合成） | 缓存少量 | +50-150KB/条语音 | 可开（免费） |
| 本地 STT（funasr-onnx） | +300-800MB | +1GB | 无 | 2G 不建议；用云端 ASR 替代 |
| playwright MCP（config/mcp.json） | +200-300MB（npx 常驻+浏览器） | +500MB | 无 | 服务器清空 mcp.json |
| 主动聊天/自主引擎 | 已内置（45s/300s 轮询） | — | LLM 调用按需 | 默认即可，CPU 可忽略 |
| 阿里云快照备份 | 0 | — | 40G 盘 ~6 元/月内 | 建议开；99 计划已送 100GiB 文件备份+主机安全 |

## 五、上线步骤（半天工作量）

1. 重装系统（Ubuntu 22.04/Debian 12）→ 2. 建 2G swap + 安全组只留 22 → 3. 装 uv，clone + `uv sync`（默认仅 runtime 组；跑测试另加 `--group dev`）→ 4. 迁 `config/` + `data/`（不带 data/neo4j；补 `MIYA_API_TOKEN`、`mkdir logs`）→ 5. systemd unit 启动 daemon（`--api-host 127.0.0.1`），记录 RSS → 6. Docker 装 NapCat（host 网络）→ 7. SSH 隧道开 WebUI(6099) 扫码登录专用小号 → 8. NapCat 配反向 WS `ws://127.0.0.1:8095` → 9. 大号发消息端到端验证 → 10. logrotate + 快照，收工。

## 六、二轮验收记录（2026-09-08 晚：记忆类人化 + 内存优化 + 图谱 SQLite 化）

### 6.1 变更清单

**记忆类人化（Phase A）**
- A1 遗忘接线：daemon 启动 `start_cleanup_task()`（每小时过期删除 + 90 天对话归档 + 低优先级衰减，归档改走磁盘索引，冷启动后真正生效）；store 时短期记忆超 `memory_capacity.short_term_max_items`（默认 1000）裁剪最旧低优先级。
- A2 艾宾浩斯衰减：检索打分 30 天线性 → `exp(-0.05/天)` 指数衰减；`access_count` 高的记忆衰减更慢（间隔重复）；检索命中联动回忆强化（`on_memories_accessed`，权重表带 2000 条容量保护）。
- A3 情绪加权：`emotional_tone` 非空 +0.10、`significance≥0.7` +0.15（`cognitive_engine.recall_weights` 可配）；store 侧情绪强度 >0.7 的记忆 priority+0.2。
- A4 联想召回：MMR 后 top-3 每条经 memory_links.json 带最多 2 条一跳关联，二次 MMR；上下文标注"（由「…」想起）"；无链接零影响。
- A5 回忆模糊化：≥0.75 确定陈述 / 0.5-0.75"印象里" / 更低"好像…（不太确定）"；30~50 天旧记忆 ≤10% 概率以"很模糊的记忆碎片"浮现；时间措辞人类化（今天/昨天/上周/去年夏天左右）。
- A6 图谱 SQLite 化：新增 `memory/graph_store.py`（kg_entities/kg_edges 表，SPO 幂等 upsert）；GRAG 写/查默认走 graph_store；decision_hub 图谱上下文修复（原 Neo4j 读取链路全断）；Neo4j 仅 `MIYA_USE_NEO4J=1` 显式启用；daemon 的 Neo4j 迁移补课子进程默认关闭（`MIYA_ENABLE_NEO4J_MIGRATE=1` 开启）。

**内存优化（Phase B）**
- B1 SQLite cache_size -64000→-16000（库仅 4.8MB）。
- B2 runtime 依赖组移除 pandas/matplotlib/loguru/neo4j；`core/web_api/tools.py` pandas 改函数内懒加载；可选项 `core/entropy.py` 去 numpy（math 实现，core/__init__ 顶层导入不再拉 numpy）。
- B3 表情包语义标签先用 text_config 关键词表匹配，无命中才加载 jieba（避免常驻 +40~80MB）。
- B4 记忆 _cache 上限 5000/2500→1000/500；潮汐/梦境记忆 maxlen=200 + 写入时清理过期。
- B5 工作记忆 `max_recent_messages` 真正从 text_config（=5）读取（原写死 15）。
- B6 `default-groups=["runtime"]`（开发机/CI 加 `--group dev`）。
- B7 失效索引清理（数千次 stat）延后后台线程；daemon 两个启动子进程延后 60s。

### 6.2 验收证据

| 项 | 结果 |
|---|---|
| 单元测试 | **161/161 通过**（原 132 + 新增 29：容量裁剪/衰减打分/情绪加权/联想召回/模糊措辞/graph_store） |
| ruff / black | 全绿（触及文件 0 违规） |
| smoke --fast | 5/5（冷导入含 daemon/decision_hub/run.main） |
| headless daemon | 就绪、平台 1/1 在线、AI 客户端健康、`记忆清理循环已启动`、`知识图谱管理器已初始化（SQLite graph_store）`、60s 延后健康检查按期执行 |
| 真实对话 | `POST /api/chat` HTTP 200，带人格/情绪回复；认知引擎话题识别（情绪/开心）→ 检索 1 条 → 上下文注入 |
| 内存（同机同依赖对比） | 导入链空载 181.8→59.7MB；daemon 空载 **217→55MB**，首条消息后 **100MB** |
| 优雅停机 | shutdown API → exit 0，端口全释放 |
| 行为 demo | `scripts/memory_humanization_demo.py`：确定/印象里/好像 分档、联想标注、模糊片段、衰减与情绪打分全部生效 |

### 6.3 遗留事项

- **`data/neo4j/`（517MB）已实证为空库，可安全删除**（2026-09-08 晚验证）：用同版本 Neo4j 5.15.0 容器挂载副本启动，实测 **0 节点 0 关系**；256MB 事务日志全量扫描仅含 1 条占位测试文本（"用户说自己喜欢看电影"，6 月 4 日首次启动时写入），无任何真实知识写入与删除记录；主库 store 文件均为 8KB 空分配块。此前"94 条五元组 / 948KB 真实图数据"的说法系将空库文件分配大小误读为数据量，予以修正。graph_store 无需导入。验证操作全程仅在拷贝副本上进行，原目录未改动。
- 服务器迁移时勿拷贝 data/neo4j；`config/.env` 中的 NEO4J_* 已无效果（除非显式 `MIYA_USE_NEO4J=1`），可留可删。
- 首条消息 +45MB 为 LLM 客户端一次性加载，属正常；swap 兜底即可。
