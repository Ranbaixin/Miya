import type { Live2DModel } from 'pixi-live2d-display/cubism4'
import * as PIXI from 'pixi.js'

interface Keyframe {
  t: number
  params: Record<string, number>
}

interface StateConfig {
  loop: boolean
  duration?: number
  keyframes?: Keyframe[]
  params?: Record<string, number>
}

interface ActionConfig {
  duration: number
  repeat: number
  keyframes: Keyframe[]
}

interface ActionsData {
  states: Record<string, StateConfig>
  actions: Record<string, ActionConfig>
  _states?: Record<string, StateConfig>
  _actions?: Record<string, ActionConfig>
}

interface Exp3Param {
  Id: string
  Value: number
  Blend: 'Add' | 'Multiply' | 'Overwrite'
}

interface ExpressionDef {
  name: string
  fadeInTime: number
  params: Exp3Param[]
}

type Live2dState = 'idle' | 'thinking' | 'talking'

// ─── 内部状态 ────────────────────────────────────────
let model: Live2DModel | null = null
let actionsData: ActionsData | null = null
let stateStartTime = 0
let currentStateName: Live2dState = 'idle'
let lastTickTime = 0

let mouthParams: Record<string, number> = {}
let targetMouthParams: Record<string, number> = {}

// ─── 暴露给 IPC ──────────────────────────────────────

const live2dControl = {
  setEmotion(emo: string) {
    if (model) applyEmotion(model, emo)
  },
  setState(state: Live2dState) {
    currentStateName = state
    stateStartTime = performance.now()
    if (model && actionsData?._states?.[state]) {
      applyState(model, actionsData._states[state])
    }
  },
  setMouth(params: Record<string, number>) {
    targetMouthParams = { ...params }
  },
  triggerAction(action: string) {
    if (model && actionsData?._actions?.[action]) {
      applySequenceAction(model, actionsData._actions[action])
    }
  },
  setTracking(_enabled: boolean) {},
}

;(window as unknown as { __live2dControl: typeof live2dControl }).__live2dControl = live2dControl

// ─── 初始化 ──────────────────────────────────────────

export async function initStandaloneController(
  rawModel: Live2DModel,
  _actionsData: ActionsData | null,
  expressions: ExpressionDef[],
): Promise<void> {
  model = rawModel
  actionsData = _actionsData

  if (actionsData) {
    actionsData._states = {}
    actionsData._actions = {}
    for (const key of Object.keys(actionsData.states)) {
      const v = actionsData.states[key]
      if (typeof v === 'object' && !Array.isArray(v)) {
        actionsData._states[key] = v as unknown as StateConfig
      }
    }
    for (const key of Object.keys(actionsData.actions)) {
      const v = actionsData.actions[key]
      if (typeof v === 'object' && !Array.isArray(v)) {
        actionsData._actions[key] = v as unknown as ActionConfig
      }
    }
  }

  // 不 hijack model.update —— pixi-live2d-display 内部 ticker 直接调 internalModel.update
  // 我们通过 PIXI.Ticker.shared 注册自己的帧逻辑
  PIXI.Ticker.shared.add(tickStandalone)

  stateStartTime = performance.now()
  if (actionsData?._states?.idle) {
    applyState(model, actionsData._states.idle)
  }

  console.log('[Live2D Standalone] 控制器初始化完成, ticker registered, expressions:', expressions.length)
}

export function destroyStandaloneController(): void {
  PIXI.Ticker.shared.remove(tickStandalone)
  model = null
  actionsData = null
}

// ─── 每帧 tick ───────────────────────────────────────

function tickStandalone(_dt: number): void {
  if (!model) return
  const now = performance.now()
  lastTickTime = now

  // 口型平滑
  if (Object.keys(targetMouthParams).length > 0) {
    for (const [key, target] of Object.entries(targetMouthParams)) {
      const current = mouthParams[key] ?? 0
      mouthParams[key] = lerp(current, target, 0.3)
    }
    applyMouthParams(model, mouthParams)
  }

  // 状态 keyframe 推进
  if (actionsData?._states?.[currentStateName]) {
    advanceStateKeyframes(model, actionsData._states[currentStateName])
  }
}

