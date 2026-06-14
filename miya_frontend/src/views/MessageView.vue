<script lang="ts">
import type { ChatTab, Message } from '@/utils/session'
import { useEventListener } from '@vueuse/core'
import Dialog from 'primevue/dialog'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import API from '@/api/core'
import BoxContainer from '@/components/BoxContainer.vue'
import Markdown from '@/components/Markdown.vue'
import MessageItem from '@/components/MessageItem.vue'
import { CONFIG } from '@/utils/config'
import { proxySetSoulEmotion, proxySetState } from '@/utils/live2dProxy'
import { activeTabId, CURRENT_SESSION_ID, formatRelativeTime, getActiveTab, IS_TEMPORARY_SESSION, latestEmotion, loadCurrentSession, MESSAGES, newSession, saveMessages, switchSession, tabs } from '@/utils/session'
import { clearSpeakQueue, isPlaying, queueSpeak, stop as stopTTS } from '@/utils/tts'
import { setMessageViewExpanded } from '@/utils/uiState'

const isSending = ref(false)
const messageQueue: Array<{ content: string, options?: any }> = []
const ttsEnabled = ref(localStorage.getItem('ttsEnabled') !== 'false')
let lastAppliedMemoryHash = ''

async function processQueue() {
  if (messageQueue.length === 0 || isSending.value)
    return

  const { content, options } = messageQueue.shift()!
  await chatStreamInternal(content, options)
}

export function chatStream(content: string, options?: { skill?: string, images?: string[], voiceInput?: boolean }) {
  stopTTS()

  MESSAGES.value.push({ role: 'user', content: options?.images?.length ? `[截图x${options.images.length}] ${content}` : content })
  saveMessages()

  messageQueue.push({ content, options })
  processQueue()
}

function applySoulToMessage(soul: any) {
  const msgs = MESSAGES.value
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i]!.role === 'assistant') {
      const existing = (msgs[i]! as any).soulData || {}
      if (soul.emotions && Array.isArray(soul.emotions)) {
        existing.emotions = soul.emotions
      } else if (soul.emotions && typeof soul.emotions === 'object') {
        existing.emotions = Object.entries(soul.emotions).map(([name, val]: any) => ({ name, intensity: typeof val === 'number' ? Math.round(val) : 50 }))
      }
      if (!existing.innerThought && soul.inner_thought) existing.innerThought = soul.inner_thought
      if (!existing.attribution && soul.attribution) existing.attribution = soul.attribution
      if (!existing.reflection && soul.reflection) existing.reflection = soul.reflection
      if (!existing.thinking && soul.thinking) existing.thinking = soul.thinking
      ;(msgs[i]! as any).soulData = existing
      if (existing.emotions?.length) latestEmotion.value = { ...latestEmotion.value, emotions: existing.emotions }
      break
    }
  }
}

async function fetchSoulData(retryCount = 0) {
  try {
    // 优先：直连后端灵魂数据（_last_soul_output）
    const soulRes = await fetch('http://localhost:9800/api/soul/current')
    const directSoul = await soulRes.json()
    if (directSoul && (directSoul.emotions || directSoul.inner_thought || directSoul.thinking)) {
      applySoulToMessage(directSoul)
      return
    }

    // Fallback: 认知记忆文件
    const res = await fetch('http://localhost:9800/api/desktop/files/read?path=data%2Fmemory%2Fcognitive_memories.json')
    const data = await res.json()
    if (data?.lines) {
      const items = JSON.parse(data.lines.join(''))
      if (!Array.isArray(items) || items.length === 0) {
        if (retryCount < 2) { setTimeout(() => fetchSoulData(retryCount + 1), 1500) }
        return
      }

      const memoryHash = JSON.stringify(items[items.length - 1])
      if (memoryHash === lastAppliedMemoryHash) {
        if (retryCount < 2) { setTimeout(() => fetchSoulData(retryCount + 1), 1500) }
        return
      }
      lastAppliedMemoryHash = memoryHash

      const merged: any = {}
      for (let i = items.length - 1; i >= Math.max(0, items.length - 5); i--) {
        const entry = items[i]
        if (!entry || String(entry.user_id) !== '1523878699') continue
        let emo = entry.emotions
        if (typeof emo === 'string') { try { emo = eval(`(${emo})`) } catch { emo = null } }
        if (!merged.emotions && emo && typeof emo === 'object') {
          merged.emotions = Object.entries(emo).map(([name, val]: any) => ({ name, intensity: val as number }))
        }
        if (!merged.innerThought && entry.inner_thought) merged.innerThought = entry.inner_thought
        if (!merged.attribution && entry.attribution) merged.attribution = entry.attribution
        if (!merged.reflection && entry.reflection) merged.reflection = entry.reflection
        if (!merged.thinking && entry.thinking) merged.thinking = entry.thinking
      }
      if (merged.emotions) merged.emotions = merged.emotions.slice(0, 6)

      if (!merged.emotions?.length && !merged.innerThought && retryCount < 2) {
        setTimeout(() => fetchSoulData(retryCount + 1), 1500)
        return
      }

      applySoulToMessage(merged)
    } else if (retryCount < 2) {
      setTimeout(() => fetchSoulData(retryCount + 1), 1500)
    }
  } catch {}
}

