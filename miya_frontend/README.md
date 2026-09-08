# miya_frontend — Electron 桌面端

弥娅桌面应用：Electron 主进程（`electron/`）+ Vue 3 渲染层（`src/`）+ Live2D 角色窗口（`src/live2d-app/`）。

## 启动 / 构建

```bash
# 推荐：从项目根 start.bat 选 3（自动处理 '#' 路径问题，见下）
# 手动等价：
npm run dev          # dev（默认尝试自动拉起后端；start.bat 3 会设 MIYA_NO_BACKEND=1 跳过）
npm run dev:web      # 仅渲染层（WEB_ONLY=1，不起 Electron）
npm run build        # 构建（dist/ + dist-electron/）
npm run dist:win     # 打包 Windows 安装包（electron-builder）
```

## ⚠️ 项目路径含 `#` 的规避机制（重要）

项目位于 `F:\#Ranxin\Miya` 时，Vite 把路径中 `#` 当 URL 锚点截断，且 Node 的
`realpathSync.native` 会穿透目录映射——模块解析必败（历史上表现为 `Could not resolve`、
`EISDIR read F:/`、渲染层白屏）。当前三层修复，**改构建相关代码前先理解**：

1. **subst 盘符**：`start.bat :ensure_nohash` 自动从 Z: 起找空闲盘符 `subst` 到项目根并从盘符路径启动。
2. **vite realpath 补丁**：`scripts/patch_vite_realpath.mjs` 把 vite 产物里的 `realpathSync.native`
   替换为非 native（对 subst 不穿透）。已挂 `postinstall`，`npm install` 后自动生效——
   **重装依赖后无需手动操作，但删掉 patch 脚本必复现白屏**。
3. **`vite.config.ts` 的 `hashPathFixPlugin`**：把仍带真实路径的模块 id 映射回盘符路径（第二道防线）。

根治方案是把项目迁到无 `#` 路径；迁移后可移除 1-3。

## 目录速览

| 路径 | 说明 |
|---|---|
| `electron/main.ts` | 主进程入口：窗口/托盘/快捷键/后端拉起 |
| `electron/modules/backend.ts` | spawn Python 后端（开发模式 `.venv/Scripts/python.exe run/daemon.py`；`MIYA_NO_BACKEND=1` 跳过） |
| `electron/modules/window.ts` | 主窗口（含渲染层 console 转发，dev 下渲染报错直接显示在终端） |
| `electron/modules/live2d-window.ts` | Live2D 窗口（注入 `__MIYA_API_PORT__=8000`） |
| `src/api/core.ts` | **业务 API 客户端（端口 8000**，`VITE_CORE_PORT` 可覆盖）；字段归一化在此层做 |
| `src/api/index.ts` | axios 封装：请求 snake_case ↔ 响应 camelCase 自动转换 |
| `src/composables/useMIYARealtime.ts` | WS 客户端（`ws://localhost:9800/api/v1/ws`，管理面事件） |
| `src/utils/session.ts` | 会话/消息本地状态；`loadCurrentSession` 无本地会话时回退后端 `default` 会话 |
| `src/views/` | 聊天(Message/Floating)/配置(Config)/思维(Mind)/面板(Panel) 等 |

## API 契约要点

- 业务调用（chat/memory/persona/config/desktop.files）全部走 **8000**；只有
  `/api/v1/platforms` 与 WS 走 **9800**。别再把业务打到 9800（历史事故：30+ 调用 404）。
- 后端 snake_case 字段经 axios 拦截器自动转 camelCase；包裹键差异（`data.history`→
  `messages` 等）在 `core.ts` 包装层归一化。
- 聊天发送 = `POST /api/chat/send {message, session_id}`；`session_id` 会透传到存储层，
  与终端/Web 共享会话（详见 `docs/API_REFERENCE.md` §2.1）。

## 已知约束

- 与 `frontend/ui`（Web HUD）默认同用 5173 端口：IPv4/IPv6 各绑一个可共存，但 `start.bat a`
  模式下 `:web` 分支会杀 5173 进程，误伤本桌面 dev server（待分配独立端口）。
- `src/live2d-app/` 与主渲染层是两个入口，dev 下经 `http://localhost:5173/src/live2d-app/index.html` 加载。
