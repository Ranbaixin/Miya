<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import API from '@/api/core'
import { CONFIG } from '@/utils/config'

const backendOnline = ref(false)
const miyaPersona = ref('默认')
const miyaPlatforms = ref(0)
const currentTime = ref('')
let timer: ReturnType<typeof setInterval> | null = null

async function fetchStatus() {
  try {
    const health = await API.health()
    backendOnline.value = health.status === 'healthy'
    const persona = await API.getCurrentPersona()
    miyaPersona.value = persona?.persona?.name || persona?.persona?.id || '默认'
    const platforms = await fetch('http://localhost:9800/api/v1/platforms').then(r => r.json())
    miyaPlatforms.value = platforms.online || 0
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
  <header class="top-bar">
    <div class="top-left">
      <span class="top-brand">MIYA</span>
      <span class="top-sep">//</span>
      <span class="top-version">v2.0</span>
    </div>

    <div v-if="showStatus" class="top-center">
      <span class="top-dot" :class="{ online: backendOnline }" />
      <span class="top-status-text">
        {{ backendOnline ? 'SYS.ONLINE' : 'SYS.OFFLINE' }}
      </span>
      <span class="top-sep">·</span>
      <span class="top-status-text">{{ miyaPlatforms }} 平台</span>
      <span class="top-sep">·</span>
      <span class="top-status-text">人格: {{ miyaPersona }}</span>
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
  height: 36px;
  min-height: 36px;
  padding: 0 1rem;
  background: transparent;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border-bottom: 1px solid color-mix(in srgb, var(--miya-border) 4%, transparent);
  z-index: 60;
  user-select: none;
}

.top-left {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.top-brand {
  font-family: 'Noto Serif SC', serif;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  background: linear-gradient(135deg, var(--miya-chat-ai), var(--miya-accent));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.top-sep {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
  color: color-mix(in srgb, var(--miya-border) 25%, transparent);
}

.top-version {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.5rem;
  color: color-mix(in srgb, var(--miya-border) 35%, transparent);
  letter-spacing: 0.1em;
}

.top-center {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
}

.top-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(255, 100, 100, 0.5);
  box-shadow: 0 0 4px rgba(255, 100, 100, 0.3);
  transition: all 0.5s ease;
}

.top-dot.online {
  background: color-mix(in srgb, var(--miya-chat-ai) 60%, transparent);
  box-shadow: 0 0 8px color-mix(in srgb, var(--miya-chat-ai) 40%, transparent);
}

.top-status-text {
  color: color-mix(in srgb, var(--miya-border) 50%, transparent);
  letter-spacing: 0.05em;
}

.top-right {
  display: flex;
  align-items: center;
}

.top-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  color: color-mix(in srgb, var(--miya-chat-ai) 45%, transparent);
}
</style>
