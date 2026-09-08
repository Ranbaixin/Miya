# frontend/ui — Web HUD（Ops Center）

React 18 + Vite + Tailwind 的浏览器管理界面（Ops Center）：总览/健康/平台/资源/模型/Agent/消息/记忆/调度/终端/日志/配置/权限。

## 启动 / 构建

```bash
# 推荐：从项目根 start.bat 选 4（自动处理 '#' 路径问题）
# 手动：
npm run dev           # dev server（默认 5173，被占用自动 +1）
npm run build         # 产物输出到 ../../packages/web/dist（后端挂载为 HUD 静态页）
npx tsc --noEmit      # 类型检查
```

## API 对接

- 直连后端 **8000**（`src/services/miyaApi.ts` 的 `CORE` 常量，`VITE_CORE_URL` 可覆盖）。
- dev 模式 vite proxy：`/api → 8000`、`/mgmt → 9800(/api/v1)`。
- 2026-09 修复的历史断点（勿回退）：
  - 配置保存走 `POST /api/desktop/files/write`（JSON body）——原 `POST /api/config/file` 不存在（405）。
  - Web 终端走 `POST /api/chat/send`——原 `/api/terminal/chat` 已迁移 Open-ClaudeCode（404）。
  - 会话历史走 `/api/chat/get_session`——原 `/api/chat/history` 不存在。
  - `/api/tools/history` 轮询已移除（后端无此数据）。

## 与 miya_frontend 的关系

两者是**独立的两个前端**：本目录是浏览器 HUD（运维向），`miya_frontend/` 是 Electron 桌面应用（陪伴向）。
共享的只有后端（8000/9800）与部分设计语言；**默认端口都是 5173**，同时启动会争用
（`start.bat a` 模式下 `:web` 杀 5173 会误伤桌面 dev server，待分配独立端口）。

## `#` 路径问题

同 `miya_frontend`（见其 README）：`start.bat :ensure_nohash` 的 subst 盘符 +
`scripts/patch_vite_realpath.mjs`（postinstall）+ `vite.config.ts` 的 `hashPathFixPlugin` 三层规避。

## 残留清理提示

根目录若出现 `build_check.log` / `build_check2.log` 为本地构建日志，勿提交。
