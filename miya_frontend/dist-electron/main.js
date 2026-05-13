import { existsSync as R, readFileSync as $, mkdirSync as we, writeFileSync as ye } from "node:fs";
import { readdir as be } from "node:fs/promises";
import { dirname as C, join as I, resolve as x } from "node:path";
import h from "node:process";
import { fileURLToPath as A, pathToFileURL as Ee, domainToUnicode as X } from "node:url";
import { app as m, BrowserWindow as de, shell as ue, screen as H, globalShortcut as pe, Menu as O, nativeImage as Q, Tray as xe, protocol as F, net as Se, nativeTheme as ke, ipcMain as u, systemPreferences as Pe, desktopCapturer as Z } from "electron";
import { spawn as he, execSync as ve } from "node:child_process";
import { spawn as _e } from "@lydell/node-pty";
const Be = A(import.meta.url), Ce = C(Be);
let b = null, f = "classic", j = null, _ = null;
const E = 100, P = 420, Ie = 640, D = 200, W = E, q = E, Me = 160, me = 60, J = Math.round(Me / (1e3 / me));
let v = null;
function z(e, t, n, i) {
  v == null || v();
  let r = 0;
  const c = setInterval(() => {
    r++;
    const o = 1 - (1 - r / J) ** 3, s = Math.round(t.x + (n.x - t.x) * o), d = Math.round(t.y + (n.y - t.y) * o), a = Math.round(t.width + (n.width - t.width) * o), l = Math.round(t.height + (n.height - t.height) * o);
    e.setBounds({ x: s, y: d, width: a, height: l }), r >= J && (clearInterval(c), v = null, e.setBounds(n), i == null || i());
  }, 1e3 / me);
  v = () => {
    clearInterval(c), v = null;
  };
}
function Re(e, t, n) {
  const i = H.getPrimaryDisplay(), { width: r, height: c } = i.workAreaSize;
  let p = e;
  p + P > r && (p = r - P), p < 0 && (p = 0);
  let o = t;
  return o + n > c && (o = c - n), o < 0 && (o = 0), { x: p, y: o };
}
function ee() {
  h.platform;
  const e = m.isPackaged ? h.resourcesPath : m.getAppPath(), t = I(e, "public", "my.png");
  return b = new de({
    width: 1280,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    frame: !1,
    resizable: !0,
    hasShadow: !0,
    transparent: !1,
    show: !0,
    icon: t,
    webPreferences: {
      preload: I(Ce, "preload.mjs"),
      contextIsolation: !0,
      nodeIntegration: !1,
      webgl: !0
    }
  }), b.once("ready-to-show", () => {
    b == null || b.show();
  }), b.webContents.setWindowOpenHandler(({ url: n }) => (ue.openExternal(n), { action: "deny" })), h.env.VITE_DEV_SERVER_URL ? b.loadURL(h.env.VITE_DEV_SERVER_URL) : b.loadURL("miya-app://dist/index.html"), b;
}
function y() {
  return b;
}
function G() {
  return f;
}
function te() {
  const e = b;
  if (e) {
    if (j = e.getBounds(), f = "ball", !_) {
      const t = H.getPrimaryDisplay(), { width: n, height: i } = t.workAreaSize;
      _ = {
        x: n - E - 40,
        y: i - E - 40
      };
    }
    e.setAlwaysOnTop(!0, "modal-panel"), e.setSkipTaskbar(!0), e.setResizable(!1), e.setHasShadow(!1), e.setMinimumSize(E, E), e.setBounds({
      x: _.x,
      y: _.y,
      width: E,
      height: E
    }), e.webContents.send("floating:stateChanged", f);
  }
}
function ne() {
  const e = b;
  e && (f = "classic", e.setAlwaysOnTop(!1), e.setSkipTaskbar(!1), e.setResizable(!0), e.setHasShadow(!0), e.setMinimumSize(800, 600), j ? e.setBounds(j) : (e.setBounds({ width: 1280, height: 800 }), e.center()), e.webContents.send("floating:stateChanged", f));
}
function fe(e = !1) {
  const t = b;
  if (!t || f !== "ball")
    return;
  const n = t.getBounds();
  _ = { x: n.x, y: n.y };
  const i = e ? D : q;
  f = e ? "full" : "compact";
  const { x: r, y: c } = Re(_.x, _.y, i), p = { x: r, y: c, width: P, height: i };
  t.setMinimumSize(E, E), t.setHasShadow(!0), z(t, n, p, () => {
    t.setMinimumSize(P, i), t.webContents.send("floating:stateChanged", f);
  });
}
function Ae() {
  const e = b;
  if (!e || f !== "compact")
    return;
  f = "full", e.webContents.send("floating:stateChanged", f);
  const t = e.getBounds(), n = H.getPrimaryDisplay(), { height: i } = n.workAreaSize;
  let r = t.y;
  t.y + D > i && (r = i - D, r < 0 && (r = 0));
  const c = {
    x: t.x,
    y: r,
    width: P,
    height: D
  };
  e.setMinimumSize(E, E), z(e, t, c, () => {
    e.setMinimumSize(P, W);
  });
}
function Te() {
  const e = b;
  if (!e || f !== "full")
    return;
  f = "compact", e.webContents.send("floating:stateChanged", f);
  const t = e.getBounds(), n = {
    x: t.x,
    y: t.y,
    width: P,
    height: q
  };
  e.setMinimumSize(E, E), z(e, t, n, () => {
    e.setMinimumSize(P, q);
  });
}
function K() {
  const e = b;
  if (!e || f !== "compact" && f !== "full")
    return;
  f = "ball", e.webContents.send("floating:stateChanged", f);
  const t = e.getBounds(), n = t.x, i = t.y;
  _ = { x: n, y: i };
  const r = {
    x: n,
    y: i,
    width: E,
    height: E
  };
  e.setMinimumSize(E, E), e.setHasShadow(!1), z(e, t, r);
}
function Le(e, t) {
  const n = b;
  if (!n)
    return;
  const i = Math.round(e), r = Math.round(t);
  n.setPosition(i, r), f !== "classic" && (_ = { x: i, y: r });
}
function ze(e) {
  const t = b;
  if (!t || f !== "full")
    return;
  v == null || v();
  const n = Math.max(W, Math.min(Math.round(e), Ie)), i = t.getBounds();
  if (i.height === n)
    return;
  const r = H.getPrimaryDisplay(), { height: c } = r.workAreaSize;
  let p = i.y;
  i.y + n > c && (p = c - n, p < 0 && (p = 0));
  const o = { x: i.x, y: p, width: P, height: n }, s = Math.abs(n - i.height);
  t.setMinimumSize(P, W), s > 50 ? z(t, i, o) : t.setBounds(o);
}
const Fe = A(import.meta.url), De = C(Fe);
let k = null;
const oe = 1200, L = [];
function M(e, t = "system") {
  var r;
  const n = e.replace(/\r/g, "").trimEnd();
  if (!n.trim())
    return;
  const i = t === "system" ? n : `[${t}] ${n}`;
  L.push(i), L.length > oe && L.splice(0, L.length - oe);
  try {
    (r = y()) == null || r.webContents.send("backend:log", { line: i });
  } catch {
  }
}
function se(e, t) {
  let n = "";
  return (i) => {
    const c = `${n}${i.replace(/\r\n/g, `
`).replace(/\r/g, `
`)}`.split(`
`);
    n = c.pop() ?? "";
    for (const p of c) {
      const o = p.trimEnd();
      if (!o.trim())
        continue;
      t(o) !== !1 && M(o, e);
    }
  };
}
function Ue() {
  return L.join(`
`);
}
function Oe(e) {
  return h.platform === "win32" ? I(e, ".venv", "Scripts", "python.exe") : I(e, ".venv", "bin", "python");
}
function Ne() {
  var s, d;
  let e, t, n;
  if (m.isPackaged) {
    const a = I(h.resourcesPath, "backend"), l = h.platform === "win32" ? ".exe" : "";
    e = I(a, `miya-backend${l}`), t = [], n = a;
  } else {
    n = I(De, "..", "..");
    let a = Oe(n);
    if (!R(a)) {
      const l = h.platform === "win32" ? "D:/Python/python3.11.9/python.exe" : "python3";
      if (R(l))
        a = l, console.log("[Backend] 使用系统 Python:", l);
      else {
        console.warn("[Backend] 未找到 Python 解释器，跳过后端启动"), M("[Backend] Python not found, skipping backend start");
        return;
      }
    }
    e = a, t = ["run/miya_demo.py"];
  }
  console.log(`[Backend] Starting from ${n}`), console.log(`[Backend] Command: ${e} ${t.join(" ")}`), M(`[Backend] Starting from ${n}`), M(`[Backend] Command: ${e} ${t.join(" ")}`);
  const i = { ...h.env, PYTHONUNBUFFERED: "1" }, r = [], c = "##PROGRESS##", p = se("stdout", (a) => {
    var l;
    if (r.push(a), a.startsWith(c)) {
      try {
        const g = JSON.parse(a.slice(c.length));
        (l = y()) == null || l.webContents.send("backend:progress", g);
      } catch {
      }
      return !1;
    }
    return !0;
  }), o = se("stderr", (a) => (r.push(a), !0));
  k = he(e, t, {
    cwd: n,
    stdio: ["ignore", "pipe", "pipe"],
    env: i,
    // 创建独立进程组，关闭时用 process.kill(-pid) 杀掉所有子进程
    detached: h.platform !== "win32"
  }), (s = k.stdout) == null || s.on("data", (a) => {
    const l = a.toString();
    p(l), console.log(`[Backend] ${l.trimEnd()}`);
  }), (d = k.stderr) == null || d.on("data", (a) => {
    const l = a.toString();
    console.error(`[Backend] ${l.trimEnd()}`), o(l);
  }), k.on("error", (a) => {
    console.error(`[Backend] Failed to start: ${a.message}`), M(`[Backend] Failed to start: ${a.message}`);
  }), k.on("exit", (a) => {
    var l;
    if (console.log(`[Backend] Exited with code ${a}`), M(`[Backend] Exited with code ${a}`), k = null, a !== null && a !== 0) {
      const g = r.slice(-200).join(`
`);
      (l = y()) == null || l.webContents.send("backend:error", { code: a, logs: g });
    }
  });
}
function He() {
  if (!k)
    return;
  const e = k.pid;
  if (console.log("[Backend] Stopping..."), M("[Backend] Stopping..."), !e) {
    k = null;
    return;
  }
  if (h.platform === "win32")
    he("taskkill", ["/pid", String(e), "/f", "/t"]);
  else {
    try {
      h.kill(-e, "SIGTERM");
    } catch {
      try {
        h.kill(e, "SIGTERM");
      } catch {
      }
    }
    setTimeout(() => {
      try {
        h.kill(-e, "SIGKILL");
      } catch {
        try {
          h.kill(e, "SIGKILL");
        } catch {
        }
      }
    }, 200);
  }
  k = null;
}
function $e() {
  pe.register("CommandOrControl+Shift+N", () => {
    const e = y();
    if (!e)
      return;
    const t = G();
    t === "classic" ? e.isVisible() ? e.hide() : (e.show(), e.focus()) : t === "ball" ? e.isVisible() ? (fe(), e.focus()) : e.show() : (t === "compact" || t === "full") && K();
  });
}
function je() {
  pe.unregisterAll();
}
function We() {
  const e = h.platform === "darwin", t = [
    ...e ? [{
      label: "弥娅 AI",
      submenu: [
        { role: "about" },
        { type: "separator" },
        { role: "services" },
        { type: "separator" },
        { role: "hide" },
        { role: "hideOthers" },
        { role: "unhide" },
        { type: "separator" },
        { role: "quit" }
      ]
    }] : [],
    {
      label: "编辑",
      submenu: [
        { role: "undo", label: "撤销" },
        { role: "redo", label: "重做" },
        { type: "separator" },
        { role: "cut", label: "剪切" },
        { role: "copy", label: "复制" },
        { role: "paste", label: "粘贴" },
        { role: "selectAll", label: "全选" }
      ]
    },
    {
      label: "视图",
      submenu: [
        { role: "reload", label: "重新加载" },
        { role: "forceReload", label: "强制重新加载" },
        { role: "toggleDevTools", label: "开发者工具" },
        { type: "separator" },
        { role: "resetZoom", label: "重置缩放" },
        { role: "zoomIn", label: "放大" },
        { role: "zoomOut", label: "缩小" },
        { type: "separator" },
        { role: "togglefullscreen", label: "全屏" }
      ]
    },
    {
      label: "窗口",
      submenu: [
        { role: "minimize", label: "最小化" },
        { role: "zoom", label: "缩放" },
        ...e ? [
          { type: "separator" },
          { role: "front", label: "前置全部窗口" }
        ] : [
          { role: "close", label: "关闭" }
        ]
      ]
    }
  ], n = O.buildFromTemplate(t);
  O.setApplicationMenu(n);
}
function qe() {
  try {
    const n = ve("where node", { timeout: 5e3, encoding: "utf-8" }).trim().split(`\r
`);
    for (const i of n)
      if (R(i)) return i;
  } catch {
  }
  const e = [
    "D:\\node.exe",
    "C:\\Program Files\\nodejs\\node.exe",
    process.env.NODE_EXE,
    process.env.NODE
  ];
  for (const t of e)
    if (t && R(t)) return t;
  return "node";
}
const ae = qe();
function Ge(e) {
  const t = {}, n = x(e, "config", ".env");
  if (R(n)) {
    const i = $(n, "utf-8");
    for (const r of i.split(`
`)) {
      const c = r.trim();
      if (!c || c.startsWith("#")) continue;
      const p = c.indexOf("=");
      if (p === -1) continue;
      const o = c.slice(0, p).trim(), s = c.slice(p + 1).trim();
      o && s && (t[o] = s);
    }
  }
  return t;
}
let S = null, ge = "", N = "";
function Ke(e) {
  ge = e;
}
function Ve(e, t) {
  const n = Ge(e), i = n.DEEPSEEK_API_KEY || process.env.DEEPSEEK_API_KEY || "", r = n.DEEPSEEK_API_BASE || "https://api.deepseek.com/v1", c = t || n.DEEPSEEK_MODEL || "deepseek-v4-flash";
  return {
    ...process.env,
    CLAUDE_CODE_USE_OPENAI: "1",
    OPENAI_API_KEY: i,
    OPENAI_BASE_URL: r,
    OPENAI_MODEL: c,
    FORCE_COLOR: "1",
    TERM: "xterm-256color"
  };
}
function Ye(e = {}, t, n) {
  S && V();
  const i = ge || process.cwd(), r = Ve(i, e.model), c = x(i, "claude-code-engine", "dist", "cli-node.js");
  if (!R(c))
    throw new Error(`Claude Code Engine not found: ${c}`);
  if (!R(ae))
    throw new Error("Node.js not found. Searched PATH and common locations. Try installing Node.js.");
  S = _e(ae, [c], {
    name: "xterm-256color",
    cwd: i,
    env: r,
    cols: 120,
    rows: 40
  }), N = "", S.onData((p) => {
    N += p, t(p);
  }), S.onExit(({ exitCode: p }) => {
    n(p), S = null;
  });
}
function Xe(e) {
  S && S.write(e);
}
function Qe(e, t) {
  S && S.resize(e, t);
}
function V() {
  S && (S.kill(), S = null, N = "");
}
function Ze() {
  return S !== null;
}
function Je() {
  return N;
}
let B = null;
function et() {
  const e = h.platform === "win32", t = m.isPackaged ? h.resourcesPath : m.getAppPath();
  let n;
  try {
    const r = I(t, "public", "my.png");
    n = Q.createFromPath(r), e ? n = n.resize({ width: 32, height: 32 }) : n = n.resize({ width: 64, height: 64 }).resize({ width: 22, height: 22 });
  } catch {
    n = Q.createEmpty();
  }
  B = new xe(n), B.setToolTip("弥娅 AI");
  const i = O.buildFromTemplate([
    {
      label: "显示窗口",
      click: () => {
        const r = y();
        r && (r.show(), r.focus());
      }
    },
    { type: "separator" },
    {
      label: "退出",
      click: () => {
        m.quit();
      }
    }
  ]);
  return B.setContextMenu(i), B.on("click", () => {
    const r = y();
    r && (r.isVisible() ? r.focus() : r.show());
  }), B;
}
function tt() {
  B && (B.destroy(), B = null);
}
let w = null;
async function nt(e) {
  var t;
  try {
    const n = await import("electron-updater");
    w = n.autoUpdater ?? ((t = n.default) == null ? void 0 : t.autoUpdater) ?? n.default ?? null;
  } catch {
    console.warn("[Updater] electron-updater not available");
    return;
  }
  if (!w || typeof w.checkForUpdates != "function") {
    console.warn("[Updater] autoUpdater unavailable after import"), w = null;
    return;
  }
  w.autoDownload = !1, w.autoInstallOnAppQuit = !0, w.on("update-available", (n) => {
    e.webContents.send("updater:update-available", {
      version: n.version,
      releaseNotes: n.releaseNotes
    });
  }), w.on("update-not-available", () => {
    e.webContents.send("updater:update-not-available");
  }), w.on("download-progress", (n) => {
    e.webContents.send("updater:download-progress", {
      percent: n.percent,
      bytesPerSecond: n.bytesPerSecond
    });
  }), w.on("update-downloaded", () => {
    e.webContents.send("updater:update-downloaded");
  }), w.on("error", (n) => {
    e.webContents.send("updater:error", n.message);
  }), setTimeout(() => {
    w.checkForUpdates().catch(() => {
    });
  }, 3e3);
}
function ot() {
  w == null || w.downloadUpdate();
}
function st() {
  w == null || w.quitAndInstall();
}
let U = !1;
var le;
(le = h.stdout) == null || le.on("error", () => {
});
var ce;
(ce = h.stderr) == null || ce.on("error", () => {
});
const at = m.requestSingleInstanceLock();
at || m.quit();
const ie = m.isPackaged ? x(h.resourcesPath, "characters") : x(C(A(import.meta.url)), "..", "..", "characters"), it = m.isPackaged ? x(h.resourcesPath, "..") : x(C(A(import.meta.url)), "..", ".."), rt = "弥娅", re = m.isPackaged ? x(h.resourcesPath, "premium-assets", "backgrounds") : x(C(A(import.meta.url)), "..", "premium-assets", "backgrounds");
F.registerSchemesAsPrivileged([
  { scheme: "miya-char", privileges: { secure: !0, supportFetchAPI: !0, corsEnabled: !0, standard: !0, stream: !0 } },
  { scheme: "miya-bg", privileges: { secure: !0, supportFetchAPI: !0, corsEnabled: !0, standard: !0, stream: !0 } },
  { scheme: "miya-app", privileges: { secure: !0, supportFetchAPI: !0, corsEnabled: !0, standard: !0, stream: !0 } }
]);
m.on("second-instance", () => {
  const e = y();
  e && (e.isMinimized() && e.restore(), e.show(), e.focus());
});
m.whenReady().then(async () => {
  Ke(it);
  const e = {
    mp3: "audio/mpeg",
    wav: "audio/wav",
    ogg: "audio/ogg",
    m4a: "audio/mp4",
    flac: "audio/flac",
    aac: "audio/aac",
    webm: "audio/webm",
    mp4: "video/mp4",
    mkv: "video/x-matroska"
  }, t = {
    ...e,
    json: "application/json; charset=utf-8",
    txt: "text/plain; charset=utf-8",
    png: "image/png",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    webp: "image/webp",
    svg: "image/svg+xml",
    moc3: "application/octet-stream"
  };
  function n(o, s) {
    try {
      const d = new URL(o), a = X(d.hostname || ""), l = decodeURIComponent(d.pathname).replace(/^\/+/, ""), g = [a, l].filter(Boolean).join("/"), T = x(s, g);
      return T.startsWith(s) ? T : null;
    } catch {
      return null;
    }
  }
  function i(o, s = "Not Found") {
    var d;
    try {
      const a = $(o), l = ((d = o.split(".").pop()) == null ? void 0 : d.toLowerCase()) ?? "", g = t[l] || "application/octet-stream";
      return new Response(a, {
        headers: {
          "Content-Type": g,
          "Content-Length": a.length.toString(),
          "Cache-Control": "no-cache"
        }
      });
    } catch {
      return new Response(s, { status: 404 });
    }
  }
  const r = x(C(A(import.meta.url)), "..", "dist");
  F.handle("miya-app", (o) => {
    var T;
    const s = decodeURIComponent(new URL(o.url).pathname).replace(/^\/+/, ""), d = s.startsWith("dist/") ? s.slice(5) : s, a = x(r, d);
    if (!a.startsWith(r))
      return new Response("Forbidden", { status: 403 });
    const l = ((T = a.split(".").pop()) == null ? void 0 : T.toLowerCase()) ?? "", g = e[l];
    if (g)
      try {
        const Y = $(a);
        return new Response(Y, {
          headers: { "Content-Type": g, "Content-Length": Y.length.toString() }
        });
      } catch {
        return new Response("Not Found", { status: 404 });
      }
    return Se.fetch(Ee(a).toString());
  }), F.handle("miya-char", (o) => {
    try {
      const s = new URL(o.url);
      let d = X(s.hostname || "");
      const a = decodeURIComponent(s.pathname).replace(/^\/+/, "");
      d || (d = rt);
      const l = [d, a].filter(Boolean).join("/"), g = x(ie, l);
      return g.startsWith(ie) ? i(g, "Character Asset Not Found") : new Response("Forbidden", { status: 403 });
    } catch {
      return new Response("Forbidden", { status: 403 });
    }
  }), F.handle("miya-bg", (o) => {
    const s = n(o.url, re);
    return s ? i(s, "Background Asset Not Found") : new Response("Forbidden", { status: 403 });
  }), ke.themeSource = "dark", We();
  const c = ee();
  let p = null;
  et(), $e(), nt(c), u.on("window:minimize", () => {
    var o;
    return (o = y()) == null ? void 0 : o.minimize();
  }), u.on("window:maximize", () => {
    const o = y();
    o && (o.isMaximized() ? o.unmaximize() : (p = o.getBounds(), o.maximize()));
  }), u.on("window:close", () => {
    var s;
    const o = G();
    o === "compact" || o === "full" ? K() : o === "classic" ? te() : (s = y()) == null || s.hide();
  }), u.handle("window:isMaximized", () => {
    var o;
    return ((o = y()) == null ? void 0 : o.isMaximized()) ?? !1;
  }), u.handle("window:getBounds", () => {
    var o;
    return ((o = y()) == null ? void 0 : o.getBounds()) ?? { x: 0, y: 0, width: 1280, height: 800 };
  }), u.on("window:setBounds", (o, s) => {
    const d = y();
    if (!d || d.isMaximized())
      return;
    const a = d.getBounds(), l = {
      x: s.x ?? a.x,
      y: s.y ?? a.y,
      width: Math.max(800, s.width ?? a.width),
      height: Math.max(600, s.height ?? a.height)
    };
    d.setBounds(l);
  }), u.handle("floating:enter", () => {
    te();
  }), u.handle("floating:exit", () => {
    ne();
  }), u.handle("floating:expand", (o, s) => {
    fe(s ?? !1);
  }), u.handle("floating:expandToFull", () => {
    Ae();
  }), u.handle("floating:collapse", () => {
    K();
  }), u.handle("floating:collapseToCompact", () => {
    Te();
  }), u.handle("floating:getState", () => G()), u.on("floating:pin", (o, s) => {
    const d = y();
    d && d.setSkipTaskbar(!s);
  }), u.on("floating:setPosition", (o, s, d) => {
    Le(s, d);
  }), u.on("floating:fitHeight", (o, s) => {
    ze(s);
  }), u.on("updater:download", () => ot()), u.on("updater:install", () => st()), u.on("app:quit", () => {
    U = !0, m.quit();
  }), u.on("context-menu:show", () => {
    O.buildFromTemplate([
      {
        label: "打开主界面",
        click: () => ne()
      },
      {
        label: "隐藏到托盘",
        click: () => {
          var s;
          return (s = y()) == null ? void 0 : s.hide();
        }
      },
      { type: "separator" },
      {
        label: "退出应用",
        click: () => {
          U = !0, m.quit();
        }
      }
    ]).popup();
  }), u.handle("capture:getSources", async () => {
    if (h.platform === "darwin") {
      const o = Pe.getMediaAccessStatus("screen");
      if (o !== "granted")
        return { permission: o };
    }
    try {
      return (await Z.getSources({
        types: ["window", "screen"],
        thumbnailSize: { width: 320, height: 180 },
        fetchWindowIcons: !0
      })).map((s) => {
        var d;
        return {
          id: s.id,
          name: s.name,
          thumbnail: s.thumbnail.toDataURL(),
          appIcon: ((d = s.appIcon) == null ? void 0 : d.toDataURL()) || null
        };
      });
    } catch {
      return { permission: "denied" };
    }
  }), u.handle("capture:captureWindow", async (o, s) => {
    const a = (await Z.getSources({
      types: ["window", "screen"],
      thumbnailSize: { width: 1920, height: 1080 }
    })).find((l) => l.id === s);
    return a ? a.thumbnail.toDataURL() : null;
  }), u.handle("capture:openScreenSettings", async () => {
    h.platform === "darwin" && await ue.openExternal("x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture");
  }), u.handle("backgrounds:scan", async () => {
    try {
      const o = await be(re), s = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"];
      return o.filter((d) => s.some((a) => d.toLowerCase().endsWith(a)));
    } catch {
      return [];
    }
  }), u.handle("fs:writeFile", (o, s, d) => {
    const a = m.isPackaged ? x(h.resourcesPath) : x(C(A(import.meta.url)), "..", ".."), l = x(a, s);
    we(C(l), { recursive: !0 }), ye(l, Buffer.from(d, "base64"));
  }), u.handle("autoLaunch:get", () => m.getLoginItemSettings().openAtLogin), u.handle("autoLaunch:set", (o, s) => {
    m.setLoginItemSettings({ openAtLogin: s });
  }), u.handle("backend:getLogs", () => Ue()), u.handle("terminal:start", (o, s) => new Promise((d, a) => {
    try {
      Ye(
        s,
        (l) => {
          var g;
          (g = y()) == null || g.webContents.send("terminal:data", l);
        },
        (l) => {
          var g;
          (g = y()) == null || g.webContents.send("terminal:exit", l);
        }
      ), d();
    } catch (l) {
      a(l instanceof Error ? l.message : String(l));
    }
  })), u.handle("terminal:write", (o, s) => {
    Xe(s);
  }), u.handle("terminal:resize", (o, s, d) => {
    Qe(s, d);
  }), u.handle("terminal:stop", () => {
    V();
  }), u.handle("terminal:isRunning", () => Ze()), u.handle("terminal:getBuffer", () => Je()), c.on("close", (o) => {
    U || (o.preventDefault(), c.hide());
  }), c.on("maximize", () => c.webContents.send("window:maximized", !0)), c.on("unmaximize", () => {
    c.webContents.send("window:maximized", !1), p && (c.setBounds(p), p = null);
  }), c.on("blur", () => {
    c.webContents.send("floating:windowBlur");
  }), m.on("activate", () => {
    var o;
    de.getAllWindows().length === 0 ? ee() : (o = y()) == null || o.show();
  }), Ne();
});
m.on("before-quit", () => {
  U = !0;
});
m.on("will-quit", () => {
  je(), tt(), V(), He();
});
m.on("window-all-closed", () => {
  h.platform !== "darwin" && m.quit();
});