async function chatStreamInternal(content: string, options?: { skill?: string, images?: string[], voiceInput?: boolean }) {
  isSending.value = true

  MESSAGES.value.push({ role: 'assistant', content: '', reasoning: '', generating: true, status: options?.voiceInput ? '理解话语中' : undefined })
  const message = MESSAGES.value[MESSAGES.value.length - 1]!

  let spokenContent = ''

  const voiceSync = CONFIG.value.system.voice_enabled
  let contentBuf = ''
  const pushContent = (text: string) => {
    contentBuf += text
    message.content = contentBuf
    // 每次内容更新保存到 localStorage
    try {
      localStorage.setItem('miya-messages', JSON.stringify(MESSAGES.value.slice(-200)))
    } catch {}
  }

  proxySetState('thinking')
  let compressTimer: ReturnType<typeof setTimeout> | undefined
  let ttsSentenceBuf = ''

  let roundContentStart = 0

  return API.chatSend({
    message: content,
    session_id: CURRENT_SESSION_ID.value ?? 'default',
    platform: 'desktop',
    user_id: CONFIG.value.ui?.owner_id || '1523878699',
    usg_id: CONFIG.value.ui?.desktop_usg_id || 'desktop_user',
  }).then((res: any) => {
    // 解析响应 (可能是 SSE 或 JSON)
    let responseText = ''
    const soulRaw: any = {}
    if (typeof res === 'string' && res.startsWith('data:')) {
      // SSE 格式 - 弥娅后端返回: data: {"type":"plain","data":"...","chain_type":"final"}
      const lines = res.split('\n')
      for (const line of lines) {
        const dataPrefix = 'data: '
        if (!line.startsWith(dataPrefix)) continue
        const jsonStr = line.slice(dataPrefix.length).trim()
        if (!jsonStr || jsonStr === '[DONE]') continue
        try {
          const chunk = JSON.parse(jsonStr)
          if (chunk.type === 'plain' && chunk.data) {
            responseText = chunk.data
          } else if (chunk.type === 'reasoning') {
            message.reasoning = (message.reasoning || '') + (chunk.data || chunk.text || '')
          } else if (chunk.type === 'soul' && chunk.data) {
            Object.assign(soulRaw, chunk.data)
          } else if (chunk.type === 'done' && chunk.data?.response && !responseText) {
            responseText = chunk.data.response
          }
        } catch {}
      }
    } else {
      responseText = res?.response || res?.data?.response || JSON.stringify(res)
      // JSON 响应路径：直接提取 soul 数据
      if (res?.soul) {
        Object.assign(soulRaw, res.soul)
      }
    }

    pushContent(responseText || res?.response || JSON.stringify(res))
    message.generating = false
    message.status = undefined
    proxySetState('idle')

    // 存储灵魂数据到消息（仅来自 SSE 流每句专属数据）
    if (Object.keys(soulRaw).length > 0) {
      const soulData: any = {}
      if (soulRaw.emotions) {
        soulData.emotions = Object.entries(soulRaw.emotions).map(([name, val]: any) => ({
          name,
          intensity: typeof val === 'number' ? Math.round(val) : 50,
        }))
        latestEmotion.value = { emotions: soulData.emotions }
        proxySetSoulEmotion(soulData.emotions)
      }
      if (soulRaw.inner_thought) soulData.innerThought = soulRaw.inner_thought
      if (soulRaw.attribution) soulData.attribution = soulRaw.attribution
      if (soulRaw.reflection) soulData.reflection = soulRaw.reflection
      if (soulRaw.thinking) soulData.thinking = soulRaw.thinking
      ;(message as any).soulData = soulData
      saveMessages()
      // 异步从认知记忆补全灵魂数据（内心独白/归因/反思/思考/情绪）
      fetchSoulData()
    }

    // 滚动到底部
    nextTick(() => {
      const el = document.querySelector('.p-scrollpanel-content')
      if (el) el.scrollTop = el.scrollHeight
    })

    isSending.value = false
    saveMessages()
    processQueue()
  }).catch((err: any) => {
    message.content = `[连接失败: ${err?.message || '后端未响应'}]`
    message.generating = false
    isSending.value = false
    saveMessages()
    processQueue()
  })
}

