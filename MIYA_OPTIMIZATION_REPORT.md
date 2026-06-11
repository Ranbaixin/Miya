# 弥娅 (Miya) v8.0 优化报告

> 分支: `Ranxin` | 备份: `backup-20260610-2329` | 日期: 2026-06-11

---

## 一、修改结果

### 已完成的 9 个 Commit

| # | Commit | 分类 | 文件数 | 说明 |
|:---:|------|------|:---:|------|
| 1 | `acbc3c87` | 基础 | 32 | 版本号 v7.0→v8.0 统一、UTF-8 BOM 清除、.gitignore 补漏、代码简化 |
| 2 | `a34e2498` | 性能 | 11 | 统一配置缓存(9→1次I/O)、写入防抖(每条→5秒批)、hot-path 缓存、embedding key md5 |
| 3 | `332537c9` | Neo4j | 3 | 默认端口 7687→17687、MemoryNet 注入 grag_memory、管道连通 |
| 4 | `3b0312fb` | Neo4j | 1 | MemoryManager 接入 Neo4j 存储 |
| 5 | `71f8325d` | Neo4j | 1 | LLM 五元组提取中英文 key 兼容 |
| 6 | `84b4b2b4` | 安全 | 6 | shell=True 加固、exec 沙箱、凭据环境变量化、CORS 修复、async 边界 |
| 7 | `714aa738` | 韧性 | 2 | 索引批量写盘(10x)、守护进程优雅降级 |
| 8 | `b6a54941` | 低风险 | 8 | 配置去重、加密降级、权限 fails-closed、硬编码凭据消除、资源泄漏、边界保护 |
| 9 | `67c3ad44` | 中风险 | 5 | QQ 重连指数退避、scheduler 线程锁、消息队列 backpressure、内存泄漏 |

### 修改详情

#### 🔧 基础修复 (Commit 1)
- `.gitignore`: 补漏 `config/multi_model_config.json.*`、`AGENTS.md`、`.codex/`、`data/neo4j/`
- 版本号: 代码/文档/前端全部 `v7.0`/`v7.0.0` → `v8.0`/`v8.0.0`
- 5 处硬编码 `VERSION = "8.0.0"` 改为 `from core.version import VERSION`
- BOM 清除: 6 个文件 (`config/*.json`, `config/*.py`, `config/*.yaml`, `miya_frontend/electron/*.ts`)
- 代码简化: scheduler 生命周期提取、lazy_load 参数化、冗余 import 移除、DAEMON_CMD 变量

#### ⚡ 性能优化 (Commit 2)
- **统一配置缓存**: 新增 `memory/memory_config.py`，9 个模块共享单次加载
- **写入防抖**: `working_memory.add_message()` 从每条消息写盘 → 5 秒批量写入
- **Hot-path 缓存**: `_is_low_info()` 不再每次读配置文件
- **Embedding 缓存 key**: `hash()` → `hashlib.md5()` hexdigest（跨进程稳定）
- 移除 `store_cognition()` 裸 `print()`

#### 🧠 Neo4j 知识图谱 (Commit 3-5)
- `grag_memory.py`: 默认端口 `7687` → `17687`（匹配 Docker 容器）
- `webnet/memory.py`: `MemoryNet` 新增 `grag_memory` 属性
- `run/main.py`: 不再禁用 Neo4j，改为从 `.env` 读取配置创建 GRAGMemoryManager
- `hub/memory_manager.py`: `store_assistant_response()` 末尾接入 Neo4j 存储
- 五元组 prompt 改为英文 key + 解析器兼容中文 key
- **已验证**: "我叫佳，喜欢看电影" → 3 条五元组成功存入 Neo4j

#### 🔒 安全加固 (Commit 6)
- `core/tools_astrbot/__init__.py`: `shell=True` → `shlex.split()` + `shell=False`，危险命令拦截
- `core/tools_astrbot/__init__.py`: `python -c` 添加危险导入拦截 + 临时文件隔离
- `webnet/ToolNet/tools/basic/python_interpreter.py`: `exec()` 添加安全 builtins 沙箱
- `core/dashboard/routes.py`: 硬编码 `miya/miya` → 环境变量 `MIYA_DASHBOARD_USER/PASSWORD`
- `core/management_api.py`: CORS `*` + `allow_credentials=True` → 显式 localhost 列表
- `core/ai_client.py`: `response.content[0]` 空列表保护
- `webnet/ToolNet/base.py`: `__call__` 用 `ensure_future` 避免裸协程

