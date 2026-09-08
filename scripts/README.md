# scripts/ — 运维与验证脚本

统一用 `uv run python -X utf8 scripts/<脚本>.py` 执行（Windows 必须 `-X utf8` 防 GBK 崩溃）。

## 质量与验证（提交前跑）

| 脚本 | 作用 | 基线/白名单文件 |
|---|---|---|
| `smoke_test.py` | 9 阶段冒烟：S0 编译→S1 导入图→S2 冷导入→S3 配置→S4 平台注册→S5 核心构造→S6 链路探针→S7 日志白名单差分→S8 数值基线。`--fast` 跳过 S5/S6；`--write-baseline` 重建基线 | `.smoke_baseline.json`；日志白名单=脚本内 `DEFAULT_LOG_WHITELIST`（可用 `.smoke_log_blacklist.json` 覆盖） |
| `import_graph.py` | 模块可达图检查（`--check` 拦截误删；`--write-baseline` 重建） | `.import_baseline.json` |
| `check_imports_vs_requirements.py` | import 与依赖声明一致性（读 pyproject 全部依赖数组 + setup/dependencies） | 无 |
| `ci-check.bat` | CI 入口 | — |

**结构性删改后**（删模块/工具/配置）：S1/S8 会报「可达集缩小/基线不匹配」——确认变化符合预期后
`--write-baseline` 重建。运行期新增的已知无害 ERROR（如 Neo4j 未启动的连接拒绝）加进白名单。

**教训**：删除"死配置"前必须人工复核引用方式——`diteng_strategy_config.json` 曾因被路径
拼接引用而逃过 grep，误删后谛听策略失效、消息被静默丢弃（2026-09 事故，文件已恢复）。

## 构建类

| 脚本 | 作用 |
|---|---|
| `build_hud.sh` | 构建 frontend/ui（自动复制到无 `#` 临时目录绕过 Vite 路径缺陷，产物拷回 `frontend/packages/web/dist`） |
| `verify_hud_build.sh` | 仅验证 HUD 可构建（trap 自动清理临时目录），不部署产物 |
| `build_web_frontend.ps1` | 旧 Web 前端构建（`build_web_frontend.sh` 已删除——其目标目录无 package.json，属旧架构残留） |
| `patch_vite_realpath.mjs` | 把 vite 产物的 `realpathSync.native` 替换为非 native（项目路径含 `#` 时防白屏；已挂 miya_frontend 与 frontend/ui 的 postinstall，幂等可重跑） |

## 维护类

| 脚本 | 作用 |
|---|---|
| `scan_swallowed_exceptions.py` / `check_new_swallowed.py` | 异常吞噬扫描（PHASE9 配套） |
| `memory_health_check.py` | 记忆健康检查（daemon 后台引用，勿随意改名/移动） |
| `migrate_memory_to_neo4j.py` | 记忆图迁移（daemon 后台引用） |
| `init_*_anchors.py` | 记忆锚点初始化 |
| `encrypt_config.py` | 配置加密工具 |
| `scan_secrets.py` | 密钥泄漏扫描 |

## 约定

- 新脚本：argparse + `-X utf8` 兼容 + 失败返回非零退出码；长进程脚本必须可 Ctrl+C 干净退出。
- 会写仓库文件的脚本（基线/补丁）必须幂等。
- `daemon`/启动链引用的脚本路径（见 `core/miya_daemon.py`）变更时同步更新引用方。
