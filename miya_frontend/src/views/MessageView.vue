<script lang="ts">
import type { ChatTab, Message } from '@/utils/session'
import { useEventListener } from '@vueuse/core'
import Dialog from 'primevue/dialog'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue'
import API from '@/api/core'
import GlassPanel from '@/components/GlassPanel.vue'
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
    const soulRes = await fetch(`http://localhost:${Number(import.meta.env.VITE_API_PORT) || 9800}/api/soul/current`)
    const directSoul = await soulRes.json()
    if (directSoul && (directSoul.emotions || directSoul.inner_thought || directSoul.thinking)) {
      applySoulToMessage(directSoul)
      return
    }

    const res = await fetch(`http://localhost:${Number(import.meta.env.VITE_API_PORT) || 9800}/api/desktop/files/read?path=data%2Fmemory%2Fcognitive_memories.json`)
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
    image_data: (options?.images?.length ?? 0) > 0 ? options!.images![0] : undefined,
  } as any).then((res: any) => {
    let responseText = ''
    const soulRaw: any = {}
    if (typeof res === 'string' && res.startsWith('data:')) {
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
      if (res?.soul) {
        Object.assign(soulRaw, res.soul)
      }
    }

    pushContent(responseText || res?.response || JSON.stringify(res))
    message.generating = false
    message.status = undefined
    proxySetState('idle')

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
      fetchSoulData()
    }

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
const scrollPanelRef = useTemplateRef<{
  scrollTop: (scrollTop: number) => void
}>('scrollPanelRef')

const normalContainerRef = ref<InstanceType<typeof GlassPanel> | null>(null)
const expandedContainerRef = ref<InstanceType<typeof GlassPanel> | null>(null)
const composerRef = ref<HTMLTextAreaElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const inputDockRef = ref<HTMLElement | null>(null)
const isExpanded = ref(false)
const expandedStyle = ref<Record<string, string>>({})
const expandedInputStyle = ref<Record<string, string>>({})
const expandedAnchorLeft = ref(8)
const msgListRef = ref<HTMLDivElement | null>(null)
const msgListExpandedRef = ref<HTMLDivElement | null>(null)
const showMoreActions = ref(false)

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
  if (!inputDockRef.value) return
  const msgEl = (normalContainerRef.value as any)?.$el as HTMLElement | undefined
  const chatRect = msgEl?.getBoundingClientRect?.()
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
  const el = isExpanded.value ? msgListExpandedRef.value : msgListRef.value
  if (el) el.scrollTop = el.scrollHeight
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
  <div class="msg-view">
    <div class="msg-view-main">
      <!-- 主内容区 -->
      <GlassPanel v-show="!isExpanded" ref="normalContainerRef" title="弥娅对话" subtitle="CHAT · SOUL RESONANCE" size="fluid" class="msg-glass">
        <template #header-actions>
          <button
            class="msg-expand-btn"
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
        </template>

        <div ref="msgListRef" class="msg-scroll">
          <div class="msg-list">
            <TransitionGroup name="msg-in">
              <MessageItem
                v-for="item, index in activeMessages" :key="index"
                :role="item.role" :content="item.content"
                :reasoning="item.reasoning" :sender="item.sender"
                :generating="item.generating" :status="item.status"
                :tool-events="item.toolEvents"
                :soul-data="item.soulData"
                :style="{ '--msg-index': index }"
              />
            </TransitionGroup>
          </div>
        </div>
      </GlassPanel>

      <Teleport to="body">
        <div v-if="isExpanded" class="expanded-overlay" :style="expandedStyle">
          <GlassPanel ref="expandedContainerRef" title="弥娅对话" subtitle="CHAT · EXPANDED VIEW" size="full" :hide-back="false">
            <template #header-actions>
              <button
                class="msg-expand-btn"
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
            </template>

            <div ref="msgListExpandedRef" class="msg-scroll">
              <div class="msg-list">
                <TransitionGroup name="msg-in">
                  <MessageItem
                    v-for="item, index in activeMessages" :key="`expanded-${index}`"
                    :role="item.role" :content="item.content"
                    :reasoning="item.reasoning" :sender="item.sender"
                    :generating="item.generating" :status="item.status"
                    :tool-events="item.toolEvents"
                    :soul-data="item.soulData"
                    :style="{ '--msg-index': index }"
                  />
                </TransitionGroup>
              </div>
            </div>
          </GlassPanel>
        </div>
      </Teleport>
    </div>

    <!-- ── 会话历史面板 ── -->
    <Transition name="slide-up">
      <div v-if="showHistory && !isExpanded" class="history-panel">
        <div class="history-header">
          <span class="history-title">◇ 对话历史</span>
          <button class="history-close" @click="showHistory = false">✕</button>
        </div>
        <div class="history-list">
          <div v-if="loadingSessions" class="history-loading">加载中...</div>
          <div v-else-if="sessions.length === 0" class="history-empty">暂无历史对话</div>
          <div
            v-for="s in sessions" :key="s.sessionId"
            class="history-item"
            :class="{ active: s.sessionId === CURRENT_SESSION_ID }"
            @click="handleSwitchSession(s.sessionId)"
          >
            <div class="history-item-main">
              <span class="history-item-id">{{ s.sessionId.slice(0, 8) }}</span>
              <span class="history-item-meta">{{ formatRelativeTime(s.lastActiveAt) }} · {{ s.conversationRounds }} 轮</span>
            </div>
            <button
              class="history-del"
              title="删除"
              @click.stop="handleDeleteSession(s.sessionId)"
            >✕</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── 输入栏 ── -->
    <div
      ref="inputDockRef"
      class="input-dock"
      :class="{ expanded: isExpanded }"
      :style="isExpanded ? expandedInputStyle : undefined"
    >
      <div class="input-box">
        <div class="input-main">
          <button class="input-btn" title="新建对话" @click="handleNewSession">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14" /></svg>
          </button>
          <span class="input-cursor">&gt;</span>
          <textarea
            ref="composerRef"
            v-model="input"
            rows="1"
            class="input-textarea"
            placeholder="与弥娅对话..."
            @keydown.enter.exact="handleComposerEnter"
            @input="resizeComposer"
          />
          <div class="input-actions">
            <button
              class="input-btn" :class="{ active: showHistory }"
              title="对话历史" @click="toggleHistory"
            >H</button>
            <button
              v-if="CONFIG.voice_realtime.enabled"
              class="input-btn" :class="{ recording: isRecording }"
              :title="isRecording ? '停止录音' : '语音输入'"
              @click="toggleVoiceInput"
            >
              <svg v-if="!isRecording" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" x2="12" y1="19" y2="22" /></svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2"><rect x="6" y="6" width="12" height="12" rx="2" /></svg>
            </button>
          </div>

          <!-- 更多操作 -->
          <div class="input-more-wrap">
            <button class="input-btn" title="更多" @click="showMoreActions = !showMoreActions">···</button>
          </div>

          <button
            class="send-btn" :disabled="!input?.trim()" title="发送"
            @click="sendMessage"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 2 11 13" />
              <path d="m22 2-7 20-4-9-9-4Z" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 更多菜单 (放在 input-box 外面避免被 clip-path 裁切) -->
      <Transition name="more-pop">
        <div v-if="showMoreActions" class="input-more-menu">
          <button v-if="CONFIG.system.voice_enabled" class="more-item" @click="toggleTTS">
            {{ ttsEnabled ? '♪ 关闭语音播报' : '♪ 开启语音播报' }}
          </button>
          <button class="more-item" @click="triggerUpload">⇧ 上传文件</button>
        </div>
      </Transition>
      <input
        ref="fileInput"
        type="file"
        accept=".docx,.xlsx,.txt,.csv,.md,.pdf,.png,.jpg,.jpeg"
        class="hidden"
        @change="handleFileUpload"
      >
    </div>
  </div>
</template>

<style scoped>
.msg-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.msg-view-main {
  flex: 1;
  min-height: 0;
  display: flex;
}

.msg-glass {
  width: 100%;
  flex: 1;
}

/* ── 消息列表 ── */
.msg-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 0.3rem;
}