</script>

<script setup lang="ts">
const input = defineModel<string>()
const normalContainerRef = ref(null)
const expandedContainerRef = ref(null)
const composerRef = ref<HTMLTextAreaElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const inputDockRef = ref<HTMLElement | null>(null)
const isExpanded = ref(false)
const expandedStyle = ref<Record<string, string>>({})
const expandedInputStyle = ref<Record<string, string>>({})
const expandedAnchorLeft = ref(8)

function isImeComposing(event: KeyboardEvent) {
  return event.isComposing || (event as any).keyCode === 229
}

function resizeComposer() {
  if (!composerRef.value) {
    return
  }
  composerRef.value.style.height = '0px'
  const nextHeight = Math.min(Math.max(composerRef.value.scrollHeight, 44), 160)
  composerRef.value.style.height = `${nextHeight}px`
}

function toggleExpanded() {
  if (!isExpanded.value) {
    const chatRect = (normalContainerRef.value as any)?.$el?.getBoundingClientRect?.()
    if (chatRect) {
      expandedAnchorLeft.value = Math.max(8, chatRect.left)
    }
  }
  isExpanded.value = !isExpanded.value
  nextTick(() => {
    resizeComposer()
    if (isExpanded.value) {
      updateExpandedLayout()
      nextTick().then(scrollToBottom)
    }
  })
}

function handleComposerEnter(event: KeyboardEvent) {
  if (isImeComposing(event) || event.shiftKey) {
    return
  }
  event.preventDefault()
  sendMessage()
}

function updateExpandedLayout() {
  if (!inputDockRef.value) {
    return
  }
  const chatRect = (normalContainerRef.value as any)?.$el?.getBoundingClientRect?.()
  const inputRect = inputDockRef.value.getBoundingClientRect()
  const left = isExpanded.value
    ? expandedAnchorLeft.value
    : Math.max(8, chatRect?.left ?? expandedAnchorLeft.value)
  const composerHeight = Math.max(56, Math.ceil(inputRect.height))
  expandedStyle.value = {
    left: `${left}px`,
    top: '8px',
    right: '8px',
    bottom: `${composerHeight + 16}px`,
  }
  expandedInputStyle.value = {
    left: `${left}px`,
    right: '8px',
    bottom: '8px',
  }
}

function toggleTTS() {
  ttsEnabled.value = !ttsEnabled.value
  localStorage.setItem('ttsEnabled', String(ttsEnabled.value))
  if (!ttsEnabled.value) {
    stopTTS()
  }
}

watch(isPlaying, (playing) => {
  proxySetState(playing ? 'talking' : 'idle')
})

watch(input, () => {
  nextTick(() => {
    resizeComposer()
    if (isExpanded.value) {
      updateExpandedLayout()
    }
  })
})

watch(isExpanded, (value) => {
  setMessageViewExpanded(value)
})

function scrollToBottom() {
  ;(normalContainerRef.value as any)?.scrollToBottom?.()
  ;(expandedContainerRef.value as any)?.scrollToBottom?.()
}

const activeMessages = computed(() => getActiveTab().messages)

function sendMessage() {
  if (!input.value?.trim())
    return
  chatStream(input.value)
  nextTick().then(scrollToBottom)
  input.value = ''
}

function pushSystemMessage(content: string): Message {
  const message: Message = { role: 'system', content }
  MESSAGES.value.push(message)
  nextTick().then(scrollToBottom)
  return message
}

