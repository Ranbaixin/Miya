import type { StreamChunk } from '@/utils/encoding'
import { useStorage } from '@vueuse/core'
import { ref } from 'vue'
import API from '@/api/core'

export const proactiveNotifier = ref<null | ((source: string, content: string) => void)>(null)

export interface Message {
  role: 'system' | 'user' | 'assistant' | 'info'
  content: string
  reasoning?: string
  generating?: boolean
  status?: string
  sender?: string
  toolEvents?: ToolEvent[]
  soulData?: SoulData
}

export interface SoulData {
  emotions?: Array<{ name: string, intensity: number }>
  innerThought?: string
  attribution?: string
  reflection?: string
  thinking?: string
}

export interface ToolEvent {
  type: 'tool_call' | 'tool_result'
  name?: string
  toolCallId?: string
  args?: any
  result?: any
  isError?: boolean
}

// ── Tab 状态管理 ──

export interface ChatTab {
  id: string
  name: string
  messages: Message[]
  unread: number
}

export const tabs = ref<ChatTab[]>([
  { id: 'default', name: '弥娅', messages: [], unread: 0 },
])

// 全局最新情绪（跨组件共享）
export const latestEmotion = ref<SoulData>({ emotions: [] })

export const activeTabId = useStorage('miya-active-tab', 'default')

export function getActiveTab(): ChatTab {
  return tabs.value.find(t => t.id === activeTabId.value) || tabs.value[0]!
}

export function getDefaultTab(): ChatTab {
  return tabs.value[0]!
}

export function appendDefaultMessage(message: Message) {
  MESSAGES.value.push(message)
  syncDefaultMessages()
}

export async function reloadCurrentSessionMessages() {
  if (!CURRENT_SESSION_ID.value)
    return
  const detail = await API.getSessionDetail(CURRENT_SESSION_ID.value)
  MESSAGES.value = normalizeMessages(detail.messages)
  syncDefaultMessages()
}

function normalizeToolEvent(input: any): ToolEvent | null {
  if (!input || typeof input !== 'object')
    return null
  const type = input.type === 'tool_result' ? 'tool_result' : input.type === 'tool_call' ? 'tool_call' : null
  if (!type)
    return null
  return {
    type,
    name: typeof input.name === 'string' ? input.name : undefined,
    toolCallId: typeof input.toolCallId === 'string'
      ? input.toolCallId
      : typeof input.tool_call_id === 'string'
        ? input.tool_call_id
        : undefined,
    args: input.args,
    result: input.result,
    isError: Boolean(input.isError ?? input.is_error),
  }
}

function extractStructuredToolBlocks(content: string): { content: string, toolEvents: ToolEvent[] } {
  if (!content.includes('```tool-'))
    return { content, toolEvents: [] }

  const toolEvents: ToolEvent[] = []
  let remaining = content
  let cleaned = ''

  while (remaining.length > 0) {
    const startCall = remaining.indexOf('```tool-call')
    const startResult = remaining.indexOf('```tool-result')
    const start = startCall === -1
      ? startResult
      : startResult === -1
        ? startCall
        : Math.min(startCall, startResult)
    if (start === -1) {
      cleaned += remaining
      break
    }

    cleaned += remaining.slice(0, start)
    const isToolCall = remaining.startsWith('```tool-call', start)
    const afterHeader = remaining.indexOf('\n', start)
    if (afterHeader === -1) {
      cleaned += remaining.slice(start)
      break
    }

    const end = remaining.indexOf('```', afterHeader + 1)
    if (end === -1) {
      cleaned += remaining.slice(start)
      break
    }

    const block = remaining.slice(afterHeader + 1, end).trim()
    if (block) {
      const lines = block.split('\n')
      const summary = (lines[0] || '').trim()
      const body = lines.slice(1).join('\n').trim()
      const isError = summary.startsWith('❌ ')
      const isSuccess = summary.startsWith('✅ ')
      const name = (isError || isSuccess) ? summary.slice(2).trim() : summary
      toolEvents.push({
        type: isToolCall ? 'tool_call' : 'tool_result',
        name: name || '工具',
        isError: isToolCall ? undefined : isError,
        args: isToolCall ? body : undefined,
        result: isToolCall ? undefined : body,
      })
    }

    remaining = remaining.slice(end + 3)
  }

  return {
    content: cleaned.replace(/\n{3,}/g, '\n\n').trim(),
    toolEvents,
  }
}

