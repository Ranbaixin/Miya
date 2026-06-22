import { contextBridge, ipcRenderer } from 'electron'

function detectPlatform(): 'darwin' | 'win32' | 'linux' | 'unknown' {
  const uaDataPlatform = (navigator as Navigator & { userAgentData?: { platform?: string } }).userAgentData?.platform
  const parts = [
    uaDataPlatform,
    navigator.platform,
    navigator.userAgent,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()

  if (parts.includes('mac'))
    return 'darwin'
  if (parts.includes('win'))
    return 'win32'
  if (parts.includes('linux'))
    return 'linux'
  return 'unknown'
}

const electronAPI = {
  // Window controls
  minimize: () => ipcRenderer.send('window:minimize'),
  maximize: () => ipcRenderer.send('window:maximize'),
  close: () => ipcRenderer.send('window:close'),
  isMaximized: () => ipcRenderer.invoke('window:isMaximized'),
  getBounds: () => ipcRenderer.invoke('window:getBounds') as Promise<{ x: number, y: number, width: number, height: number }>,
  setBounds: (bounds: { x?: number, y?: number, width?: number, height?: number }) => ipcRenderer.send('window:setBounds', bounds),
  quit: () => ipcRenderer.send('app:quit'),
  showContextMenu: () => ipcRenderer.send('context-menu:show'),

  // Window state events
  onMaximized: (callback: (maximized: boolean) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, maximized: boolean) => callback(maximized)
    ipcRenderer.on('window:maximized', handler)
    return () => ipcRenderer.removeListener('window:maximized', handler)
  },

  // Updater
  downloadUpdate: () => ipcRenderer.send('updater:download'),
  installUpdate: () => ipcRenderer.send('updater:install'),

  onUpdateAvailable: (callback: (info: { version: string, releaseNotes: string }) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, info: { version: string, releaseNotes: string }) => callback(info)
    ipcRenderer.on('updater:update-available', handler)
    return () => ipcRenderer.removeListener('updater:update-available', handler)
  },
  onUpdateDownloaded: (callback: () => void) => {
    const handler = () => callback()
    ipcRenderer.on('updater:update-downloaded', handler)
    return () => ipcRenderer.removeListener('updater:update-downloaded', handler)
  },

  // 悬浮球模式控制
  floating: {
    enter: () => ipcRenderer.invoke('floating:enter'),
    exit: () => ipcRenderer.invoke('floating:exit'),
    expand: (toFull?: boolean) => ipcRenderer.invoke('floating:expand', toFull),
    expandToFull: () => ipcRenderer.invoke('floating:expandToFull'),
    collapse: () => ipcRenderer.invoke('floating:collapse'),
    collapseToCompact: () => ipcRenderer.invoke('floating:collapseToCompact'),
    getState: () => ipcRenderer.invoke('floating:getState') as Promise<'classic' | 'ball' | 'compact' | 'full'>,
    pin: (value: boolean) => ipcRenderer.send('floating:pin', value),
    fitHeight: (height: number) => ipcRenderer.send('floating:fitHeight', height),
    setPosition: (x: number, y: number) => ipcRenderer.send('floating:setPosition', x, y),
    onStateChange: (callback: (state: 'classic' | 'ball' | 'compact' | 'full') => void) => {
      const handler = (_event: Electron.IpcRendererEvent, state: 'classic' | 'ball' | 'compact' | 'full') => callback(state)
      ipcRenderer.on('floating:stateChanged', handler)
      return () => ipcRenderer.removeListener('floating:stateChanged', handler)
    },
    onWindowBlur: (callback: () => void) => {
      const handler = () => callback()
      ipcRenderer.on('floating:windowBlur', handler)
      return () => ipcRenderer.removeListener('floating:windowBlur', handler)
    },
  },

  // 窗口截屏功能
  capture: {
    getSources: () => ipcRenderer.invoke('capture:getSources') as Promise<
      | { permission: string }
      | Array<{ id: string, name: string, thumbnail: string, appIcon: string | null }>
    >,
    captureWindow: (sourceId: string) => ipcRenderer.invoke('capture:captureWindow', sourceId) as Promise<string | null>,
    openScreenSettings: () => ipcRenderer.invoke('capture:openScreenSettings') as Promise<void>,
  },

  // 后端进程通信
  backend: {
    getLogs: () => ipcRenderer.invoke('backend:getLogs') as Promise<string>,
    onProgress: (callback: (payload: { percent: number, phase: string }) => void) => {
      const handler = (_event: Electron.IpcRendererEvent, payload: { percent: number, phase: string }) => callback(payload)
      ipcRenderer.on('backend:progress', handler)
      return () => ipcRenderer.removeListener('backend:progress', handler)
    },
    onLog: (callback: (payload: { line: string }) => void) => {
      const handler = (_event: Electron.IpcRendererEvent, payload: { line: string }) => callback(payload)
      ipcRenderer.on('backend:log', handler)
      return () => ipcRenderer.removeListener('backend:log', handler)
    },
    onError: (callback: (payload: { code: number, logs: string }) => void) => {
      const handler = (_event: Electron.IpcRendererEvent, payload: { code: number, logs: string }) => callback(payload)
      ipcRenderer.on('backend:error', handler)
      return () => ipcRenderer.removeListener('backend:error', handler)
    },
  },

  // 背景图片扫描
  backgrounds: {
    scan: () => ipcRenderer.invoke('backgrounds:scan') as Promise<string[]>,
  },

  // 文件写入（用于保存背景图片，base64 编码）
  writeFile: (relPath: string, base64: string) =>
    ipcRenderer.invoke('fs:writeFile', relPath, base64) as Promise<void>,

  // 开机自启动
  autoLaunch: {
    get: () => ipcRenderer.invoke('autoLaunch:get') as Promise<boolean>,
    set: (enabled: boolean) => ipcRenderer.invoke('autoLaunch:set', enabled) as Promise<void>,
  },

  // Terminal (Claude Code Engine)
  terminal: {
    start: (options?: { model?: string }) => ipcRenderer.invoke('terminal:start', options) as Promise<void>,
    write: (data: string) => ipcRenderer.invoke('terminal:write', data),
    resize: (cols: number, rows: number) => ipcRenderer.invoke('terminal:resize', cols, rows),
    stop: () => ipcRenderer.invoke('terminal:stop'),
    isRunning: () => ipcRenderer.invoke('terminal:isRunning') as Promise<boolean>,
    getBuffer: () => ipcRenderer.invoke('terminal:getBuffer') as Promise<string>,
    onData: (callback: (data: string) => void) => {
      const handler = (_event: Electron.IpcRendererEvent, data: string) => callback(data)
      ipcRenderer.on('terminal:data', handler)
      return () => ipcRenderer.removeListener('terminal:data', handler)
    },
    onExit: (callback: (code: number) => void) => {
      const handler = (_event: Electron.IpcRendererEvent, code: number) => callback(code)
      ipcRenderer.on('terminal:exit', handler)
      return () => ipcRenderer.removeListener('terminal:exit', handler)
    },
  },

  // Platform info
  platform: detectPlatform(),

  // Artboard window
  artboard: {
    open: () => ipcRenderer.invoke('artboard:open'),
    close: () => ipcRenderer.invoke('artboard:close'),
    toggle: () => ipcRenderer.invoke('artboard:toggle'),
  },
}

