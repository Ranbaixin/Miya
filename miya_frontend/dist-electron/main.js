var _a, _b;
import { existsSync, readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { readdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL, domainToUnicode } from "node:url";
import { app, BrowserWindow, shell, screen, globalShortcut, Menu, nativeImage, Tray, protocol, net, nativeTheme, ipcMain, systemPreferences, desktopCapturer } from "electron";
import { spawn } from "node:child_process";
const __filename$2 = fileURLToPath(import.meta.url);
const __dirname$2 = dirname(__filename$2);
let mainWindow = null;
let floatingState = "classic";
let classicBounds = null;
let ballPosition = null;
const BALL_SIZE = 100;
const EXPANDED_WIDTH = 420;
const MAX_FULL_HEIGHT = 640;
const INITIAL_FULL_HEIGHT = 200;
const MIN_FIT_HEIGHT = BALL_SIZE;
const COMPACT_HEIGHT = BALL_SIZE;
const ANIM_DURATION_MS = 160;
const ANIM_FPS = 60;
const ANIM_FRAMES = Math.round(ANIM_DURATION_MS / (1e3 / ANIM_FPS));
let cancelCurrentAnimation = null;
function animateBounds(win, from, to, onDone) {
  cancelCurrentAnimation == null ? void 0 : cancelCurrentAnimation();
  let frame = 0;
  const interval = setInterval(() => {
    frame++;
    const t = frame / ANIM_FRAMES;
    const ease = 1 - (1 - t) ** 3;
    const x = Math.round(from.x + (to.x - from.x) * ease);
    const y = Math.round(from.y + (to.y - from.y) * ease);
    const w = Math.round(from.width + (to.width - from.width) * ease);
    const h = Math.round(from.height + (to.height - from.height) * ease);
    win.setBounds({ x, y, width: w, height: h });
    if (frame >= ANIM_FRAMES) {
      clearInterval(interval);
      cancelCurrentAnimation = null;
      win.setBounds(to);
      onDone == null ? void 0 : onDone();
    }
  }, 1e3 / ANIM_FPS);
  cancelCurrentAnimation = () => {
    clearInterval(interval);
    cancelCurrentAnimation = null;
  };
}
function calcExpandPosition(ballX, ballY, targetHeight) {
  const display = screen.getPrimaryDisplay();
  const { width: screenW, height: screenH } = display.workAreaSize;
  let expandX = ballX;
  if (expandX + EXPANDED_WIDTH > screenW)
    expandX = screenW - EXPANDED_WIDTH;
  if (expandX < 0)
    expandX = 0;
  let expandY = ballY;
  if (expandY + targetHeight > screenH)
    expandY = screenH - targetHeight;
  if (expandY < 0)
    expandY = 0;
  return { x: expandX, y: expandY };
}
function createWindow() {
  process.platform === "win32";
  const baseDir = app.isPackaged ? process.resourcesPath : app.getAppPath();
  const iconPath = join(baseDir, "public", "my.png");
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    frame: false,
    resizable: true,
    hasShadow: true,
    transparent: false,
    show: true,
    icon: iconPath,
    webPreferences: {
      preload: join(__dirname$2, "preload.mjs"),
      contextIsolation: true,
      nodeIntegration: false,
      webgl: true
    }
  });
  mainWindow.once("ready-to-show", () => {
    mainWindow == null ? void 0 : mainWindow.show();
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadURL("miya-app://dist/index.html");
  }
  return mainWindow;
}
function getMainWindow() {
  return mainWindow;
}
function getFloatingState() {
  return floatingState;
}
function enterFloatingMode() {
  const win = mainWindow;
  if (!win)
    return;
  classicBounds = win.getBounds();
  floatingState = "ball";
  if (!ballPosition) {
    const display = screen.getPrimaryDisplay();
    const { width, height } = display.workAreaSize;
    ballPosition = {
      x: width - BALL_SIZE - 40,
      y: height - BALL_SIZE - 40
    };
  }
  win.setAlwaysOnTop(true, "modal-panel");
  win.setSkipTaskbar(true);
  win.setResizable(false);
  win.setHasShadow(false);
  win.setMinimumSize(BALL_SIZE, BALL_SIZE);
  win.setBounds({
    x: ballPosition.x,
    y: ballPosition.y,
    width: BALL_SIZE,
    height: BALL_SIZE
  });
  win.webContents.send("floating:stateChanged", floatingState);
}
function exitFloatingMode() {
  const win = mainWindow;
  if (!win)
    return;
  floatingState = "classic";
  win.setAlwaysOnTop(false);
  win.setSkipTaskbar(false);
  win.setResizable(true);
  win.setHasShadow(true);
  win.setMinimumSize(800, 600);
  if (classicBounds) {
    win.setBounds(classicBounds);
  } else {
    win.setBounds({ width: 1280, height: 800 });
    win.center();
  }
  win.webContents.send("floating:stateChanged", floatingState);
}
function expandFloatingWindow(toFull = false) {
  const win = mainWindow;
  if (!win || floatingState !== "ball")
    return;
  const fromBounds = win.getBounds();
  ballPosition = { x: fromBounds.x, y: fromBounds.y };
  const targetHeight = toFull ? INITIAL_FULL_HEIGHT : COMPACT_HEIGHT;
  floatingState = toFull ? "full" : "compact";
  const { x: expandX, y: expandY } = calcExpandPosition(ballPosition.x, ballPosition.y, targetHeight);
  const toBounds = { x: expandX, y: expandY, width: EXPANDED_WIDTH, height: targetHeight };
  win.setMinimumSize(BALL_SIZE, BALL_SIZE);
  win.setHasShadow(true);
  animateBounds(win, fromBounds, toBounds, () => {
    win.setMinimumSize(EXPANDED_WIDTH, targetHeight);
    win.webContents.send("floating:stateChanged", floatingState);
  });
}
function expandCompactToFull() {
  const win = mainWindow;
  if (!win || floatingState !== "compact")
    return;
  floatingState = "full";
  win.webContents.send("floating:stateChanged", floatingState);
  const fromBounds = win.getBounds();
  const display = screen.getPrimaryDisplay();
  const { height: screenH } = display.workAreaSize;
  let newY = fromBounds.y;
  if (fromBounds.y + INITIAL_FULL_HEIGHT > screenH) {
    newY = screenH - INITIAL_FULL_HEIGHT;
    if (newY < 0)
      newY = 0;
  }
  const toBounds = {
    x: fromBounds.x,
    y: newY,
    width: EXPANDED_WIDTH,
    height: INITIAL_FULL_HEIGHT
  };
  win.setMinimumSize(BALL_SIZE, BALL_SIZE);
  animateBounds(win, fromBounds, toBounds, () => {
    win.setMinimumSize(EXPANDED_WIDTH, MIN_FIT_HEIGHT);
  });
}
function collapseFullToCompact() {
  const win = mainWindow;
  if (!win || floatingState !== "full")
    return;
  floatingState = "compact";
  win.webContents.send("floating:stateChanged", floatingState);
  const fromBounds = win.getBounds();
  const toBounds = {
    x: fromBounds.x,
    y: fromBounds.y,
    width: EXPANDED_WIDTH,
    height: COMPACT_HEIGHT
  };
  win.setMinimumSize(BALL_SIZE, BALL_SIZE);
  animateBounds(win, fromBounds, toBounds, () => {
    win.setMinimumSize(EXPANDED_WIDTH, COMPACT_HEIGHT);
  });
}
function collapseFloatingWindow() {
  const win = mainWindow;
  if (!win || floatingState !== "compact" && floatingState !== "full")
    return;
  floatingState = "ball";
  win.webContents.send("floating:stateChanged", floatingState);
  const fromBounds = win.getBounds();
  const targetX = fromBounds.x;
  const targetY = fromBounds.y;
  ballPosition = { x: targetX, y: targetY };
  const toBounds = {
    x: targetX,
    y: targetY,
    width: BALL_SIZE,
    height: BALL_SIZE
  };
  win.setMinimumSize(BALL_SIZE, BALL_SIZE);
  win.setHasShadow(false);
  animateBounds(win, fromBounds, toBounds);
}
function setWindowPosition(x, y) {
  const win = mainWindow;
  if (!win)
    return;
  const rx = Math.round(x);
  const ry = Math.round(y);
  win.setPosition(rx, ry);
  if (floatingState !== "classic") {
    ballPosition = { x: rx, y: ry };
  }
}
function setFloatingHeight(height) {
  const win = mainWindow;
  if (!win || floatingState !== "full")
    return;
  cancelCurrentAnimation == null ? void 0 : cancelCurrentAnimation();
  const clamped = Math.max(MIN_FIT_HEIGHT, Math.min(Math.round(height), MAX_FULL_HEIGHT));
  const bounds = win.getBounds();
  if (bounds.height === clamped)
    return;
  const display = screen.getPrimaryDisplay();
  const { height: screenH } = display.workAreaSize;
  let newY = bounds.y;
  if (bounds.y + clamped > screenH) {
    newY = screenH - clamped;
    if (newY < 0)
      newY = 0;
  }
  const toBounds = { x: bounds.x, y: newY, width: EXPANDED_WIDTH, height: clamped };
  const delta = Math.abs(clamped - bounds.height);
  win.setMinimumSize(EXPANDED_WIDTH, MIN_FIT_HEIGHT);
  if (delta > 50) {
    animateBounds(win, bounds, toBounds);
  } else {
    win.setBounds(toBounds);
  }
}
const __filename$1 = fileURLToPath(import.meta.url);
const __dirname$1 = dirname(__filename$1);
let backendProcess = null;
const BACKEND_LOG_MAX_LINES = 1200;
const backendLogLines = [];
function appendBackendLog(line, stream = "system") {
  var _a2;
  const normalized = line.replace(/\r/g, "").trimEnd();
  if (!normalized.trim())
    return;
  const entry = stream === "system" ? normalized : `[${stream}] ${normalized}`;
  backendLogLines.push(entry);
  if (backendLogLines.length > BACKEND_LOG_MAX_LINES) {
    backendLogLines.splice(0, backendLogLines.length - BACKEND_LOG_MAX_LINES);
  }
  try {
    (_a2 = getMainWindow()) == null ? void 0 : _a2.webContents.send("backend:log", { line: entry });
  } catch {
  }
}
function createChunkForwarder(stream, onLine) {
  let carry = "";
  return (text) => {
    const normalized = `${carry}${text.replace(/\r\n/g, "\n").replace(/\r/g, "\n")}`;
    const parts = normalized.split("\n");
    carry = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trimEnd();
      if (!line.trim())
        continue;
      const shouldMirror = onLine(line);
      if (shouldMirror !== false) {
        appendBackendLog(line, stream);
      }
    }
  };
}
function getBackendLogs() {
  return backendLogLines.join("\n");
}
function resolveVenvPython(cwd) {
  return process.platform === "win32" ? join(cwd, ".venv", "Scripts", "python.exe") : join(cwd, ".venv", "bin", "python");
}
function startBackend() {
  var _a2, _b2;
  let cmd;
  let args;
  let cwd;
  if (app.isPackaged) {
    const backendDir = join(process.resourcesPath, "backend");
    const ext = process.platform === "win32" ? ".exe" : "";
    cmd = join(backendDir, `miya-backend${ext}`);
    args = [];
    cwd = backendDir;
  } else {
    cwd = join(__dirname$1, "..", "..");
    let pythonPath = resolveVenvPython(cwd);
    if (!existsSync(pythonPath)) {
      const sysPython = process.platform === "win32" ? "D:/Python/python3.11.9/python.exe" : "python3";
      if (existsSync(sysPython)) {
        pythonPath = sysPython;
        console.log("[Backend] 使用系统 Python:", sysPython);
      } else {
        console.warn("[Backend] 未找到 Python 解释器，跳过后端启动");
        appendBackendLog("[Backend] Python not found, skipping backend start");
        return;
      }
    }
    cmd = pythonPath;
    args = ["run/miya_demo.py"];
  }
  console.log(`[Backend] Starting from ${cwd}`);
  console.log(`[Backend] Command: ${cmd} ${args.join(" ")}`);
  appendBackendLog(`[Backend] Starting from ${cwd}`);
  appendBackendLog(`[Backend] Command: ${cmd} ${args.join(" ")}`);
  const env = { ...process.env, PYTHONUNBUFFERED: "1" };
  const outputLines = [];
  const PROGRESS_PREFIX = "##PROGRESS##";
  const consumeStdoutChunk = createChunkForwarder("stdout", (trimmed) => {
    var _a3;
    outputLines.push(trimmed);
    if (trimmed.startsWith(PROGRESS_PREFIX)) {
      try {
        const payload = JSON.parse(trimmed.slice(PROGRESS_PREFIX.length));
        (_a3 = getMainWindow()) == null ? void 0 : _a3.webContents.send("backend:progress", payload);
      } catch {
      }
      return false;
    }
    return true;
  });
  const consumeStderrChunk = createChunkForwarder("stderr", (trimmed) => {
    outputLines.push(trimmed);
    return true;
  });
  backendProcess = spawn(cmd, args, {
    cwd,
    stdio: ["ignore", "pipe", "pipe"],
    env,
    // 创建独立进程组，关闭时用 process.kill(-pid) 杀掉所有子进程
    detached: process.platform !== "win32"
  });
  (_a2 = backendProcess.stdout) == null ? void 0 : _a2.on("data", (data) => {
    const text = data.toString();
    consumeStdoutChunk(text);
    console.log(`[Backend] ${text.trimEnd()}`);
  });
  (_b2 = backendProcess.stderr) == null ? void 0 : _b2.on("data", (data) => {
    const text = data.toString();
    console.error(`[Backend] ${text.trimEnd()}`);
    consumeStderrChunk(text);
  });
  backendProcess.on("error", (err) => {
    console.error(`[Backend] Failed to start: ${err.message}`);
    appendBackendLog(`[Backend] Failed to start: ${err.message}`);
  });
  backendProcess.on("exit", (code) => {
    var _a3;
    console.log(`[Backend] Exited with code ${code}`);
    appendBackendLog(`[Backend] Exited with code ${code}`);
    backendProcess = null;
    if (code !== null && code !== 0) {
      const logs = outputLines.slice(-200).join("\n");
      (_a3 = getMainWindow()) == null ? void 0 : _a3.webContents.send("backend:error", { code, logs });
    }
  });
}
function stopBackend() {
  if (!backendProcess)
    return;
  const pid = backendProcess.pid;
  console.log("[Backend] Stopping...");
  appendBackendLog("[Backend] Stopping...");
  if (!pid) {
    backendProcess = null;
    return;
  }
  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", String(pid), "/f", "/t"]);
  } else {
    try {
      process.kill(-pid, "SIGTERM");
    } catch {
      try {
        process.kill(pid, "SIGTERM");
      } catch {
      }
    }
    setTimeout(() => {
      try {
        process.kill(-pid, "SIGKILL");
      } catch {
        try {
          process.kill(pid, "SIGKILL");
        } catch {
        }
      }
    }, 200);
  }
  backendProcess = null;
}
function registerHotkeys() {
  globalShortcut.register("CommandOrControl+Shift+N", () => {
    const win = getMainWindow();
    if (!win)
      return;
    const state = getFloatingState();
    if (state === "classic") {
      if (win.isVisible()) {
        win.hide();
      } else {
        win.show();
        win.focus();
      }
    } else if (state === "ball") {
      if (win.isVisible()) {
        expandFloatingWindow();
        win.focus();
      } else {
        win.show();
      }
    } else if (state === "compact" || state === "full") {
      collapseFloatingWindow();
    }
  });
}
function unregisterHotkeys() {
  globalShortcut.unregisterAll();
}
function createMenu() {
  const isMac = process.platform === "darwin";
  const template = [
    ...isMac ? [{
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
        ...isMac ? [
          { type: "separator" },
          { role: "front", label: "前置全部窗口" }
        ] : [
          { role: "close", label: "关闭" }
        ]
      ]
    }
  ];
  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}
