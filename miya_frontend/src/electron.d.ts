export type FloatingState = 'classic' | 'ball' | 'compact' | 'full'

export interface CaptureSource {
  id: string
  name: string
  thumbnail: string
  appIcon: string | null
}

interface CaptureAPI {
  getSources: () => Promise<CaptureSource[] | { permission: string }>
  captureWindow: (sourceId: string) => Promise<string | null>
  openScreenSettings: () => Promise<void>
}

interface BackendAPI {
  getLogs: () => Promise<string>
  onProgress: (callback: (payload: { percent: number, phase: string }) => void) => () => void
  onLog: (callback: (payload: { line: string }) => void) => () => void
  onError: (callback: (payload: { code: number, logs: string }) => void) => () => void
}

interface FloatingAPI {
  enter: () => Promise<void>
  exit: () => Promise<void>
  expand: (toFull?: boolean) => Promise<void>
  expandToFull: () => Promise<void>
  collapse: () => Promise<void>
  collapseToCompact: () => Promise<void>
  getState: () => Promise<FloatingState>
  pin: (value: boolean) => void
  fitHeight: (height: number) => void
  setPosition: (x: number, y: number) => void
  onStateChange: (callback: (state: FloatingState) => void) => () => void
  onWindowBlur: (callback: () => void) => () => void
}

interface BackgroundsAPI {
  scan: () => Promise<string[]>
}

interface AutoLaunchAPI {
  get: () => Promise<boolean>
  set: (enabled: boolean) => Promise<void>
}

interface TerminalAPI {
  start: (options?: { model?: string }) => Promise<void>
  write: (data: string) => Promise<void>
  resize: (cols: number, rows: number) => Promise<void>
  stop: () => Promise<void>
  isRunning: () => Promise<boolean>
  getBuffer: () => Promise<string>
  onData: (callback: (data: string) => void) => () => void
  onExit: (callback: (code: number) => void) => () => void
}

export interface Live2dAPI {
  setEmotion: (emotion: string) => void
  setState: (state: string) => void
  setMouth: (params: Record<string, number>) => void
  triggerAction: (action: string) => void
  setTracking: (enabled: boolean) => void
  switchClothes: (clothes: string) => void
  toggleVisibility: () => void
  setAlwaysOnTop: (enabled: boolean) => void
  resetPosition: () => void
  setBackground: (colorHex: string, alpha: number) => void
  setWindowScale: (scale: number) => void
  positionRelative: (bounds?: { x: number, y: number, width: number, height: number }) => void
  onReady: (callback: () => void) => () => void
  onModelInfo: (callback: (info: { faceX: number, faceY: number }) => void) => () => void
}

export interface ElectronAPI {
  minimize: () => void
  maximize: () => void
  close: () => void
  isMaximized: () => Promise<boolean>
  getBounds: () => Promise<{ x: number, y: number, width: number, height: number }>
  setBounds: (bounds: { x?: number, y?: number, width?: number, height?: number }) => void
  quit: () => void
  showContextMenu: () => void
  onMaximized: (callback: (maximized: boolean) => void) => () => void
  downloadUpdate: () => void
  installUpdate: () => void
  onUpdateAvailable: (callback: (info: { version: string, releaseNotes: string }) => void) => () => void
  onUpdateDownloaded: (callback: () => void) => () => void
  floating: FloatingAPI
  capture: CaptureAPI
  backend: BackendAPI
  backgrounds: BackgroundsAPI
  autoLaunch: AutoLaunchAPI
  terminal: TerminalAPI
  writeFile: (relPath: string, base64: string) => Promise<void>
  platform: string
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
    live2dAPI?: Live2dAPI
  }
}

export {}
