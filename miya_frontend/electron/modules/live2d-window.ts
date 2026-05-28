import { dirname, join, resolve } from 'node:path'
import fs from 'node:fs'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { app, BrowserWindow, screen } from 'electron'
import type { Live2DCallback } from './types'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

let live2dWindow: BrowserWindow | null = null
let live2dCallback: Live2DCallback | null = null

const DEFAULT_SIZE = { width: 400, height: 600 }

function resolveLive2dUrl(): string {
  if (process.env.VITE_DEV_SERVER_URL) {
    const devBase = process.env.VITE_DEV_SERVER_URL.replace(/\/+$/, '')
    return `${devBase}/src/live2d-app/index.html`
  }

  // Production: look in dist/live2d-app first, then src/live2d-app as fallback
  const distPath = resolve(__dirname, '..', 'dist', 'live2d-app', 'index.html')
  if (fs.existsSync(distPath)) {
    return `file://${distPath}`
  }

  const srcPath = resolve(__dirname, '..', '..', 'src', 'live2d-app', 'index.html')
  if (fs.existsSync(srcPath)) {
    return `file://${srcPath}`
  }

  console.warn('[Live2D Window] live2d-app/index.html not found, window will not load')
  return ''
}

export function createLive2dWindow(
  callback?: Live2DCallback,
  alwaysOnTop = true,
): BrowserWindow | null {
  live2dCallback = callback ?? live2dCallback

  if (live2dWindow && !live2dWindow.isDestroyed()) {
    live2dWindow.setAlwaysOnTop(alwaysOnTop)
    live2dWindow.show()
    return live2dWindow
  }

  const url = resolveLive2dUrl()
  if (!url) return null

  const primaryDisplay = screen.getPrimaryDisplay()
  const { workArea } = primaryDisplay
  const x = workArea.x + workArea.width - DEFAULT_SIZE.width - 20
  const y = workArea.y + workArea.height - DEFAULT_SIZE.height - 60

  live2dWindow = new BrowserWindow({
    x,
    y,
    width: DEFAULT_SIZE.width,
    height: DEFAULT_SIZE.height,
    minWidth: 200,
    minHeight: 300,
    frame: false,
    transparent: true,
    alwaysOnTop,
    skipTaskbar: true,
    resizable: true,
    hasShadow: false,
    show: true,
    webPreferences: {
      preload: join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      webgl: true,
    },
  })

  live2dWindow.setAspectRatio(2 / 3)
  live2dWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })

  live2dWindow.loadURL(url).catch(err => {
    console.warn('[Live2D Window] loadURL failed:', err.message)
  })

  live2dWindow.webContents.on('did-finish-load', () => {
    live2dWindow?.webContents.executeJavaScript(
      'window.__MIYA_API_PORT__ = 8000'
    ).catch(() => {})
  })

  live2dWindow.on('closed', () => {
    live2dWindow = null
  })

  live2dWindow.webContents.on('did-fail-load', (_e, errorCode, errorDescription) => {
    console.warn(`[Live2D Window] load failed: ${errorCode} - ${errorDescription}`)
  })

  if (process.env.VITE_DEV_SERVER_URL) {
    live2dWindow.webContents.openDevTools({ mode: 'detach' })
  }

  return live2dWindow
}

export function getLive2dWindow(): BrowserWindow | null {
  if (!live2dWindow) return null
  try {
    if (live2dWindow.isDestroyed()) {
      live2dWindow = null
      return null
    }
    return live2dWindow
  }
  catch {
    live2dWindow = null
    return null
  }
}

export function toggleLive2dVisibility(): void {
  const win = getLive2dWindow()
  if (!win) return
  win.isVisible() ? win.hide() : win.show()
  broadcastLive2dCommand('live2d:visibilityChanged', win.isVisible())
}

export function setLive2dAlwaysOnTop(enabled: boolean): void {
  const win = getLive2dWindow()
  if (win) win.setAlwaysOnTop(enabled)
}

export function resetLive2dPosition(): void {
  const win = getLive2dWindow()
  if (!win) return
  const primaryDisplay = screen.getPrimaryDisplay()
  const { workArea } = primaryDisplay
  const x = workArea.x + workArea.width - DEFAULT_SIZE.width - 20
  const y = workArea.y + workArea.height - DEFAULT_SIZE.height - 60
  win.setBounds({ x, y, width: DEFAULT_SIZE.width, height: DEFAULT_SIZE.height })
}

export function setLive2dWindowScale(scale: number): void {
  const win = getLive2dWindow()
  if (!win) return
  const ratio = 2 / 3
  const newWidth = Math.round(DEFAULT_SIZE.width * scale / 100)
  const newHeight = Math.round(newWidth / ratio)
  win.setSize(newWidth, newHeight)
}

export function broadcastLive2dCommand(channel: string, ...args: unknown[]): void {
  const win = getLive2dWindow()
  if (!win) return
  try {
    win.webContents.send(channel, ...args)
  }
  catch {
    // Window destroyed between check and send — ignore
  }
}
