import type { Message } from '@/utils/session'
import { ref } from 'vue'
import { MESSAGES } from '@/utils/session'

const wsUrl = 'ws://localhost:9800/api/v1/ws'
const connected = ref(false)
const reconnecting = ref(false)
let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

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
    // 新消息事件
    if (data.type === 'new_message' || data.type === 'message') {
      const msg = data.data || data
      const content = msg.content || msg.text || msg.message || ''
      const sender = msg.sender_name || msg.sender || msg.platform || '未知'
      const platform = msg.platform || ''
      const role = platform === 'desktop' ? 'user' : 'system'

      // 避免重复（简单去重：检查最后一条消息内容）
      const lastMsg = MESSAGES.value[MESSAGES.value.length - 1]
      if (lastMsg?.content === content && lastMsg?.role === role) return

      const newMsg: Message = {
        role: role as 'system' | 'user',
        content: `[${sender}] ${content}`,
        sender: sender,
      }
      MESSAGES.value.push(newMsg)
    }
  }

  function disconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws?.close()
    ws = null
  }

  return { connected, reconnecting, connect, disconnect }
}
