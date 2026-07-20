<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { onMounted, onUnmounted, ref } from 'vue'
import API from '@/api/core'

const backendOnline = ref(false)
const miyaPersona = ref('默认')
const currentTime = ref('')
let timer: ReturnType<typeof setInterval> | null = null

async function fetchStatus() {
  try {
    const health = await API.health()
    backendOnline.value = health.status === 'healthy'
    const persona = await API.getCurrentPersona()
    miyaPersona.value = persona?.persona?.name || persona?.persona?.id || '默认'
  } catch {
    backendOnline.value = false
  }
}

function updateTime() {
  currentTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  fetchStatus()
  updateTime()
  timer = setInterval(() => {
    updateTime()
    fetchStatus()
  }, 30000)
})

onUnmounted(() => { if (timer) clearInterval(timer) })

const showStatus = useStorage('miya-show-status', true)
</script>

<template>
  <header v-if="showStatus" class="top-bar">
    <div class="top-left">
      <span class="top-dot" :class="{ online: backendOnline }" />
      <span class="top-brand">MIYA</span>
      <span class="top-sep">·</span>
      <span class="top-persona">{{ miyaPersona }}</span>
    </div>
    <div class="top-right">
      <span class="top-time">{{ currentTime }}</span>
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 32px;
  min-height: 32px;
  padding: 0 1rem;
  border-bottom: 1px solid color-mix(in srgb, var(--miya-border) 3%, transparent);
  z-index: 60;
  user-select: none;
}

.top-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.top-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(255, 100, 100, 0.45);
  transition: all 0.5s ease;
}

.top-dot.online {
  background: color-mix(in srgb, var(--miya-chat-ai) 50%, transparent);
  box-shadow: 0 0 6px color-mix(in srgb, var(--miya-chat-ai) 30%, transparent);
}

.top-brand {
  font-family: 'Noto Serif SC', serif;
  font-size: 0.7rem;
  font-weight: 700;
  background: linear-gradient(135deg, var(--miya-chat-ai), var(--miya-accent));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.top-sep {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.5rem;
  color: color-mix(in srgb, var(--miya-border) 20%, transparent);
}

.top-persona {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.52rem;
  color: color-mix(in srgb, var(--miya-border) 40%, transparent);
  letter-spacing: 0.04em;
}

.top-right {
  display: flex;
  align-items: center;
}

.top-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
  color: color-mix(in srgb, var(--miya-chat-ai) 35%, transparent);
}
</style>