function dispatchToActiveTab(content: string, options?: { skill?: string, images?: string[], voiceInput?: boolean }) {
  chatStream(content, options)
  nextTick().then(scrollToBottom)
}

onMounted(async () => {
  await loadCurrentSession()
  scrollToBottom()
  nextTick(resizeComposer)
})

onBeforeUnmount(() => {
  setMessageViewExpanded(false)
})

useEventListener('token', scrollToBottom)
useEventListener(window, 'resize', () => {
  if (isExpanded.value) {
    updateExpandedLayout()
  }
})

// Session history
const showHistory = ref(false)
const sessions = ref<Array<{
  sessionId: string
  createdAt: string
  lastActiveAt: string
  conversationRounds: number
  temporary: boolean
}>>([])
const loadingSessions = ref(false)

async function fetchSessions() {
  loadingSessions.value = true
  try {
    const res = await API.getSessions()
    sessions.value = res.sessions ?? []
  }
  catch {
    sessions.value = []
  }
  loadingSessions.value = false
}

function toggleHistory() {
  showHistory.value = !showHistory.value
  if (showHistory.value) {
    fetchSessions()
  }
}

async function handleSwitchSession(id: string) {
  await switchSession(id)
  showHistory.value = false
  nextTick().then(scrollToBottom)
}

async function handleDeleteSession(id: string) {
  try {
    await API.deleteSession(id)
    sessions.value = sessions.value.filter(s => s.sessionId !== id)
    if (CURRENT_SESSION_ID.value === id) {
      newSession()
    }
  }
  catch { /* ignore */ }
}

function handleNewSession() {
  newSession()
  showHistory.value = false
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file)
    return

  const ext = file.name.split('.').pop()?.toLowerCase()
  const parseable = ['docx', 'xlsx', 'txt', 'csv', 'md']

  if (ext && parseable.includes(ext)) {
    const msg = pushSystemMessage(`正在解析文件: ${file.name}...`)
    try {
      const result = await API.parseDocument(file)
      const truncNote = result.truncated ? '（内容过长，已截断）' : ''
      msg.content = `文件解析完成: ${file.name}${truncNote}`
      dispatchToActiveTab(`以下是文件「${file.name}」的内容：\n\n${result.content}\n\n请分析这个文件的内容。`)
    }
    catch (err: any) {
      msg.content = `文件解析失败: ${err?.response?.data?.detail || err.message}`
    }
  }
  else {
    const msg = pushSystemMessage(`正在上传文件: ${file.name}...`)
    try {
      const result = await API.uploadDocument(file)
      msg.content = `文件上传成功: ${file.name}`
      if (result.filePath) {
        dispatchToActiveTab(`请分析我刚上传的文件「${file.name}」，文件完整路径: ${result.filePath}`)
      }
    }
    catch (err: any) {
      msg.content = `文件上传失败: ${err.message}`
    }
  }
  target.value = ''
}

// ── 语音输入（MediaRecorder + ASR API） ──
const isRecording = ref(false)
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []

async function toggleVoiceInput() {
  if (!CONFIG.value.voice_realtime.enabled)
    return

  if (isRecording.value) {
    stopVoiceInput()
    return
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []
    mediaRecorder = new MediaRecorder(stream, { mimeType: getSupportedMimeType() })

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0)
        audioChunks.push(e.data)
    }

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      if (audioChunks.length === 0)
        return

      const audioBlob = new Blob(audioChunks, { type: mediaRecorder?.mimeType || 'audio/webm' })
      try {
        const { text } = await API.transcribeAudio(audioBlob, { language: 'zh' })
        if (text && typeof text === 'string' && text.trim()) {
          dispatchToActiveTab(`以下是用户的语音输入：【${text.trim()}】`, { voiceInput: true })
        }
      }
      catch (err: any) {
        const status = err?.response?.status
        if (status === 401) {
          pushSystemMessage('语音识别需要登录后使用')
        }
        else if (status === 402) {
          pushSystemMessage('余额不足，无法使用语音识别')
        }
        else {
          pushSystemMessage(`语音识别失败: ${err.message || err}`)
        }
      }
    }

    mediaRecorder.start()
    isRecording.value = true
  }
  catch (err: any) {
    if (err.name === 'NotAllowedError') {
      pushSystemMessage('麦克风权限被拒绝，请在系统设置中允许麦克风访问')
    }
    else {
      pushSystemMessage(`无法启动录音: ${err.message || err}`)
    }
  }
}