function applyMouthParams(m: Live2DModel, params: Record<string, number>): void {
  for (const [key, val] of Object.entries(params)) {
    try { m.internalModel.coreModel.setParameterValueById(key, val) } catch {}
  }
}

function applyState(m: Live2DModel, cfg: StateConfig): void {
  if (cfg.params) {
    for (const [key, val] of Object.entries(cfg.params)) {
      try { m.internalModel.coreModel.setParameterValueById(key, val) } catch {}
    }
  }
}

function advanceStateKeyframes(m: Live2DModel, cfg: StateConfig): void {
  if (!cfg.keyframes || cfg.keyframes.length === 0) return

  const elapsed = (performance.now() - stateStartTime) / 1000
  const totalDuration = cfg.keyframes[cfg.keyframes.length - 1].t

  let t: number
  if (cfg.loop) {
    t = elapsed % totalDuration
  }
  else {
    t = Math.min(elapsed, totalDuration)
  }

  let kfA = cfg.keyframes[0]
  let kfB = cfg.keyframes[0]
  for (let i = 0; i < cfg.keyframes.length - 1; i++) {
    if (t >= cfg.keyframes[i].t && t <= cfg.keyframes[i + 1].t) {
      kfA = cfg.keyframes[i]
      kfB = cfg.keyframes[i + 1]
      break
    }
  }

  const seg = kfB.t - kfA.t
  const localT = seg > 0 ? (t - kfA.t) / seg : 0

  for (const key of Object.keys(kfA.params)) {
    const a = kfA.params[key] ?? 0
    const b = kfB.params[key] ?? a
    const val = lerp(a, b, localT)
    try { m.internalModel.coreModel.setParameterValueById(key, val) } catch {}
  }
}

function applySequenceAction(m: Live2DModel, cfg: ActionConfig): void {
  let elapsed = 0
  const perFrame = 16

  const tick = () => {
    elapsed += perFrame / 1000
    const totalDuration = cfg.keyframes[cfg.keyframes.length - 1].t * cfg.repeat
    if (elapsed >= totalDuration) return

    const t = (elapsed % cfg.keyframes[cfg.keyframes.length - 1].t)
    let kfA = cfg.keyframes[0]
    let kfB = cfg.keyframes[0]
    for (let i = 0; i < cfg.keyframes.length - 1; i++) {
      if (t >= cfg.keyframes[i].t && t <= cfg.keyframes[i + 1].t) {
        kfA = cfg.keyframes[i]
        kfB = cfg.keyframes[i + 1]
        break
      }
    }
    const seg = kfB.t - kfA.t
    const localT = seg > 0 ? (t - kfA.t) / seg : 0

    for (const key of Object.keys(kfA.params)) {
      const a = kfA.params[key] ?? 0
      const b = kfB.params[key] ?? a
      const val = lerp(a, b, localT)
      try { m.internalModel.coreModel.setParameterValueById(key, val) } catch {}
    }
    requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

function applyEmotion(m: Live2DModel, emotion: string): void {
  const emotionParams: Record<string, Record<string, number>> = {
    happy: { ParamMouthOpenY: 0.3, ParamEyeLOpen: 0.9, ParamEyeROpen: 0.9 },
    sad: { ParamMouthOpenY: -0.2, ParamEyeLOpen: 0.5, ParamEyeROpen: 0.5, ParamBrowLY: -0.5, ParamBrowRY: -0.5 },
    angry: { ParamBrowLY: -0.8, ParamBrowRY: -0.8, ParamEyeLOpen: 0.7, ParamEyeROpen: 0.7 },
    surprise: { ParamMouthOpenY: 0.5, ParamEyeLOpen: 1.0, ParamEyeROpen: 1.0, ParamBrowLY: 0.5, ParamBrowRY: 0.5 },
    neutral: { ParamMouthOpenY: 0, ParamEyeLOpen: 0.8, ParamEyeROpen: 0.8, ParamBrowLY: 0, ParamBrowRY: 0 },
  }

  const params = emotionParams[emotion] || emotionParams.neutral
  for (const [key, val] of Object.entries(params)) {
    try { m.internalModel.coreModel.setParameterValueById(key, val) } catch {}
  }
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * Math.max(0, Math.min(1, t))
}