let tray = null;
function createTray() {
  const isWin = process.platform === "win32";
  const baseDir = app.isPackaged ? process.resourcesPath : app.getAppPath();
  let icon;
  try {
    const pngPath = join(baseDir, "public", "my.png");
    icon = nativeImage.createFromPath(pngPath);
    if (isWin) {
      icon = icon.resize({ width: 32, height: 32 });
    } else {
      icon = icon.resize({ width: 64, height: 64 }).resize({ width: 22, height: 22 });
    }
  } catch {
    icon = nativeImage.createEmpty();
  }
  tray = new Tray(icon);
  tray.setToolTip("弥娅 AI");
  const contextMenu = Menu.buildFromTemplate([
    {
      label: "显示窗口",
      click: () => {
        const win = getMainWindow();
        if (win) {
          win.show();
          win.focus();
        }
      }
    },
    { type: "separator" },
    {
      label: "退出",
      click: () => {
        app.quit();
      }
    }
  ]);
  tray.setContextMenu(contextMenu);
  tray.on("click", () => {
    const win = getMainWindow();
    if (win) {
      if (win.isVisible()) {
        win.focus();
      } else {
        win.show();
      }
    }
  });
  return tray;
}
function destroyTray() {
  if (tray) {
    tray.destroy();
    tray = null;
  }
}
let autoUpdater = null;
async function setupAutoUpdater(win) {
  var _a2;
  try {
    const pkg = await import("electron-updater");
    autoUpdater = pkg.autoUpdater ?? ((_a2 = pkg.default) == null ? void 0 : _a2.autoUpdater) ?? pkg.default ?? null;
  } catch {
    console.warn("[Updater] electron-updater not available");
    return;
  }
  if (!autoUpdater || typeof autoUpdater.checkForUpdates !== "function") {
    console.warn("[Updater] autoUpdater unavailable after import");
    autoUpdater = null;
    return;
  }
  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = true;
  autoUpdater.on("update-available", (info) => {
    win.webContents.send("updater:update-available", {
      version: info.version,
      releaseNotes: info.releaseNotes
    });
  });
  autoUpdater.on("update-not-available", () => {
    win.webContents.send("updater:update-not-available");
  });
  autoUpdater.on("download-progress", (progress) => {
    win.webContents.send("updater:download-progress", {
      percent: progress.percent,
      bytesPerSecond: progress.bytesPerSecond
    });
  });
  autoUpdater.on("update-downloaded", () => {
    win.webContents.send("updater:update-downloaded");
  });
  autoUpdater.on("error", (err) => {
    win.webContents.send("updater:error", err.message);
  });
  setTimeout(() => {
    autoUpdater.checkForUpdates().catch(() => {
    });
  }, 3e3);
}
function downloadUpdate() {
  autoUpdater == null ? void 0 : autoUpdater.downloadUpdate();
}
function installUpdate() {
  autoUpdater == null ? void 0 : autoUpdater.quitAndInstall();
}
let isQuitting = false;
(_a = process.stdout) == null ? void 0 : _a.on("error", () => {
});
(_b = process.stderr) == null ? void 0 : _b.on("error", () => {
});
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
}
const CHARACTERS_DIR = app.isPackaged ? resolve(process.resourcesPath, "characters") : resolve(dirname(fileURLToPath(import.meta.url)), "..", "..", "characters");
const DEFAULT_CHARACTER = "弥娅";
const BACKGROUNDS_DIR = app.isPackaged ? resolve(process.resourcesPath, "premium-assets", "backgrounds") : resolve(dirname(fileURLToPath(import.meta.url)), "..", "premium-assets", "backgrounds");
protocol.registerSchemesAsPrivileged([
  { scheme: "miya-char", privileges: { secure: true, supportFetchAPI: true, corsEnabled: true, standard: true, stream: true } },
  { scheme: "miya-bg", privileges: { secure: true, supportFetchAPI: true, corsEnabled: true, standard: true, stream: true } },
  { scheme: "miya-app", privileges: { secure: true, supportFetchAPI: true, corsEnabled: true, standard: true, stream: true } }
]);
app.on("second-instance", () => {
  const win = getMainWindow();
  if (win) {
    if (win.isMinimized())
      win.restore();
    win.show();
    win.focus();
  }
});
app.whenReady().then(async () => {
  const MEDIA_MIME = {
    mp3: "audio/mpeg",
    wav: "audio/wav",
    ogg: "audio/ogg",
    m4a: "audio/mp4",
    flac: "audio/flac",
    aac: "audio/aac",
    webm: "audio/webm",
    mp4: "video/mp4",
    mkv: "video/x-matroska"
  };
  const FILE_MIME = {
    ...MEDIA_MIME,
    json: "application/json; charset=utf-8",
    txt: "text/plain; charset=utf-8",
    png: "image/png",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    webp: "image/webp",
    svg: "image/svg+xml",
    moc3: "application/octet-stream"
  };
  function resolveCustomProtocolPath(requestUrl, baseDir) {
    try {
      const url = new URL(requestUrl);
      const host = domainToUnicode(url.hostname || "");
      const pathname = decodeURIComponent(url.pathname).replace(/^\/+/, "");
      const relativePath = [host, pathname].filter(Boolean).join("/");
      const filePath = resolve(baseDir, relativePath);
      if (!filePath.startsWith(baseDir)) {
        return null;
      }
      return filePath;
    } catch {
      return null;
    }
  }
  function serveLocalFile(filePath, notFoundMessage = "Not Found") {
    var _a2;
    try {
      const data = readFileSync(filePath);
      const ext = ((_a2 = filePath.split(".").pop()) == null ? void 0 : _a2.toLowerCase()) ?? "";
      const mime = FILE_MIME[ext] || "application/octet-stream";
      return new Response(data, {
        headers: {
          "Content-Type": mime,
          "Content-Length": data.length.toString(),
          "Cache-Control": "no-cache"
        }
      });
    } catch {
      return new Response(notFoundMessage, { status: 404 });
    }
  }
  const appDistDir = resolve(dirname(fileURLToPath(import.meta.url)), "..", "dist");
  protocol.handle("miya-app", (request) => {
    var _a2;
    const rawPath = decodeURIComponent(new URL(request.url).pathname).replace(/^\/+/, "");
    const relativePath = rawPath.startsWith("dist/") ? rawPath.slice(5) : rawPath;
    const basePath = resolve(appDistDir, relativePath);
    if (!basePath.startsWith(appDistDir)) {
      return new Response("Forbidden", { status: 403 });
    }
    const ext = ((_a2 = basePath.split(".").pop()) == null ? void 0 : _a2.toLowerCase()) ?? "";
    const mime = MEDIA_MIME[ext];
    if (mime) {
      try {
        const data = readFileSync(basePath);
        return new Response(data, {
          headers: { "Content-Type": mime, "Content-Length": data.length.toString() }
        });
      } catch {
        return new Response("Not Found", { status: 404 });
      }
    }
    return net.fetch(pathToFileURL(basePath).toString());
  });
  protocol.handle("miya-char", (request) => {
    try {
      const url = new URL(request.url);
      let host = domainToUnicode(url.hostname || "");
      const pathname = decodeURIComponent(url.pathname).replace(/^\/+/, "");
      if (!host) {
        host = DEFAULT_CHARACTER;
      }
      const relativePath = [host, pathname].filter(Boolean).join("/");
      const filePath = resolve(CHARACTERS_DIR, relativePath);
      if (!filePath.startsWith(CHARACTERS_DIR)) {
        return new Response("Forbidden", { status: 403 });
      }
      return serveLocalFile(filePath, "Character Asset Not Found");
    } catch {
      return new Response("Forbidden", { status: 403 });
    }
  });
  protocol.handle("miya-bg", (request) => {
    const filePath = resolveCustomProtocolPath(request.url, BACKGROUNDS_DIR);
    if (!filePath) {
      return new Response("Forbidden", { status: 403 });
    }
    return serveLocalFile(filePath, "Background Asset Not Found");
  });
  nativeTheme.themeSource = "dark";
  createMenu();
  const win = createWindow();
  let preMaximizeBounds = null;
  createTray();
  registerHotkeys();
  void setupAutoUpdater(win);
  ipcMain.on("window:minimize", () => {
    var _a2;
    return (_a2 = getMainWindow()) == null ? void 0 : _a2.minimize();
  });
  ipcMain.on("window:maximize", () => {
    const w = getMainWindow();
    if (w) {
      if (w.isMaximized()) {
        w.unmaximize();
      } else {
        preMaximizeBounds = w.getBounds();
        w.maximize();
      }
    }
  });
  ipcMain.on("window:close", () => {
    var _a2;
    const state = getFloatingState();
    if (state === "compact" || state === "full") {
      collapseFloatingWindow();
    } else if (state === "classic") {
      enterFloatingMode();
    } else {
      (_a2 = getMainWindow()) == null ? void 0 : _a2.hide();
    }
  });
  ipcMain.handle("window:isMaximized", () => {
    var _a2;
    return ((_a2 = getMainWindow()) == null ? void 0 : _a2.isMaximized()) ?? false;
  });
  ipcMain.handle("window:getBounds", () => {
    var _a2;
    return ((_a2 = getMainWindow()) == null ? void 0 : _a2.getBounds()) ?? { x: 0, y: 0, width: 1280, height: 800 };
  });
  ipcMain.on("window:setBounds", (_event, bounds) => {
    const win2 = getMainWindow();
    if (!win2 || win2.isMaximized())
      return;
    const current = win2.getBounds();
    const next = {
      x: bounds.x ?? current.x,
      y: bounds.y ?? current.y,
      width: Math.max(800, bounds.width ?? current.width),
      height: Math.max(600, bounds.height ?? current.height)
    };
    win2.setBounds(next);
  });
  ipcMain.handle("floating:enter", () => {
    enterFloatingMode();
  });
  ipcMain.handle("floating:exit", () => {
    exitFloatingMode();
  });
  ipcMain.handle("floating:expand", (_event, toFull) => {
    expandFloatingWindow(toFull ?? false);
  });
  ipcMain.handle("floating:expandToFull", () => {
    expandCompactToFull();
  });
  ipcMain.handle("floating:collapse", () => {
    collapseFloatingWindow();
  });
  ipcMain.handle("floating:collapseToCompact", () => {
    collapseFullToCompact();
  });
  ipcMain.handle("floating:getState", () => getFloatingState());
  ipcMain.on("floating:pin", (_event, pinned) => {
    const w = getMainWindow();
    if (w) {
      w.setSkipTaskbar(!pinned);
    }
  });
  ipcMain.on("floating:setPosition", (_event, x, y) => {
    setWindowPosition(x, y);
  });
  ipcMain.on("floating:fitHeight", (_event, height) => {
    setFloatingHeight(height);
  });
  ipcMain.on("updater:download", () => downloadUpdate());
  ipcMain.on("updater:install", () => installUpdate());
  ipcMain.on("app:quit", () => {
    isQuitting = true;
    app.quit();
  });
  ipcMain.on("context-menu:show", () => {
    const menu = Menu.buildFromTemplate([
      {
        label: "打开主界面",
        click: () => exitFloatingMode()
      },
      {
        label: "隐藏到托盘",
        click: () => {
          var _a2;
          return (_a2 = getMainWindow()) == null ? void 0 : _a2.hide();
        }
      },
      { type: "separator" },
      {
        label: "退出应用",
        click: () => {
          isQuitting = true;
          app.quit();
        }
      }
    ]);
    menu.popup();
  });
  ipcMain.handle("capture:getSources", async () => {
    if (process.platform === "darwin") {
      const status = systemPreferences.getMediaAccessStatus("screen");
      if (status !== "granted") {
        return { permission: status };
      }
    }
    try {
      const sources = await desktopCapturer.getSources({
        types: ["window", "screen"],
        thumbnailSize: { width: 320, height: 180 },
        fetchWindowIcons: true
      });
      return sources.map((s) => {
        var _a2;
        return {
          id: s.id,
          name: s.name,
          thumbnail: s.thumbnail.toDataURL(),
          appIcon: ((_a2 = s.appIcon) == null ? void 0 : _a2.toDataURL()) || null
        };
      });
    } catch {
      return { permission: "denied" };
    }
  });
  ipcMain.handle("capture:captureWindow", async (_event, sourceId) => {
    const sources = await desktopCapturer.getSources({
      types: ["window", "screen"],
      thumbnailSize: { width: 1920, height: 1080 }
    });
    const target = sources.find((s) => s.id === sourceId);
    if (!target)
      return null;
    return target.thumbnail.toDataURL();
  });
  ipcMain.handle("capture:openScreenSettings", async () => {
    if (process.platform === "darwin") {
      await shell.openExternal("x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture");
    }
  });
  ipcMain.handle("backgrounds:scan", async () => {
    try {
      const files = await readdir(BACKGROUNDS_DIR);
      const imageExts = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"];
      return files.filter((f) => imageExts.some((ext) => f.toLowerCase().endsWith(ext)));
    } catch {
      return [];
    }
  });
  ipcMain.handle("fs:writeFile", (_event, relPath, base64) => {
    const base = app.isPackaged ? resolve(process.resourcesPath) : resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
    const filePath = resolve(base, relPath);
    mkdirSync(dirname(filePath), { recursive: true });
    writeFileSync(filePath, Buffer.from(base64, "base64"));
  });
  ipcMain.handle("autoLaunch:get", () => {
    return app.getLoginItemSettings().openAtLogin;
  });
  ipcMain.handle("autoLaunch:set", (_event, enabled) => {
    app.setLoginItemSettings({ openAtLogin: enabled });
  });
  ipcMain.handle("backend:getLogs", () => getBackendLogs());
  win.on("close", (event) => {
    if (!isQuitting) {
      event.preventDefault();
      win.hide();
    }
  });
  win.on("maximize", () => win.webContents.send("window:maximized", true));
  win.on("unmaximize", () => {
    win.webContents.send("window:maximized", false);
    if (preMaximizeBounds) {
      win.setBounds(preMaximizeBounds);
      preMaximizeBounds = null;
    }
  });
  win.on("blur", () => {
    win.webContents.send("floating:windowBlur");
  });
  app.on("activate", () => {
    var _a2;
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else {
      (_a2 = getMainWindow()) == null ? void 0 : _a2.show();
    }
  });
  startBackend();
});
app.on("before-quit", () => {
  isQuitting = true;
});
app.on("will-quit", () => {
  unregisterHotkeys();
  destroyTray();
  stopBackend();
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
