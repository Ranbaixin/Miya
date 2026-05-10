<script setup lang="ts">
import { useWindowSize } from '@vueuse/core'
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import API from '@/api/core'

const router = useRouter()
import { CONFIG } from '@/utils/config'

const miyaPersona = ref('')
const miyaBackendOnline = ref(false)
const miyaPlatforms = ref(0)

onMounted(async () => {
  try {
    const health = await API.health()
    miyaBackendOnline.value = health.status === 'healthy'
    const persona = await API.getCurrentPersona()
    miyaPersona.value = persona?.persona?.name || persona?.persona?.id || '默认'
    const platforms = await fetch('http://localhost:9800/api/v1/platforms').then(r => r.json())
    miyaPlatforms.value = platforms.online || 0
  } catch (e) {
    miyaBackendOnline.value = false
  }
})

const { height } = useWindowSize()
const scale = computed(() => Math.min(1.2, Math.max(0.65, height.value / 800)))

const mouse = reactive({ x: 0.5, y: 0.5 })

function onMouseMove(e: MouseEvent) {
  mouse.x = e.clientX / window.innerWidth
  mouse.y = e.clientY / window.innerHeight
}

onMounted(() => window.addEventListener('mousemove', onMouseMove))
onUnmounted(() => window.removeEventListener('mousemove', onMouseMove))

const rx = computed(() => (mouse.y - 0.5) * -8)
const ry = computed(() => (mouse.x - 0.5) * 12)
const tx = computed(() => (mouse.x - 0.5) * -20)
const ty = computed(() => (mouse.y - 0.5) * -15)

function enterFloatingMode() {
  CONFIG.value.floating.enabled = true
  window.electronAPI?.floating.enter()
}
</script>

<template>
  <div class="miya-home">
    <div
      class="miya-parallax"
      :style="{
        transform: `perspective(1000px) rotateX(${rx}deg) rotateY(${ry}deg) translate(${tx}px, ${ty}px) scale(${scale})`,
      }"
    >
      <!-- Logo -->
      <div class="miya-logo">
        <div class="miya-logo-ring">
          <svg viewBox="0 0 100 100" fill="none">
            <circle cx="50" cy="42" r="36" stroke="var(--miya-primary)" stroke-width="1.2" opacity="0.3" />
            <circle cx="50" cy="42" r="24" stroke="var(--miya-accent)" stroke-width="1.8" opacity="0.5" />
            <circle cx="50" cy="42" r="12" stroke="var(--miya-primary)" stroke-width="2" opacity="0.4" />
            <path d="M50 5C50 5 22 25 22 50C22 68 50 85 50 85" stroke="var(--miya-primary)" stroke-width="1.5" stroke-linecap="round" opacity="0.6" />
            <path d="M50 5C50 5 78 25 78 50C78 68 50 85 50 85" stroke="var(--miya-primary)" stroke-width="1.5" stroke-linecap="round" opacity="0.4" />
            <circle cx="50" cy="42" r="5" fill="var(--miya-accent)" opacity="0.8" />
            <circle cx="38" cy="38" r="2" fill="var(--miya-gold)" opacity="0.6" />
            <circle cx="62" cy="38" r="2" fill="var(--miya-gold)" opacity="0.6" />
            <circle cx="50" cy="55" r="1.5" fill="var(--miya-gold)" opacity="0.4" />
          </svg>
        </div>
        <div class="miya-title">弥娅</div>
        <div class="miya-sub">MIYA</div>
      </div>

      <!-- 导航区域 -->
      <div class="miya-nav">
        <button class="miya-card chat-card" @click="router.push('/chat')">
          <div class="miya-card-glow" />
          <div class="miya-card-content">
            <span class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" /></svg>
            </span>
            <div class="card-text">
              <span class="card-label">弥娅对话</span>
              <span class="card-desc">决策层 · 感知 · 协作引擎</span>
            </div>
          </div>
        </button>

        <div class="miya-grid">
          <button class="miya-card" @click="router.push('/mind')">
            <div class="miya-card-content">
              <span class="card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10" /><circle cx="8" cy="9" r="1.2" fill="currentColor" opacity="0.6" /><circle cx="16" cy="8" r="1" fill="currentColor" opacity="0.4" /><circle cx="14" cy="14" r="1.2" fill="currentColor" opacity="0.5" /><circle cx="6" cy="15" r="0.8" fill="currentColor" opacity="0.3" /><circle cx="18" cy="15" r="0.8" fill="currentColor" opacity="0.3" /><path d="M2 12h2M20 12h2" opacity="0.3" /></svg>
              </span>
              <div class="card-text">
                <span class="card-label">记忆星河</span>
                <span class="card-desc">认知引擎 · 记忆网络</span>
              </div>
            </div>
          </button>

          <button class="miya-card" @click="router.push('/config')">
            <div class="miya-card-content">
              <span class="card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" /></svg>
              </span>
              <div class="card-text">
                <span class="card-label">灵魂调谐</span>
                <span class="card-desc">人格 · 情绪 · 模型池</span>
              </div>
            </div>
          </button>

          <button class="miya-card" @click="enterFloatingMode">
            <div class="miya-card-content">
              <span class="card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2a3 3 0 013 3v1a1 1 0 01-1 1h-4a1 1 0 01-1-1V5a3 3 0 013-3z" /><path d="M9 8h6a3 3 0 013 3v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-1a3 3 0 013-3z" /><circle cx="12" cy="17" r="4" /><path d="M10 17h4" /></svg>
              </span>
              <div class="card-text">
                <span class="card-label">铃音守护</span>
                <span class="card-desc">轻量陪伴 · 悬浮球</span>
              </div>
            </div>
          </button>

          <button class="miya-card" disabled>
            <div class="miya-card-content">
              <span class="card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><path d="M21 15l-5-5L5 21" /></svg>
              </span>
              <div class="card-text">
                <span class="card-label">感知画卷</span>
                <span class="card-desc">即将开放</span>
              </div>
            </div>
          </button>
        </div>
      </div>

      <div class="miya-verse">雪落无声 — 愿系铃中</div>

      <!-- 弥娅系统状态 -->
      <div v-if="miyaBackendOnline" class="miya-status">
        <span class="status-badge online">● 在线</span>
        <span class="status-item">{{ miyaPlatforms }} 平台</span>
        <span class="status-item">人格: {{ miyaPersona }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.miya-home {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  user-select: none;
  overflow: hidden;
}

.miya-parallax {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  will-change: transform;
  transform-style: preserve-3d;
  transition: transform 0.1s linear;
}

/* ── Logo ── */
.miya-logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
}