function stopVoiceInput() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  mediaRecorder = null
  isRecording.value = false
}

function getSupportedMimeType(): string {
  const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
  for (const t of types) {
    if (MediaRecorder.isTypeSupported(t))
      return t
  }
  return ''
}
</script>

<template>
  <div class="flex flex-col gap-8 relative">
    <div class="flex min-h-0 grow">
      <!-- 主内容区 -->
      <BoxContainer v-show="!isExpanded" ref="normalContainerRef" class="w-full grow">
        <template #header>
          <div class="message-header px-1 pt-3 pb-2">
            <div class="tab-row" />
            <div class="window-actions">
              <button
                v-if="!isExpanded"
                class="window-btn"
                title="放大对话窗口"
                @click="toggleExpanded"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M15 3h6v6" />
                  <path d="M9 21H3v-6" />
                  <path d="M21 3l-7 7" />
                  <path d="M3 21l7-7" />
                </svg>
              </button>
            </div>
          </div>
        </template>

        <div class="grid gap-4 pb-8">
          <MessageItem
            v-for="item, index in activeMessages" :key="index"
            :role="item.role" :content="item.content"
            :reasoning="item.reasoning" :sender="item.sender"
            :generating="item.generating" :status="item.status"
            :tool-events="item.toolEvents"
            :soul-data="item.soulData"
                :class="(item.generating && index === activeMessages.length - 1) || 'msg-sep'"
          />
        </div>
      </BoxContainer>

      <Teleport to="body">
        <div v-if="isExpanded" class="expanded-chat-overlay" :style="expandedStyle">
          <BoxContainer
            ref="expandedContainerRef"
            class="message-shell size-full"
            box-class="w-full h-full"
            :parallax="false"
            hide-back
          >
            <template #header>
              <div class="message-header px-1 pt-3 pb-2">
                <div class="tab-row" />
                <div class="window-actions">
                  <button
                    class="window-btn"
                    title="缩小对话窗口"
                    @click="toggleExpanded"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M14 10 21 3" />
                      <path d="M21 10V3h-7" />
                      <path d="M3 14l7 7" />
                      <path d="M3 21h7v-7" />
                    </svg>
                  </button>
                </div>
              </div>
            </template>

            <div class="grid gap-4 pb-8">
              <MessageItem
                v-for="item, index in activeMessages" :key="`expanded-${index}`"
                :role="item.role" :content="item.content"
                :reasoning="item.reasoning" :sender="item.sender"
                :generating="item.generating" :status="item.status"
                :tool-events="item.toolEvents"
                :soul-data="item.soulData"
            :class="(item.generating && index === activeMessages.length - 1) || 'msg-sep'"
              />
            </div>
          </BoxContainer>
        </div>
      </Teleport>
    </div>

    <Transition name="slide-up">
      <div v-if="showHistory && !isExpanded" class="session-panel">
        <div class="flex items-center justify-between px-3 py-2 session-panel-header">
          <span class="text-white/70 text-sm font-bold">对话历史</span>
          <button
            class="text-white/40 hover:text-white/80 bg-transparent border-none cursor-pointer text-xs"
            @click="showHistory = false"
          >
            关闭
          </button>
        </div>
        <div class="overflow-y-auto max-h-48">
          <div v-if="loadingSessions" class="text-white/40 text-xs text-center py-4">
            加载中...
          </div>
          <div v-else-if="sessions.length === 0" class="text-white/40 text-xs text-center py-4">
            暂无历史对话
          </div>
          <div
            v-for="s in sessions" :key="s.sessionId"
            class="session-item"
            :class="{ 'bg-white/10': s.sessionId === CURRENT_SESSION_ID }"
            @click="handleSwitchSession(s.sessionId)"
          >
            <div class="flex-1 min-w-0">
              <div class="text-white/80 text-sm truncate">
                {{ s.sessionId.slice(0, 8) }}...
              </div>
              <div class="text-white/40 text-xs">
                {{ formatRelativeTime(s.lastActiveAt) }} · {{ s.conversationRounds }} 轮对话
              </div>
            </div>
            <button
              class="text-white/30 hover:text-red-400 bg-transparent border-none cursor-pointer text-xs shrink-0 ml-2"
              title="删除"
              @click.stop="handleDeleteSession(s.sessionId)"
            >
              x
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <div
      ref="inputDockRef"
      :class="isExpanded ? 'expanded-input-dock' : 'mx-[var(--nav-back-width)]'"
      :style="isExpanded ? expandedInputStyle : undefined"
    >
      <div class="miya-input-box flex items-center gap-2 min-w-0">
        <button
          class="input-icon-btn shrink-0"
          title="新建对话"
          @click="handleNewSession"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14" /></svg>
        </button>
        <button
          class="input-icon-btn shrink-0"
          :class="{ 'active': showHistory }"
          title="对话历史"
          @click="toggleHistory"
        >
          H
        </button>
        <span class="input-prefix shrink-0">&gt;</span>
        <textarea
          ref="composerRef"
          v-model="input"
          rows="1"
          class="composer-textarea flex-1 min-w-0 text-white bg-transparent border-none outline-none"
          placeholder="Type a message..."
          @keydown.enter.exact="handleComposerEnter"
          @input="resizeComposer"
        />
        <button
          v-if="CONFIG.voice_realtime.enabled"
          class="input-icon-btn shrink-0"
          :class="{ recording: isRecording }"
          :title="isRecording ? '停止录音' : '语音输入'"
          @click="toggleVoiceInput"
        >
          <svg v-if="!isRecording" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" x2="12" y1="19" y2="22" /></svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="6" width="12" height="12" rx="2" /></svg>
        </button>
        <button
          v-if="CONFIG.system.voice_enabled"
          class="input-icon-btn shrink-0"
          :title="ttsEnabled ? '关闭语音播报' : '开启语音播报'"
          @click="toggleTTS"
        >
          <svg v-if="ttsEnabled" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" /><path d="M15.54 8.46a5 5 0 0 1 0 7.07" /></svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" /><line x1="22" y1="9" x2="16" y2="15" /><line x1="16" y1="9" x2="22" y2="15" /></svg>
        </button>
        <button
          class="input-icon-btn shrink-0"
          title="上传文件 (Word/Excel/文本)"
          @click="triggerUpload"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" /><path d="M14 2v4a2 2 0 0 0 2 2h4" /><path d="M12 18v-6" /><path d="m9 15 3-3 3 3" /></svg>
        </button>
        <input
          ref="fileInput"
          type="file"
          accept=".docx,.xlsx,.txt,.csv,.md,.pdf,.png,.jpg,.jpeg"
          class="hidden"
          @change="handleFileUpload"
        >
        <button
          class="send-btn shrink-0"
          :disabled="!input?.trim()"
          title="发送消息"
          @click="sendMessage"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 2 11 13" />
            <path d="m22 2-7 20-4-9-9-4Z" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.expanded-chat-overlay {
  position: fixed;
  z-index: 80;
}

