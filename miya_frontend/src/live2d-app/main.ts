import * as PIXI from 'pixi.js'
import { Live2DModel } from 'pixi-live2d-display/cubism4'
import { ensureLive2dCoreLoaded } from '../utils/live2dCoreLoader'
import { initStandaloneController, destroyStandaloneController } from './standalone-controller'

;(window as Window & typeof globalThis & { PIXI: typeof PIXI }).PIXI = PIXI

const MODEL_SOURCE = 'miya-char://弥娅/Miya/01.model3.json'
const SSAA = 1.5

let app: PIXI.Application
let nativeWidth = 0
let nativeHeight = 0

function layoutCanvas(canvas: HTMLCanvasElement) {
  const rw = canvas.clientWidth * SSAA
  const rh = canvas.clientHeight * SSAA
  canvas.width = rw
  canvas.height = rh
}

function relayoutModel(model: Live2DModel, canvas: HTMLCanvasElement) {
  if (nativeWidth === 0) return
  const cw = canvas.width
  const ch = canvas.height
  const s = Math.min(cw / nativeWidth, ch / nativeHeight) * 0.85
  model.scale.set(s)
  model.x = (cw - nativeWidth * s) / 2
  model.y = (ch - nativeHeight * s) / 2
}

async function boot(): Promise<void> {
  const canvas = document.getElementById('live2d-canvas') as HTMLCanvasElement | null
  if (!canvas) {
    console.error('[Live2D App] canvas not found')
    return
  }

  layoutCanvas(canvas)
  console.log(`[Live2D App] canvas buffer: ${canvas.width}x${canvas.height}`)

  app = new PIXI.Application({
    view: canvas,
    width: canvas.width,
    height: canvas.height,
    antialias: true,
    backgroundColor: 0x111122,
    backgroundAlpha: 0.1,
  })

  await ensureLive2dCoreLoaded()
  console.log('[Live2D App] Cubism Core loaded, loading model...')

  try {
    const rawModel = await Live2DModel.from(MODEL_SOURCE)

    rawModel.autoInteract = false
    app.stage.addChild(rawModel)

    // 必须在 stage 上才能读到正确的像素尺寸
    nativeWidth = rawModel.width > 5000 ? rawModel.internalModel.width : rawModel.width
    nativeHeight = rawModel.height > 5000 ? rawModel.internalModel.height : rawModel.height

    relayoutModel(rawModel, canvas)

    console.log('[Live2D App] Model loaded:', nativeWidth, 'x', nativeHeight, 'scale:', rawModel.scale.x, 'children:', app.stage.children.length)

    try {
      // Load expressions from .exp3.json files in model directory
      const expFiles = ['11.exp3.json', '22.exp3.json']
      const expressions: any[] = []
      for (const f of expFiles) {
        try {
          const r = await fetch(`miya-char://弥娅/Miya/${f}`)
          if (r.ok) {
            const d = await r.json()
            expressions.push(d)
          }
        }
        catch { /* skip */ }
      }
      await initStandaloneController(rawModel, null, expressions)
    }
    catch {
      console.warn('[Live2D App] actions/expressions not available')
      await initStandaloneController(rawModel, null, [])
    }

    startIPCListener()
    startYinmeiPolling()
    notifyLive2dReady()
    console.log('[Live2D App] Ready!')
  }
  catch (err) {
    console.error('[Live2D App] Model load failed:', err)
  }
}

function getControl() {
  const w = window as unknown as {
    __live2dControl?: {
      setEmotion(e: string): void
      setState(s: string): void
      setMouth(p: Record<string, number>): void
      triggerAction(a: string): void
      setTracking(e: boolean): void
    }
  }
  return w.__live2dControl ?? null
}

function startIPCListener(): void {
  const ctrl = getControl()
  if (!ctrl) return
  const ipc = (window as unknown as {
    live2dIPC?: { on: (ch: string, h: (...args: unknown[]) => void) => void }
  }).live2dIPC
  if (!ipc) return

  ipc.on('live2d:emotion', (emotion: string) => ctrl.setEmotion(emotion))
  ipc.on('live2d:state', (state: string) => ctrl.setState(state))
  ipc.on('live2d:mouth', (params: Record<string, number>) => ctrl.setMouth(params))
  ipc.on('live2d:action', (action: string) => ctrl.triggerAction(action))
  ipc.on('live2d:tracking', (enabled: boolean) => ctrl.setTracking(enabled))
  ipc.on('live2d:background', (data: { color: string, alpha: number }) => {
    if (app && app.renderer) {
      app.renderer.backgroundColor = parseInt(String(data.color), 16)
      app.renderer.backgroundAlpha = data.alpha
    }
  })
  console.log('[Live2D App] IPC listener started')
}

function notifyLive2dReady(): void {
  try {
    const ipc = (window as unknown as {
      live2dIPC?: { send: (ch: string, ...args: unknown[]) => void }
    }).live2dIPC
    if (ipc) ipc.send('live2d:ready')
  }
  catch { /* ignore */ }
}

let _yinmeiPollTimer: ReturnType<typeof setInterval> | null = null
let _yinmeiFailCount = 0
const YINMEI_MAX_FAILS = 20
const YINMEI_INTERVAL = 5000  // 每 5 秒轮询一次

function startYinmeiPolling(): void {
  const apiPort = (window as any).__MIYA_API_PORT__ || 9800
  const pollUrl = `http://127.0.0.1:${apiPort}/api/yinmei/live2d/commands`

  _yinmeiPollTimer = setInterval(async () => {
    try {
      const resp = await fetch(pollUrl)
      if (!resp.ok) {
        _yinmeiFailCount++
        if (_yinmeiFailCount >= YINMEI_MAX_FAILS && _yinmeiPollTimer) {
          clearInterval(_yinmeiPollTimer)
          _yinmeiPollTimer = null
          console.log('[Live2D] Yinmei polling stopped after', _yinmeiFailCount, 'failures')
        }
        return
      }
      _yinmeiFailCount = 0  // 成功后重置
      const data = await resp.json()
      const cmds = data.commands || []
      if (cmds.length === 0) return

      const ctrl = getControl()
      if (!ctrl) return

      for (const cmd of cmds) {
        switch (cmd.type) {
          case 'emotion': ctrl.setEmotion(cmd.value); break
          case 'state': ctrl.setState(cmd.value); break
          case 'mouth': ctrl.setMouth(cmd.value); break
          case 'action': ctrl.triggerAction(cmd.value); break
        }
      }
    }
    catch {
      _yinmeiFailCount++
      if (_yinmeiFailCount >= YINMEI_MAX_FAILS && _yinmeiPollTimer) {
        clearInterval(_yinmeiPollTimer)
        _yinmeiPollTimer = null
        console.log('[Live2D] Yinmei polling stopped (backend unreachable)')
      }
    }
  }, YINMEI_INTERVAL)

  console.log('[Live2D App] Yinmei polling started:', pollUrl)
}

window.addEventListener('beforeunload', () => {
  if (_yinmeiPollTimer) {
    clearInterval(_yinmeiPollTimer)
    _yinmeiPollTimer = null
  }
  destroyStandaloneController()
  if (app) app.destroy(true, { children: true })
})

boot().catch(err => console.error('[Live2D App] Boot failed:', err))
