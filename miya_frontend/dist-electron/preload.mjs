"use strict";
const electron = require("electron");
function detectPlatform() {
  var _a;
  const uaDataPlatform = (_a = navigator.userAgentData) == null ? void 0 : _a.platform;
  const parts = [
    uaDataPlatform,
    navigator.platform,
    navigator.userAgent
  ].filter(Boolean).join(" ").toLowerCase();
  if (parts.includes("mac"))
    return "darwin";
  if (parts.includes("win"))
    return "win32";
  if (parts.includes("linux"))
    return "linux";
  return "unknown";
}
const electronAPI = {
  // Window controls
  minimize: () => electron.ipcRenderer.send("window:minimize"),
  maximize: () => electron.ipcRenderer.send("window:maximize"),
  close: () => electron.ipcRenderer.send("window:close"),
  isMaximized: () => electron.ipcRenderer.invoke("window:isMaximized"),
  getBounds: () => electron.ipcRenderer.invoke("window:getBounds"),
  setBounds: (bounds) => electron.ipcRenderer.send("window:setBounds", bounds),
  quit: () => electron.ipcRenderer.send("app:quit"),
  showContextMenu: () => electron.ipcRenderer.send("context-menu:show"),
  // Window state events
  onMaximized: (callback) => {
    const handler = (_event, maximized) => callback(maximized);
    electron.ipcRenderer.on("window:maximized", handler);
    return () => electron.ipcRenderer.removeListener("window:maximized", handler);
  },
  // Updater
  downloadUpdate: () => electron.ipcRenderer.send("updater:download"),
  installUpdate: () => electron.ipcRenderer.send("updater:install"),
  onUpdateAvailable: (callback) => {
    const handler = (_event, info) => callback(info);
    electron.ipcRenderer.on("updater:update-available", handler);
    return () => electron.ipcRenderer.removeListener("updater:update-available", handler);
  },
  onUpdateDownloaded: (callback) => {
    const handler = () => callback();
    electron.ipcRenderer.on("updater:update-downloaded", handler);
    return () => electron.ipcRenderer.removeListener("updater:update-downloaded", handler);
  },
  // 悬浮球模式控制
  floating: {
    enter: () => electron.ipcRenderer.invoke("floating:enter"),
    exit: () => electron.ipcRenderer.invoke("floating:exit"),
    expand: (toFull) => electron.ipcRenderer.invoke("floating:expand", toFull),
    expandToFull: () => electron.ipcRenderer.invoke("floating:expandToFull"),
    collapse: () => electron.ipcRenderer.invoke("floating:collapse"),
    collapseToCompact: () => electron.ipcRenderer.invoke("floating:collapseToCompact"),
    getState: () => electron.ipcRenderer.invoke("floating:getState"),
    pin: (value) => electron.ipcRenderer.send("floating:pin", value),
    fitHeight: (height) => electron.ipcRenderer.send("floating:fitHeight", height),
    setPosition: (x, y) => electron.ipcRenderer.send("floating:setPosition", x, y),
    onStateChange: (callback) => {
      const handler = (_event, state) => callback(state);
      electron.ipcRenderer.on("floating:stateChanged", handler);
      return () => electron.ipcRenderer.removeListener("floating:stateChanged", handler);
    },
    onWindowBlur: (callback) => {
      const handler = () => callback();
      electron.ipcRenderer.on("floating:windowBlur", handler);
      return () => electron.ipcRenderer.removeListener("floating:windowBlur", handler);
    }
  },
  // 窗口截屏功能
  capture: {
    getSources: () => electron.ipcRenderer.invoke("capture:getSources"),
    captureWindow: (sourceId) => electron.ipcRenderer.invoke("capture:captureWindow", sourceId),
    openScreenSettings: () => electron.ipcRenderer.invoke("capture:openScreenSettings")
  },
  // 后端进程通信
  backend: {
    getLogs: () => electron.ipcRenderer.invoke("backend:getLogs"),
    onProgress: (callback) => {
      const handler = (_event, payload) => callback(payload);
      electron.ipcRenderer.on("backend:progress", handler);
      return () => electron.ipcRenderer.removeListener("backend:progress", handler);
    },
    onLog: (callback) => {
      const handler = (_event, payload) => callback(payload);
      electron.ipcRenderer.on("backend:log", handler);
      return () => electron.ipcRenderer.removeListener("backend:log", handler);
    },
    onError: (callback) => {
      const handler = (_event, payload) => callback(payload);
      electron.ipcRenderer.on("backend:error", handler);
      return () => electron.ipcRenderer.removeListener("backend:error", handler);
    }
  },
  // 背景图片扫描
  backgrounds: {
    scan: () => electron.ipcRenderer.invoke("backgrounds:scan")
  },
  // 文件写入（用于保存背景图片，base64 编码）
  writeFile: (relPath, base64) => electron.ipcRenderer.invoke("fs:writeFile", relPath, base64),
  // 开机自启动
  autoLaunch: {
    get: () => electron.ipcRenderer.invoke("autoLaunch:get"),
    set: (enabled) => electron.ipcRenderer.invoke("autoLaunch:set", enabled)
  },
  // Platform info
  platform: detectPlatform()
};
electron.contextBridge.exposeInMainWorld("electronAPI", electronAPI);
