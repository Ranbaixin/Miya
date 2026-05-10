import { ref, watch } from 'vue'
import API from '@/api/core'
import { backendConnected } from '@/utils/config'
import { preloadAllViews } from '@/utils/viewPreloader'

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T | undefined> {
  return Promise.race([
    promise,
    new Promise<undefined>(resolve => setTimeout(() => resolve(undefined), ms)),
  ])
}

export function useStartupProgress() {
  const progress = ref(0)
  const phase = ref<string>('初始化...')
  const isReady = ref(false)
  const stallHint = ref(false)

  let targetProgress = 0
  let rafId = 0

  function animateProgress() {
    const diff = targetProgress - progress.value
    if (diff > 0.5) {
      progress.value = Math.min(progress.value + Math.max(diff * 0.12, 0.5), targetProgress)
    } else if (diff > 0) {
      progress.value = targetProgress
    }
    if (progress.value >= 100) {
      progress.value = 100
      isReady.value = true
    }
    if (!isReady.value || progress.value < 100) {
      rafId = requestAnimationFrame(animateProgress)
    }
  }

  function setTarget(value: number, p: string) {
    if (value > targetProgress) {
      targetProgress = value
      phase.value = p
    }
  }

  function notifyModelReady() {
    setTarget(30, '加载完成...')
  }

  async function startProgress() {
    setTarget(5, '启动中...')
    rafId = requestAnimationFrame(animateProgress)

    // 后端进程监听
    const api = window.electronAPI
    if (api?.backend) {
      api.backend.onProgress((payload: any) => {
        const mapped = 10 + (payload.percent / 50) * 40
        setTarget(Math.min(mapped, 50), payload.phase)
      })
    }

    if (backendConnected.value) {
      setTarget(60, '已连接')
      try {
        await withTimeout(API.getSessions(), 3000)
      } catch {}
      setTarget(100, '就绪')
      return
    }

    // 等后端连接
    const stop = watch(backendConnected, (connected) => {
      if (!connected) return
      stop()
      setTarget(60, '已连接')
      preloadAllViews().catch(() => {})
      withTimeout(API.getSessions(), 3000).finally(() => {
        setTarget(100, '就绪')
      })
    })

    // 3 秒后直接跳过
    setTimeout(() => {
      if (targetProgress >= 50) return
      stop()
      setTarget(100, '离线就绪')
    }, 3000)
  }

  function cleanup() {
    if (rafId) cancelAnimationFrame(rafId)
  }

  return { progress, phase, isReady, stallHint, startProgress, notifyModelReady, cleanup }
}
