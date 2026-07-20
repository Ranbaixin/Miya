import type { Message } from '@/utils/session'
import type { PlatformInfo } from '@/utils/platform'
import { ref } from 'vue'
import { MESSAGES } from '@/utils/session'
import { getPlatformLabel } from '@/utils/platform'

const wsUrl = 'ws://localhost:9800/api/v1/ws'
const connected = ref(false)
const reconnecting = ref(false)
const platforms = ref<PlatformInfo[]>([])
const lastPlatformStatus = ref<Record<string, string>>({})
let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

export interface PlatformChangeEvent {
  platformId: string
  platformName: string
  oldStatus: string
  newStatus: string
}

const onPlatformChange = ref<((event: PlatformChangeEvent) => void) | null>(null)

export function useMIYARealtime() {
  function connect() {
    if (ws?.readyState === WebSocket.OPEN) return

    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      connected.value = true
      reconnecting.value = false
      console.log('[MIYA WS] 已连接')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleMessage(data)
      } catch {}
    }

    ws.onclose = () => {
      connected.value = false
      if (!reconnecting.value) {
        reconnecting.value = true
        reconnectTimer = setTimeout(() => {
          reconnecting.value = false
          connect()
        }, 3000)
      }
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function handleMessage(data: any) {
    if (data.type === 'initial_state' || data.type === 'status_update') {
      handlePlatformList(data.platforms || data)
    }

    if (data.type === 'platform_event') {
      handlePlatformEvent(data)
    }

    if (data.type === 'new_message' || data.type === 'message') {
      handleNewMessage(data)
    }
  }

  function handlePlatformList(plats: PlatformInfo[] | any) {
    const list = Array.isArray(plats)
      ? plats
      : Array.isArray(plats?.platforms) ? plats.platforms : []

    if (!list.length) return

    for (const p of list) {
      const old = lastPlatformStatus.value[p.platform_id]
      const cur = p.status
      if (old && old !== cur && onPlatformChange.value) {
        onPlatformChange.value({
          platformId: p.platform_id,
          platformName: p.platform_name || p.platform_id,
          oldStatus: old,
          newStatus: cur,
        })
      }
    }

    for (const p of list) {
      lastPlatformStatus.value[p.platform_id] = p.status
    }

    platforms.value = list
      .filter(p => p.status !== 'disabled')
      .sort((a, b) => a.platform_name.localeCompare(b.platform_name))
  }

  function handlePlatformEvent(data: any) {
    const pid = data.platform_id
    const status = data.status
    const old = lastPlatformStatus.value[pid]
    if (old && old !== status && onPlatformChange.value) {
      onPlatformChange.value({
        platformId: pid,
        platformName: data.platform_name || pid,
        oldStatus: old,
        newStatus: status,
      })
    }
    lastPlatformStatus.value[pid] = status

    if (data.health) {
      const idx = platforms.value.findIndex(p => p.platform_id === pid)
      if (idx >= 0) {
        platforms.value[idx] = {
          ...platforms.value[idx],
          status: status || platforms.value[idx].status,
          latency_ms: data.health.latency_ms ?? platforms.value[idx].latency_ms,
          last_heartbeat: data.health.last_heartbeat ?? platforms.value[idx].last_heartbeat,
          consecutive_health_failures: data.health.consecutive_health_failures ?? platforms.value[idx].consecutive_health_failures,
          message_count: data.health.message_count ?? platforms.value[idx].message_count,
        }
      }
    }
  }

  function handleNewMessage(data: any) {
    const msg = data.data || data
    const content = msg.content || msg.text || msg.message || ''
    const sender = msg.sender_name || msg.sender || msg.platform || '未知'
    const platform = msg.platform || data.platform || ''
    const platformName = getPlatformLabel(platform)
    const direction = msg.direction || (platform === 'desktop' ? 'in' : 'in')
    const messageId = msg.message_id || msg.msg_id || undefined
    const timestamp = msg.timestamp || msg.time || null
    const role = platform === 'desktop' ? 'user' : 'system'

    const existing = MESSAGES.value[MESSAGES.value.length - 1]
    if (existing
      && existing.content === content
      && existing.role === role
      && existing.platform === platform) return

    const newMsg: Message = {
      role: role as 'system' | 'user',
      content: content,
      sender,
      platform,
      platformName: platformName !== platform ? platformName : msg.platform_name,
      messageId,
      direction,
      timestamp,
    }
    MESSAGES.value.push(newMsg)
  }

  function setOnPlatformChange(fn: (event: PlatformChangeEvent) => void) {
    onPlatformChange.value = fn
  }

  function disconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws?.close()
    ws = null
  }

  return { connected, reconnecting, platforms, connect, disconnect, setOnPlatformChange, lastPlatformStatus }
}