.msg-scroll::-webkit-scrollbar { width: 4px; }
.msg-scroll::-webkit-scrollbar-track { background: transparent; }
.msg-scroll::-webkit-scrollbar-thumb { background: rgba(0, 173, 181, 0.12); border-radius: 2px; }

.msg-list {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  padding-bottom: 0.5rem;
}

/* 消息入场动画 */
.msg-in-enter-active {
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  transition-delay: calc(var(--msg-index, 0) * 30ms);
}

.msg-in-leave-active {
  transition: all 0.2s ease-in;
}

.msg-in-enter-from {
  opacity: 0;
  transform: translateY(16px) scale(0.97);
}

.msg-in-leave-to {
  opacity: 0;
}

/* ── 展开按钮 ═─ */
.msg-expand-btn {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(0, 173, 181, 0.15);
  background: rgba(0, 173, 181, 0.06);
  color: rgba(0, 173, 181, 0.5);
  cursor: pointer;
  clip-path: polygon(0 4px, 4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%);
  transition: all 0.3s ease;
}

.msg-expand-btn:hover {
  background: rgba(0, 173, 181, 0.16);
  border-color: rgba(0, 255, 245, 0.4);
  color: rgba(0, 255, 245, 0.9);
  box-shadow: 0 0 14px rgba(0, 173, 181, 0.2);
  transform: skewX(-4deg);
}