.miya-logo-ring {
  width: 100px;
  height: 100px;
  filter: drop-shadow(0 0 20px var(--miya-glow));
}

.miya-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 3rem;
  font-weight: 700;
  background: linear-gradient(135deg, #e8d5f5 0%, var(--miya-accent) 40%, var(--miya-primary) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 0.2em;
  text-shadow: none;
  filter: drop-shadow(0 0 12px var(--miya-glow));
}

.miya-sub {
  font-size: 0.65rem;
  color: var(--miya-text-dim);
  letter-spacing: 0.4em;
}

/* ── 导航 ── */
.miya-nav {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  width: min(420px, 80vw);
}

.miya-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.8rem;
}

/* ── 卡片 ── */
.miya-card {
  --p-border: var(--miya-comp-panel-border, #a78bfa);
  --p-btn: var(--miya-comp-panel-btn, #a78bfa);
  --p-icon: var(--miya-comp-panel-icon, #a78bfa);
  position: relative;
  background: var(--miya-surface);
  border: 1px solid color-mix(in srgb, var(--p-border) 12%, transparent);
  border-radius: 1rem;
  color: var(--miya-text);
  cursor: pointer;
  padding: 0;
  overflow: hidden;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(10px);
}

.miya-card:hover:not(:disabled) {
  border-color: var(--miya-primary);
  transform: translateY(-3px) scale(1.02);
  box-shadow: 0 12px 40px rgba(167, 139, 250, 0.2), 0 0 20px var(--miya-glow);
}

.miya-card:active:not(:disabled) {
  transform: translateY(-1px) scale(0.98);
}

.miya-card:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.miya-card-content {
  position: relative;
  z-index: 1;
  padding: 1.2rem 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.card-icon {
  width: 2rem;
  height: 2rem;
  color: var(--miya-primary);
  flex-shrink: 0;
  transition: transform 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.miya-card:hover:not(:disabled) .card-icon {
  transform: scale(1.15);
}

.card-text {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.card-label {
  font-size: 1.05rem;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.card-desc {
  font-size: 0.7rem;
  color: var(--miya-text-dim);
  letter-spacing: 0.05em;
}

/* ── 对话卡片（突出） ── */
.chat-card {
  background: linear-gradient(135deg, rgba(167, 139, 250, 0.12), var(--miya-surface));
  border-color: rgba(167, 139, 250, 0.25);
}

.chat-card:hover {
  border-color: var(--miya-primary);
  box-shadow: 0 12px 50px rgba(167, 139, 250, 0.3);
}

.chat-card .card-label {
  font-size: 1.2rem;
}

.chat-card .miya-card-content {
  padding: 1.5rem 1.5rem;
}

.miya-card-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 30% 50%, var(--miya-glow), transparent 70%);
  opacity: 0;
  transition: opacity 0.4s ease;
}

.chat-card:hover .miya-card-glow {
  opacity: 0.5;
}

/* ── 意境文字 ── */
.miya-verse {
  font-family: 'Noto Serif SC', serif;
  font-size: 0.72rem;
  color: var(--miya-text-dim);
  letter-spacing: 0.2em;
  opacity: 0.5;
}

.miya-status {
  display: flex; align-items: center; gap: 1rem; margin-top: 0.5rem;
  font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
  color: var(--miya-text-dim);
}
.status-badge { color: rgba(0,255,100,0.6); }
.status-badge.online { color: rgba(0,229,255,0.6); }
.status-item { opacity: 0.6; }
</style>