function buildMessageQueueKey(role: Message['role'], content: string): string {
  return `${role}\u0000${extractStructuredToolBlocks(content).content}`
}

function normalizeMessage(input: any, assistantName?: string): Message | null {
  if (!input || typeof input !== 'object')
    return null

  const role = input.role
  if (role !== 'system' && role !== 'user' && role !== 'assistant' && role !== 'info')
    return null

  const initialContent = typeof input.content === 'string' ? input.content : ''
  const extracted = extractStructuredToolBlocks(initialContent)
  const rawEvents = Array.isArray(input.toolEvents)
    ? input.toolEvents
    : Array.isArray(input.tool_events)
      ? input.tool_events
      : []
  const toolEvents = [
    ...((rawEvents.map(normalizeToolEvent).filter(Boolean)) as ToolEvent[]),
    ...extracted.toolEvents,
  ]

  return {
    role,
    content: extracted.content,
    reasoning: typeof input.reasoning === 'string' ? input.reasoning : undefined,
    generating: Boolean(input.generating),
    status: typeof input.status === 'string' ? input.status : undefined,
    sender: typeof input.sender === 'string' ? input.sender : role === 'assistant' ? assistantName : undefined,
    toolEvents: toolEvents.length ? toolEvents : undefined,
  }
}

function mergeAssistantMessages(base: Message, extra: Message) {
  if (extra.content) {
    base.content = base.content
      ? `${base.content}\n\n${extra.content}`.trim()
      : extra.content
  }
  if (extra.reasoning) {
    base.reasoning = base.reasoning
      ? `${base.reasoning}\n\n${extra.reasoning}`.trim()
      : extra.reasoning
  }
  if (extra.toolEvents?.length) {
    base.toolEvents = [...(base.toolEvents || []), ...extra.toolEvents]
  }
  if (!base.status && extra.status)
    base.status = extra.status
  if (!base.sender && extra.sender)
    base.sender = extra.sender
  base.generating = base.generating || extra.generating
}

export function normalizeMessages(messages: unknown, assistantName?: string): Message[] {
  if (!Array.isArray(messages))
    return []

  const normalized: Message[] = []
  for (const item of messages) {
    const message = normalizeMessage(item, assistantName)
    if (!message)
      continue

    const previous = normalized[normalized.length - 1]
    if (message.role === 'assistant' && previous?.role === 'assistant') {
      mergeAssistantMessages(previous, message)
      continue
    }
    normalized.push(message)
  }
  return normalized
}

// ── 默认 tab 会话管理 ──

export const CURRENT_SESSION_ID = useStorage<string | null>('miya-session', null)
export const MESSAGES = ref<Message[]>([])
export const IS_TEMPORARY_SESSION = ref(false)

tabs.value[0]!.messages = MESSAGES.value

function syncDefaultMessages() {
  tabs.value[0]!.messages = MESSAGES.value
}

export async function loadCurrentSession() {
  if (CURRENT_SESSION_ID.value) {
    try {
      const detail = await API.getSessionDetail(CURRENT_SESSION_ID.value)
      MESSAGES.value = normalizeMessages(detail.messages)
      syncDefaultMessages()
      return
    }
    catch {
      CURRENT_SESSION_ID.value = null
    }
  }
  MESSAGES.value = []
  syncDefaultMessages()
}

export function newSession() {
  CURRENT_SESSION_ID.value = null
  MESSAGES.value = []
  syncDefaultMessages()
  IS_TEMPORARY_SESSION.value = false
}

export function newTemporarySession() {
  CURRENT_SESSION_ID.value = null
  MESSAGES.value = []
  syncDefaultMessages()
  IS_TEMPORARY_SESSION.value = true
}

export async function switchSession(id: string) {
  CURRENT_SESSION_ID.value = id
  IS_TEMPORARY_SESSION.value = false
  await loadCurrentSession()
}

export function formatRelativeTime(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1)
    return '刚刚'
  if (diffMin < 60)
    return `${diffMin}分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24)
    return `${diffHour}小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 7)
    return `${diffDay}天前`
  return d.toLocaleDateString()
}

declare global {
  interface WindowEventMap {
    token: CustomEvent<StreamChunk>
  }
}
