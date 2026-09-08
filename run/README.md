# run/ — 启动入口

| 文件 | 模式 | 说明 |
|---|---|---|
| `main.py` | 终端模式 | `Miya` 类是**全系统唯一核心构造链**（daemon 也复用它）；`amain` 交互循环；退出走 `ashutdown()` 完整关闭链。2026-09：移除死对象 arbitrator/NetManager/CrossNetEngine；AI 降级标记 `ai_degraded`；8000 挂统一鉴权网关 |
| `daemon.py` | 守护进程 | `MiyaDaemon` → 复用 `Miya()` → 平台注册 → 管理 API(9800)。CLI：`--api-port/--api-host/--platforms（仅已启用平台，未知 id 会报错）/--list-platforms`。优雅退出：`POST /api/v1/daemon/shutdown` |

两个入口共用 `Miya()` 构造；差异仅在：终端模式走 `_initialize_memory_net_async` +
交互循环，daemon 走 `memory_net.initialize()` + 平台注册 + 管理面。

启动菜单入口在根目录 `start.bat`（1 终端 / 2 daemon / 3 桌面 / 4 Web / a 全部；
3/4/a 会经 `:ensure_nohash` 做 subst 盘符映射规避路径 `#` 问题）。