.expanded-input-dock {
  position: fixed;
  z-index: 81;
}

.expanded-chat-overlay :deep(.box) {
  width: 100%;
  height: 100%;
}

.composer-textarea {
  min-height: 44px;
  max-height: 160px;
  padding: 10px 0;
  line-height: 24px;
  resize: none;
  overflow-y: auto;
}

.composer-textarea::placeholder {
  color: color-mix(in srgb, var(--miya-comp-message-ai) 30%, transparent);
}

.input-prefix {
  color: color-mix(in srgb, var(--miya-comp-message-ai) 50%, transparent);
  font-size: 1rem;
  line-height: 1;
  padding-left: 0.15rem;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.send-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: center;
  width: 36px;
  height: 36px;
  border: 1px solid color-mix(in srgb, var(--miya-comp-message-ai) 30%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--miya-comp-message-ai) 8%, transparent);
  color: color-mix(in srgb, var(--miya-comp-message-ai) 90%, transparent);
  cursor: pointer;
  transition: all 0.25s ease;
}

.send-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--miya-comp-message-ai) 18%, transparent);
  border-color: color-mix(in srgb, var(--miya-comp-message-ai) 60%, transparent);
  box-shadow: 0 0 16px color-mix(in srgb, var(--miya-comp-message-ai) 25%, transparent);
  transform: translateY(-1px);
}