/* ── 展开浮层 ── */
.expanded-overlay {
  position: fixed;
  z-index: 80;
}

.expanded-overlay :deep(.glass-panel) {
  width: 100%;
  height: 100%;
}

/* ── 会话历史面板 — PGR 风格 ═─ */
.history-panel {
  position: relative;
  margin: 0 0 0.5rem;
  background: rgba(0, 0, 0, 0.55);
  border: 1px solid rgba(0, 173, 181, 0.1);
  clip-path: polygon(0 6px, 6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%);
  backdrop-filter: blur(16px);
  overflow: hidden;
  box-shadow:
    3px 3px 12px rgba(0, 60, 70, 0.35),
    -2px -2px 6px rgba(0, 200, 210, 0.06);
  animation: panel-in 0.25s ease;
}

@keyframes panel-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid rgba(0, 173, 181, 0.08);
}

.history-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.08em;
}

.history-close {
  background: none;
  border: none;
  color: rgba(200, 200, 200, 0.35);
  cursor: pointer;
  font-size: 0.7rem;
  transition: all 0.2s ease;
}

.history-close:hover { color: rgba(0, 255, 245, 0.8); transform: skewX(-4deg); }

.history-list {
  max-height: 200px;
  overflow-y: auto;
}

.history-list::-webkit-scrollbar { width: 3px; }
.history-list::-webkit-scrollbar-thumb { background: rgba(0, 173, 181, 0.1); border-radius: 2px; }

.history-loading,
.history-empty {
  text-align: center;
  padding: 1rem;
  color: rgba(0, 173, 181, 0.3);
  font-size: 0.7rem;
}

.history-item {
  display: flex;
  align-items: center;
  padding: 0.5rem 0.8rem;
  cursor: pointer;
  transition: all 0.15s ease;
  border-bottom: 1px solid rgba(0, 173, 181, 0.04);
}

.history-item:hover,
.history-item.active {
  background: rgba(0, 173, 181, 0.1);
}

.history-item.active {
  border-left: 2px solid rgba(0, 255, 245, 0.5);
  box-shadow: inset 0 0 8px rgba(0, 255, 245, 0.04);
}

.history-item-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.history-item-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: rgba(228, 236, 240, 0.7);
}

.history-item-meta {
  font-size: 0.6rem;
  color: rgba(0, 173, 181, 0.35);
}

.history-del {
  background: none;
  border: none;
  color: rgba(0, 173, 181, 0.2);
  cursor: pointer;
  font-size: 0.65rem;
  padding: 4px;
  transition: color 0.2s;
}

.history-del:hover { color: rgba(255, 100, 100, 0.7); }

/* ── 动画 ── */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.2s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

/* ── 输入栏 ── */
.input-dock {
  position: relative;
  padding-top: 0.5rem;
  margin: 0 0 0 var(--nav-back-width);
}