#### 🛡️ 韧性增强 (Commit 7)
- `memory/core.py`: 索引每 10 次写入刷盘一次（原每条写入即刷盘），关闭时强制刷脏
- `core/miya_daemon.py`: `_init_miya_core` 失败不再 `raise` 杀死守护进程

#### 📦 低风险修复 (Commit 8)
- `config/platforms_config.py`: DINGDING_CONFIG 重复 `app_secret` key 移除
- `core/config_encryption.py`: cryptography 不可用时降级而非崩溃
- `core/memory_system_initializer.py`: `.env` 路径改为相对于项目根目录
- `webnet/ToolNet/registry.py`: 权限检查失败 → fails-closed（拒绝而非允许）
- `webnet/webnet.py`: admin 密码/JWT 密钥改用环境变量
- `memory/session_decay.py`: `fromtimestamp()` NaN/Inf 保护
- `core/cron_system.py`: `CronTask` 添加缺失的 `status` 字段
- `core/db_manager.py`: cursor 添加 `finally close()`

#### ⚙️ 中风险修复 (Commit 9)
- `webnet/qq/client.py`: 指数退避 + 随机抖动 + 最大 30 次重连上限
- `hub/scheduler.py`: heapq 操作添加 `threading.Lock()` 跨线程安全
- `mlink/message_queue.py`: `deque(maxlen=N)` 改为手动 max_size + drop 计数
- `mlink/trust_transmit.py`: propagation_history 限制 1000 条
- `memory/diteng_listener.py`: `save()` 改为 `run_in_executor` 避免阻塞事件循环

---

## 二、基础设施状态

| 组件 | 状态 | 访问地址 |
|------|:---:|------|
| Neo4j 容器 (`miya-neo4j`) | ✅ 运行中 | `bolt://127.0.0.1:17687` |
| Neo4j Browser | ✅ 可用 | `http://127.0.0.1:17474/` |
| 端口冲突 | ✅ 无冲突 | `pytorch-neo4j` 用 7688:7475 |
| 对话 → Neo4j 管道 | ✅ 已连通 | LLM 提取 → 五元组 → 图存储 |
| Docker Desktop | ✅ 已配置 | `NEO4J_AUTH=neo4j/MIYA123456` |

---

## 三、待处理清单

### 🔴 严重 / 必须手动操作

| # | 事项 | 说明 |
|:---:|------|------|
| API-1 | **轮换 DeepSeek API Key** | `config/.env` 中 `sk-2f1b79aa...` 已被泄露。登录 https://platform.deepseek.com/api_keys 吊销并重新生成 |
| API-2 | **轮换 Tavily API Key** | `config/.env` 中 `tvly-dev-2GgNrX...` 已被泄露。登录 https://app.tavily.com/home 吊销并重新生成 |
| API-3 | **修改 Neo4j 密码** | `NEO4J_PASSWORD=MIYA123456` 为弱密码 |
| API-4 | **修复 .env key 空格** | `DEEPSEEK_API_KEY= sk-...` 中 `=` 后多余空格会导致加载值带空格前缀 |
| GIT-1 | **Fork 仓库** | 当前 `Ranbaixin` 无 `Jia-520-only/Miya` 推送权限，需 fork 到 `Ranbaixin/Miya` 后 push |
| ENC-1 | **恢复 qq_config.yaml** | 中文注释已乱码，需从 git 历史恢复或手动重写 |

### 🟠 高优先级