.send-btn:disabled {
  opacity: 0.3;
  cursor: default;
  border-color: color-mix(in srgb, var(--miya-comp-message-ai) 10%, transparent);
  background: transparent;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: flex-end;
}

.tab-row {
  display: flex;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
}

.window-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
}

.window-btn {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid color-mix(in srgb, var(--miya-comp-message-ai) 15%, transparent);
  border-radius: 8px;
  background: color-mix(in srgb, var(--miya-comp-message-ai) 5%, transparent);
  color: color-mix(in srgb, var(--miya-comp-message-ai) 60%, transparent);
  cursor: pointer;
  transition: all 0.2s ease;
}

.window-btn:hover {
  background: color-mix(in srgb, var(--miya-comp-message-ai) 12%, transparent);
  color: color-mix(in srgb, var(--miya-comp-message-ai) 95%, transparent);
  border-color: color-mix(in srgb, var(--miya-comp-message-ai) 40%, transparent);
  box-shadow: 0 0 12px color-mix(in srgb, var(--miya-comp-message-ai) 15%, transparent);
}

.msg-sep {
  border-bottom: 1px solid color-mix(in srgb, var(--miya-comp-message-ai) 8%, transparent);
}

.session-panel-header {
  border-bottom: 1px solid color-mix(in srgb, var(--miya-comp-message-ai) 8%, transparent);
}

.session-panel {
  position: absolute;
  left: var(--nav-back-width);
  right: 0;
  bottom: 5rem;
  background: rgba(30, 30, 30, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  backdrop-filter: blur(12px);
  z-index: 10;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  transition: background 0.15s;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.2s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.input-icon-btn {
  padding: 0.5rem;
  color: color-mix(in srgb, var(--miya-comp-message-ai) 40%, transparent);
  background: transparent;
  border: none;
  cursor: pointer;
  border-radius: 0.5rem;
  transition: all 0.2s;
  font-size: 0.9rem;
}

.input-icon-btn:hover {
  color: color-mix(in srgb, var(--miya-comp-message-ai) 80%, transparent);
  background: color-mix(in srgb, var(--miya-comp-message-ai) 8%, transparent);
}

.miya-input-box {
  background: color-mix(in srgb, var(--miya-comp-message-bg) 50%, #000);
  border: 1px solid color-mix(in srgb, var(--miya-comp-message-ai) 15%, transparent);
  clip-path: polygon(0 4px, 4px 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%);
  padding: 0.4rem 0.6rem;
  backdrop-filter: blur(12px);
  transition: border-color 0.3s;
}
.miya-input-box:focus-within {
  border-color: rgba(0, 229, 255, 0.4);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.08);
}

.composer-textarea {
  min-height: 40px;
  max-height: 140px;
  padding: 8px 0;
  line-height: 22px;
  resize: none;
  overflow-y: auto;
  font-family: 'Noto Sans SC', sans-serif;
}

.composer-textarea::placeholder {
  color: rgba(0, 229, 255, 0.18);
}

.input-prefix {
  color: rgba(0, 229, 255, 0.4);
  font-size: 0.9rem;
  font-family: 'JetBrains Mono', monospace;
}

.send-btn {
  display: inline-flex; align-items: center; justify-content: center;
  align-self: center; width: 34px; height: 34px;
  border: 1px solid rgba(0, 229, 255, 0.25); border-radius: 2px;
  background: rgba(0, 229, 255, 0.06); color: rgba(0, 229, 255, 0.8);
  cursor: pointer; transition: all 0.25s ease;
  clip-path: polygon(2px 0, 100% 0, 100% calc(100% - 2px), calc(100% - 2px) 100%, 0 100%, 0 2px);
}
.send-btn:hover:not(:disabled) {
  background: rgba(0, 229, 255, 0.15); border-color: rgba(0, 229, 255, 0.5);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
}
.send-btn:disabled { opacity: 0.25; cursor: default; background: transparent; }

.input-icon-btn.recording {
  color: #f87171;
  animation: recording-pulse 1.2s ease-in-out infinite;
}

@keyframes recording-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(248, 113, 113, 0.4); }
  50% { box-shadow: 0 0 0 6px rgba(248, 113, 113, 0); }
}
</style>