.input-dock.expanded {
  position: fixed;
  z-index: 81;
  margin: 0;
  padding: 0.5rem 0.5rem 0;
}

.input-box {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(0, 173, 181, 0.08);
  clip-path: polygon(0 4px, 4px 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%);
  padding: 0.35rem 0.5rem;
  backdrop-filter: blur(16px);
  transition: border-color 0.3s, box-shadow 0.3s;
  box-shadow:
    2px 2px 8px rgba(0, 60, 70, 0.3),
    -1px -1px 4px rgba(0, 200, 210, 0.05);
}

.input-box:focus-within {
  border-color: rgba(0, 173, 181, 0.35);
  box-shadow:
    3px 3px 12px rgba(0, 60, 70, 0.4),
    0 0 24px rgba(0, 173, 181, 0.08);
}

.input-main {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.input-cursor {
  color: rgba(0, 255, 245, 0.4);
  font-size: 0.85rem;
  font-family: 'JetBrains Mono', monospace;
  flex-shrink: 0;
  user-select: none;
}

.input-textarea {
  flex: 1;
  min-width: 0;
  min-height: 36px;
  max-height: 140px;
  padding: 6px 0;
  line-height: 22px;
  resize: none;
  overflow-y: auto;
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 0.85rem;
  background: transparent;
  border: none;
  outline: none;
  color: rgba(228, 236, 240, 0.9);
}

.input-textarea::placeholder {
  color: rgba(0, 173, 181, 0.15);
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  flex-shrink: 0;
}

.input-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  background: transparent;
  border: none;
  color: rgba(200, 200, 200, 0.4);
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
  flex-shrink: 0;
}

.input-btn:hover {
  color: rgba(255, 255, 255, 0.85);
  background: rgba(0, 173, 181, 0.12);
  transform: skewX(-5deg);
}

.input-btn.active {
  color: rgba(0, 255, 245, 0.75);
  background: rgba(0, 173, 181, 0.14);
}

.input-btn.recording {
  color: #f87171;
  animation: rec-pulse 1.2s ease-in-out infinite;
}

@keyframes rec-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(248, 113, 113, 0.3); }
  50% { box-shadow: 0 0 0 5px rgba(248, 113, 113, 0); }
}

/* 更多菜单 */
.input-more-wrap {
  flex-shrink: 0;
}

.input-more-menu {
  position: absolute;
  bottom: calc(100% - 2px);
  right: 1rem;
  min-width: 130px;
  background: rgba(0, 0, 0, 0.65);
  border: 1px solid rgba(0, 173, 181, 0.12);
  backdrop-filter: blur(16px);
  box-shadow: 3px 3px 10px rgba(0, 60, 70, 0.4);
  overflow: hidden;
  z-index: 100;
}

.more-item {
  display: block;
  width: 100%;
  padding: 0.4rem 0.7rem;
  background: none;
  border: none;
  color: rgba(200, 200, 200, 0.55);
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 0.7rem;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.more-item:hover {
  background: rgba(0, 173, 181, 0.14);
  color: #ffffff;
  transform: skewX(-4deg);
}

.more-pop-enter-active { transition: all 0.15s ease; }
.more-pop-leave-active { transition: all 0.1s ease; }
.more-pop-enter-from,
.more-pop-leave-to { opacity: 0; transform: translateY(4px); }

/* 发送按钮 */
.send-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 1px solid rgba(0, 173, 181, 0.18);
  background: rgba(0, 173, 181, 0.06);
  color: rgba(0, 173, 181, 0.5);
  cursor: pointer;
  clip-path: polygon(0 3px, 3px 0, 100% 0, 100% calc(100% - 3px), calc(100% - 3px) 100%, 0 100%);
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: rgba(0, 173, 181, 0.2);
  border-color: rgba(0, 255, 245, 0.5);
  color: rgba(0, 255, 245, 0.95);
  box-shadow: 0 0 18px rgba(0, 173, 181, 0.22);
  transform: skewX(-3deg);
}

.send-btn:disabled {
  opacity: 0.15;
  cursor: default;
}
</style>