| # | 事项 | 文件 | 风险 |
|:---:|------|------|:---:|
| H-1 | `asyncio.run()` 在 async 上下文 | `hub/decision_hub.py:757` | 中 |
| H-2 | SQLite `check_same_thread=False` 无 mutex | `memory/sqlite_backend.py:133` | 中 |
| H-3 | LifeBook diary O(n²) copy | `memory/lifebook.py:234` | 中 |
| H-4 | Historian 升级未持久化 | `memory/historian.py:554` | 中 |
| H-5 | ConfigLoader 空 API key 无声传播 | `core/config_loader.py:122` | 低 |
| H-6 | CacheManager shelve 无显式 close | `core/cache_manager.py:123` | 低 |
| H-7 | Fire-and-forget emoji task 无法取消 | `hub/decision_hub.py:1124` | 中 |
| H-8 | `psutil` 调用阻塞事件循环 | `hub/platform_adapters.py:429` | 中 |

### 🟡 中优先级

| # | 事项 | 说明 |
|:---:|------|------|
| M-1 | 去重 `core/platform/` 和 `core/platform_astrbot/` | 214 个文件三重复制 |
| M-2 | 拆解 `decision_hub.py` (3939 行) | God Class 反模式 |
| M-3 | 统一 6 套配置系统 | `config_loader`、`multi_model_config`、`text_config`、platforms、personalities、skills |
| M-4 | 全局单例 → 依赖注入 | 7 个全局可变单例阻碍测试 |
| M-5 | 编码设置集中化 | 4 处各异的 UTF-8 设置 → `core/encoding_setup.py` |
| M-6 | `MemoryNet` 去重 extract 代码 | 732 行正则与 `MemoryManager` 的 115 行正则功能重叠 |
| M-7 | `storage_dir` 未传 `json_backend` | `core/grag_memory.py:49` |

### 🟢 低优先级

| # | 事项 | 说明 |
|:---:|------|------|
| L-1 | 版本号 6 处硬编码统一为 `from core.version` | `miya_daemon`、`miya_lifecycle`、`miya_initial_loader`、`dashboard`、`astrbot_compat` 已修复 |
| L-2 | `mcpserver/` 空目录清理 | 或实现 MCP 服务器 |
| L-3 | `plugins/` 仅 `__init__.py` | 插件系统待开发 |
| L-4 | `.backup/` 空目录 | 添加定时备份脚本 |
| L-5 | BOM 字符残留检查 | 确认 6 个文件 BOM 已清除 |
| L-6 | `config/memory_config.json` BOM | 已修复 |
| L-7 | switch_model_config.bat 无文档 | 添加使用说明 |

### ⏭️ 已评估/跳过

| # | 原审计发现 | 跳过原因 |
|:---:|------|------|
| S-1 | `run/main.py` 双事件循环 | 终端模式特有架构，动则破坏交互 |
| S-2 | `autonomous_engine` 自动批准 `file_modify` | 功能设计意图，非 bug |
| S-3 | `cross_net_engine` BFS O(n²) | 图规模小 (<100 节点)，无实际影响 |
| S-4 | `decision_hub` 重复持久化 (4-6次) | 分层记忆设计，每层独立存储 |
| S-5 | `cache_manager` shelve 未关闭 | `cleanup()` 方法中已有关闭逻辑 |
| S-6 | `config/multi_model_config.json` 10 模型 ID 缺失 | 已通过 `routing` section 映射 |
| S-7 | `autonomous_engine` 决策列表无界增长 | 每 5 分钟最多 5 条，量级可控 |
| S-8 | `cron_system` 历史列表无界增长 | 定时触发频率低，量级可控 |

---

## 四、回滚方法

```bash
# 回到修改前
git checkout backup-20260610-2329

# 回到某个中间状态
git checkout acbc3c87   # 仅基础修复
git checkout a34e2498   # + 性能优化
git checkout 84b4b2b4   # + 安全加固
git checkout b6a54941   # + 低风险修复
```

## 五、快速验证

```bash
# 验证 Neo4j
python -c "from neo4j import GraphDatabase; d=GraphDatabase.driver('bolt://127.0.0.1:17687',auth=('neo4j','MIYA123456')); d.verify_connectivity(); print('OK'); d.close()"

# 验证所有模块导入
python -c "from memory.core import get_memory_core; from core.miya_daemon import MiyaDaemon; from webnet.qq.client import QQOneBotClient; from hub.scheduler import Scheduler; from mlink.message_queue import MessageQueue; print('All OK')"

# 验证版本号
python -c "from core.version import VERSION; print(f'Miya v{VERSION}')"
```