contextBridge.exposeInMainWorld('electronAPI', electronAPI)

// ── Live2D 独立窗口 API (主窗口侧 → 发送) ──
contextBridge.exposeInMainWorld('live2dAPI', {
  setEmotion: (emotion: string) => ipcRenderer.send('live2d:emotion', emotion),
  setState: (state: string) => ipcRenderer.send('live2d:state', state),
  setMouth: (params: Record<string, number>) => ipcRenderer.send('live2d:mouth', params),
  triggerAction: (action: string) => ipcRenderer.send('live2d:action', action),
  setTracking: (enabled: boolean) => ipcRenderer.send('live2d:tracking', enabled),
  switchClothes: (clothes: string) => ipcRenderer.send('live2d:clothes', clothes),
  toggleVisibility: () => ipcRenderer.send('live2d:toggleVisibility'),
  setAlwaysOnTop: (enabled: boolean) => ipcRenderer.send('live2d:alwaysOnTop', enabled),
  resetPosition: () => ipcRenderer.send('live2d:resetPosition'),
  setBackground: (colorHex: string, alpha: number) => ipcRenderer.send('live2d:background', { color: colorHex, alpha }),
  setWindowScale: (scale: number) => ipcRenderer.send('live2d:windowScale', scale),
  positionRelative: (bounds?: { x: number, y: number, width: number, height: number }) => ipcRenderer.send('live2d:positionRelative', bounds),
})

// ── Live2D 窗口侧 IPC 接收 ──
contextBridge.exposeInMainWorld('live2dIPC', {
  on: (channel: string, handler: (...args: unknown[]) => void) => {
    const safeHandler = (_event: Electron.IpcRendererEvent, ...args: unknown[]) => handler(...args)
    ipcRenderer.on(channel, safeHandler)
  },
  send: (channel: string, ...args: unknown[]) => {
    ipcRenderer.send(channel, ...args)
  },
})
