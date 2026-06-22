<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import API from '@/api/core'
import { playBgm, stopBgm, bgmFileOptions, audioSettings } from '@/composables/useAudio'

const router = useRouter()

const backendOnline = ref(false)
const miyaPersona = ref('默认')
const soulActive = ref(87)
const currentTime = ref('')
const miyaThought = ref('佳，今天的星空很美呢...')
const currentBgm = ref('快乐的小曲')
const miyaPlatforms = ref(3)
const memoryTotal = ref(0)
const emotionName = ref('平静')
let timer: ReturnType<typeof setInterval> | null = null
let statusTimer: ReturnType<typeof setInterval> | null = null

// ═══ 隐藏/显示面板 ═══
const panelsHidden = useStorage('miya-panels-hidden', false)
function togglePanels() {
  panelsHidden.value = !panelsHidden.value
}

// ═══ BGM 控制 ═══
const bgmPlaying = ref(false)
const bgmAvailable = computed(() => bgmFileOptions.length > 0)

function toggleBgm() {
  if (!bgmAvailable.value) return
  if (bgmPlaying.value) {
    stopBgm()
    bgmPlaying.value = false
  } else {
    const file = bgmFileOptions[0]!
    playBgm(file)
    currentBgm.value = file.replace(/\.[^.]+$/, '')
    bgmPlaying.value = true
  }
}

async function loadSystemStatus() {
  try {
    const [statusRes, personaRes] = await Promise.all([
      API.systemStatus(),
      API.getCurrentPersona(),
    ])
    backendOnline.value = true

    // 人格信息
    miyaPersona.value = personaRes?.persona?.name || personaRes?.persona?.id || '默认'

    // 从 systemStatus 读取实时数据
    if (statusRes?.identity) {
      // 情感状态
      const emotion = statusRes.emotion || {}
      emotionName.value = emotion.emotion_name || '平静'
      soulActive.value = emotion.intensity ?? emotion.emotions?.[0]?.intensity ?? 87

      // 记忆统计
      const mem = statusRes.memory_stats || {}
      memoryTotal.value = mem.total || mem.short_term || 0

      // 平台信息
      const plat = statusRes.platform_info || {}
      miyaPlatforms.value = plat.enabled_count ?? plat.total_count ?? 3
    }

    // 如果有 soul 数据
    if (personaRes?.soul) {
      soulActive.value = personaRes.soul.activity || soulActive.value
    }
  } catch {
    backendOnline.value = false
  }
}

onMounted(async () => {
  await loadSystemStatus()
  updateTime()
  timer = setInterval(updateTime, 10000)
  statusTimer = setInterval(loadSystemStatus, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (statusTimer) clearInterval(statusTimer)
})

function updateTime() {
  currentTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const leftCards = [
  { id: 'chat', label: '对话', desc: '灵魂共鸣', path: '/chat' },
  { id: 'mind', label: '记忆', desc: '认知星河', path: '/mind' },
  { id: 'artboard', label: '画板', desc: 'AI 创作', path: '/artboard' },
  { id: 'terminal', label: '终端', desc: 'CC 引擎', path: '/terminal' },
]

const rightLinks = [
  { id: 'config', label: '调谐', desc: '人格·模型', path: '/config' },
  { id: 'community', label: '社区', desc: '娜迦', path: '/community' },
  { id: 'security', label: '安全', desc: '扫描', path: '/security' },
  { id: 'hub', label: '中枢', desc: '功能聚合', path: '/hub' },
]

// ═══ Banner 图片轮播 ═══
const bannerImages = ['aims.jpg', 'bg.png', '01.png', 'feixue.jpg']
const bannerIdx = ref(0)
const bannerText = ref('弥娅 v2.0 · 全新看板娘上线')
const bannerTexts = ['弥娅 v2.0 · 全新看板娘上线', '新增记忆星河 3D 可视化', '安全中心 · 漏洞扫描引擎', '多平台接入 · 智能联动']
let bannerTimer: ReturnType<typeof setInterval> | null = null

const currentBannerImg = computed(() => `/backgrounds/${bannerImages[bannerIdx.value]}`)
const nextBannerImg = computed(() => `/backgrounds/${bannerImages[(bannerIdx.value + 1) % bannerImages.length]}`)

onMounted(() => {
  bannerTimer = setInterval(() => {
    bannerIdx.value = (bannerIdx.value + 1) % bannerImages.length
    bannerText.value = bannerTexts[bannerIdx.value]!
  }, 4000)
})
onUnmounted(() => { if (bannerTimer) clearInterval(bannerTimer) })

function navigate(path: string) { router.push(path) }

const chatExpanded = ref(false)

function toggleChat() { chatExpanded.value = !chatExpanded.value }
</script>

<template>
  <div class="command-center">
    <!-- ═══ 左面板 ═══ -->
    <div class="cmd-panel cmd-left" :class="{ 'panel-hidden': panelsHidden }">
      <div class="cmd-top">
        <div class="cmd-level" @click="navigate('/chat')">
          <div class="cmd-level-head">
            <span class="cmd-level-label">灵魂活跃度</span>
            <span class="cmd-level-val">{{ soulActive }}</span>
          </div>
          <div class="cmd-level-bar">
            <div class="cmd-level-fill" :style="{ width: `${Math.min(soulActive, 100)}%` }" />
          </div>
        </div>
        <div class="cmd-name" @click="navigate('/chat')">
          <span class="cmd-name-main">弥娅</span>
          <span class="cmd-name-sub">MIYA · {{ miyaPersona }} · {{ emotionName }}</span>
        </div>
      </div>

      <div class="cmd-center">
        <div class="cmd-toggle-row">
          <button class="cmd-toggle-btn" title="隐藏面板" @click="togglePanels">
            <span class="cmd-toggle-icon">⊙</span>
          </button>
          <div class="cmd-music" @click="toggleBgm" :title="bgmPlaying ? '暂停 BGM' : '播放 BGM'">
            <span class="cmd-music-icon" :class="{ playing: bgmPlaying }">♪</span>
            <div class="cmd-music-scroll">
              <span class="cmd-music-text">
                {{ bgmPlaying ? `正在播放 — ${currentBgm}` : 'BGM 已暂停' }}
              </span>
            </div>
          </div>
        </div>

        <div class="cmd-nav">
          <button
            v-for="card in leftCards" :key="card.id"
            class="cmd-nav-card"
            @click="navigate(card.path)"
          >
            <span class="cmd-nav-icon">{{ { chat: '◆', mind: '◇', artboard: '⬡', terminal: '▷' }[card.id] }}</span>
            <span class="cmd-nav-title">{{ card.label }}</span>
            <span class="cmd-nav-desc">{{ card.desc }}</span>
          </button>
        </div>
      </div>

      <div class="cmd-bottom-area">
        <div class="cmd-banner" @click="navigate('/chat')">
          <div class="cmd-banner-track">
            <Transition name="banner-slide" mode="out-in">
              <div class="cmd-banner-slide" :key="bannerIdx">
                <img :src="currentBannerImg" class="cmd-banner-img" alt="banner" />
              </div>
            </Transition>
          </div>
          <div class="cmd-banner-label">
            <Transition name="banner-fade" mode="out-in">
              <span :key="bannerText" class="cmd-banner-text">{{ bannerText }}</span>
            </Transition>
          </div>
        </div>
        <div class="cmd-chat" :class="{ expanded: chatExpanded }" @click="toggleChat">
          <div class="cmd-chat-icon">💬</div>
          <div class="cmd-chat-text">
            <span class="cmd-chat-line">✦「{{ miyaThought }}」</span>
            <span class="cmd-chat-line">✨ 佳，有什么需要帮忙的吗？</span>
            <span class="cmd-chat-line">💭 记忆条目: {{ memoryTotal }} | 情感: {{ emotionName }}</span>
            <span class="cmd-chat-line">🎵 {{ bgmPlaying ? `BGM: ${currentBgm}` : 'BGM 已暂停' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ 右面板 ═══ -->
    <div class="cmd-panel cmd-right" :class="{ 'panel-hidden': panelsHidden }">
      <div class="cmd-resources">
        <div class="cmd-res-item" @click="navigate('/chat')">
          <span class="cmd-res-icon">◆</span>
          <span class="cmd-res-val" :title="`灵魂活跃度: ${soulActive}`">{{ soulActive }}</span>
          <span class="cmd-res-plus">+</span>
        </div>
        <div class="cmd-res-item">
          <span class="cmd-res-icon">⬢</span>
          <span class="cmd-res-val" :title="`接入平台: ${miyaPlatforms}`">{{ miyaPlatforms }}</span>
          <span class="cmd-res-plus">+</span>
        </div>
        <div class="cmd-res-item">
          <span class="cmd-res-icon">⬡</span>
          <span class="cmd-res-val time-font">{{ currentTime }}</span>
          <span class="cmd-res-plus">+</span>
        </div>
      </div>

      <div class="cmd-right-center">
        <!-- 时间 + 图标 -->
        <div class="cmd-time-row">
          <span class="cmd-time-icon" :class="{ active: backendOnline }" :title="backendOnline ? '后端在线' : '后端离线'">🔋</span>
          <span class="cmd-time-val">{{ currentTime }}</span>
          <div class="cmd-time-icons">
            <span class="cmd-time-icn" title="消息" @click="navigate('/chat')">✉</span>
            <span class="cmd-time-icn" title="设置" @click="navigate('/config')">⚙</span>
            <span class="cmd-time-icn cmd-hide-icn" title="隐藏面板" @click="togglePanels">⊙</span>
          </div>
        </div>

        <!-- 看板娘卡片 -->
        <div class="cmd-boxline cmd-boxline1">
          <div class="cmd-portrait" @click="navigate('/chat')">
            <div class="cmd-portrait-gloss" />
            <div class="cmd-portrait-avatar">
              <span class="cmd-portrait-char">弥</span>
            </div>
          </div>
          <div class="cmd-battle-info" @click="navigate('/chat')">
            <div class="cmd-battle-left">
              <h1>对话</h1>
              <span class="cmd-battle-tip">灵魂共鸣</span>
              <span class="cmd-battle-nd" :style="{ color: backendOnline ? 'rgba(0,255,245,0.6)' : 'rgba(255,100,100,0.5)' }">
                {{ backendOnline ? '弥娅在线' : '弥娅离线' }}
              </span>
            </div>
            <div class="cmd-battle-right">
              <h2 class="cmd-battle-pct">∞</h2>
              <span>陪伴</span>
            </div>
          </div>
          <div class="cmd-mascot" @click="navigate('/mind')">
            <span class="cmd-mascot-icon">◆</span>
            <span class="cmd-mascot-label">记忆</span>
            <span class="cmd-mascot-val">{{ memoryTotal }}</span>
          </div>
        </div>

        <!-- 任务卡 -->
        <div class="cmd-boxline cmd-boxline2">
          <div class="cmd-quest" @click="navigate('/chat')">
            <div class="cmd-quest-left">
              <h2>日常</h2>
              <span>对话互动</span>
            </div>
            <div class="cmd-quest-right">
              <p>与弥娅进行每日交流</p>
              <span class="cmd-quest-check">✓</span>
            </div>
          </div>
          <div class="cmd-quest-spacer" />
        </div>

        <!-- 功能区 -->
        <div class="cmd-boxline cmd-boxline3">
          <button class="cmd-feat-card" @click="navigate('/artboard')">
            <h1>画板</h1>
            <span>AI 创作</span>
          </button>
          <button class="cmd-feat-card" @click="navigate('/terminal')">
            <h1>终端</h1>
            <span>CC 引擎</span>
            <div class="cmd-feat-badge">新</div>
          </button>
          <div class="cmd-feat-spacer" />
        </div>

        <!-- 社区卡 -->
        <div class="cmd-boxline cmd-boxline4" @click="navigate('/community')">
          <span class="cmd-guild-title">娜迦社区</span>
          <span class="cmd-guild-desc">发帖 · 交友 · 互动</span>
        </div>
      </div>

      <!-- 底部4入口 -->
      <div class="cmd-bottom-nav">
        <button v-for="link in rightLinks" :key="link.id" class="cmd-bottom-item" @click="navigate(link.path)">
          <span class="cmd-bottom-icon">{{ { config: '⚙', community: '◇', security: '⬡', hub: '⬢' }[link.id] }}</span>
          <h1>{{ link.label }}</h1>
          <span>{{ link.desc }}</span>
        </button>
      </div>
    </div>

    <!-- 恢复面板按钮 -->
    <Transition name="show-btn">
      <button v-if="panelsHidden" class="cmd-show-btn" @click="togglePanels" title="显示面板">
        <span>⊙</span>
      </button>
    </Transition>
  </div>
</template>

<style scoped>
/* ═══ 容器 ═══ */
.command-center {
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  width: 100%;
  height: 100%;
  perspective: 600px;
  -webkit-perspective: 600px;
  perspective-origin: center;
  -webkit-perspective-origin: center;
  user-select: none;
  animation: cmd-enter 0.7s cubic-bezier(0.16, 1, 0.3, 1);
  overflow: visible;
  padding: 0.2rem 3% 0;
  position: relative;
}

@keyframes cmd-enter {
  from { opacity: 0; transform: scale(0.98); }
  to { opacity: 1; transform: scale(1); }
}

/* ═══ 面板容器 ═══ */
.cmd-panel {
  height: 92%;
  display: flex;
  flex-direction: column;
  transition: transform 0.5s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.5s ease;
  will-change: transform, opacity;
  overflow: hidden;
  background: transparent;
}

.cmd-left {
  width: 28%;
  min-width: 190px;
  transform: rotateY(30deg);
  padding: 0.5rem 0.5rem 0.2rem;
  transform-origin: center left;
}

.cmd-right {
  width: 32%;
  min-width: 230px;
  transform: rotateY(-30deg);
  padding: 0.5rem 0.5rem 0.2rem;
  transform-origin: center right;
}

/* ═══ 隐藏/显示 ═══ */
.panel-hidden {
  opacity: 0;
  pointer-events: none;
  transform: rotateY(50deg) scale(0.95) !important;
}

.cmd-right.panel-hidden {
  transform: rotateY(-50deg) scale(0.95) !important;
}

/* 恢复显示按钮 */
.cmd-show-btn {
  position: fixed;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 100;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 173, 181, 0.15);
  border: 1px solid rgba(0, 255, 245, 0.25);
  cursor: pointer;
  transition: all 0.4s ease;
  color: rgba(0, 255, 245, 0.55);
  font-size: 1rem;
  font-family: inherit;
  user-select: none;
}

.cmd-show-btn:hover {
  background: rgba(0, 173, 181, 0.3);
  border-color: rgba(0, 255, 245, 0.5);
  color: rgba(0, 255, 245, 0.85);
  transform: translateY(-50%) scale(1.1);
  box-shadow: 0 0 16px rgba(0, 255, 245, 0.15);
}

.show-btn-enter-active,
.show-btn-leave-active {
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}
.show-btn-enter-from,
.show-btn-leave-to {
  opacity: 0;
  transform: translateY(-50%) translateX(-20px);
}

/* ═══ 左面板: 顶部 (固定高度) ═══ */
.cmd-top {
  flex-shrink: 0;
  padding-bottom: 0.2rem;
}

.cmd-level {
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: all 0.5s ease;
}

.cmd-level:hover {
  letter-spacing: 0.15em;
  background: rgba(0, 173, 181, 0.06);
  border-radius: 2px;
}

.cmd-level-head {
  display: flex;
  align-items: baseline;
  gap: 0.3rem;
}

.cmd-level-label {
  color: rgba(228, 236, 240, 0.45);
  font-size: clamp(0.45rem, 1.2vw, 0.6rem);
  font-family: 'Noto Sans SC', sans-serif;
  transition: color 0.4s;
}

.cmd-level:hover .cmd-level-label {
  color: rgba(0, 255, 245, 0.4);
}

.cmd-level-val {
  color: #E4ECF0;
  font-size: clamp(1.2rem, 2.5vw, 1.8rem);
  font-weight: 700;
  font-family: 'Noto Serif SC', serif;
  line-height: 1;
  transition: color 0.4s, text-shadow 0.4s;
}

.cmd-level:hover .cmd-level-val {
  text-shadow: 0 0 12px rgba(0, 255, 245, 0.25);
}

.cmd-level-bar {
  width: 28%;
  height: 3px;
  background: linear-gradient(90deg, rgba(0, 255, 245, 0.4) 50%, rgba(57, 62, 70, 0.4) 50%);
  margin-top: 0.15rem;
  transition: width 0.5s ease;
}

.cmd-level:hover .cmd-level-bar {
  width: 40%;
}

.cmd-level-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(0, 255, 245, 0.55), rgba(0, 173, 181, 0.7));
  transition: width 0.6s ease;
  box-shadow: 0 0 4px rgba(0, 255, 245, 0.3);
}

.cmd-name {
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: all 0.4s ease;
}

.cmd-name-main {
  color: #E4ECF0;
  font-size: clamp(1rem, 2.2vw, 1.3rem);
  font-weight: 700;
  font-family: 'Noto Serif SC', serif;
  letter-spacing: 0.1em;
  transition: letter-spacing 0.8s, color 0.5s, text-shadow 0.5s;
  line-height: 1.3;
}

.cmd-name:hover .cmd-name-main {
  letter-spacing: 0.3em;
  color: rgba(0, 255, 245, 0.9);
  text-shadow: 0 0 15px rgba(0, 255, 245, 0.3);
}

.cmd-name-sub {
  color: rgba(0, 173, 181, 0.5);
  font-size: clamp(0.4rem, 0.9vw, 0.55rem);
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.06em;
  transition: letter-spacing 0.5s, color 0.4s;
}

.cmd-name:hover .cmd-name-sub {
  letter-spacing: 0.18em;
  color: rgba(0, 255, 245, 0.6);
}

/* ═══ 左面板: 中间 (弹性填充) ═══ */
.cmd-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 0.3rem;
  min-height: 0;
  overflow: hidden;
}

.cmd-toggle-row {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  flex-shrink: 0;
}

.cmd-toggle-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.4s ease;
  flex-shrink: 0;
  color: rgba(0, 173, 181, 0.3);
  font-size: 0.85rem;
  font-family: inherit;
}

.cmd-toggle-btn:hover {
  background: rgba(0, 173, 181, 0.12);
  color: rgba(0, 255, 245, 0.65);
  transform: skewX(-8deg);
}

.cmd-toggle-icon {
  display: block;
  transition: transform 0.4s ease;
}

.cmd-toggle-btn:hover .cmd-toggle-icon {
  transform: scale(1.2);
}

.cmd-music {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  cursor: pointer;
  transition: all 0.5s ease;
  padding: 0.1rem 0.15rem;
  margin-left: 0.5rem;
  flex-shrink: 0;
}

.cmd-music:hover {
  background: rgba(0, 173, 181, 0.08);
}

.cmd-music-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(0, 255, 245, 0.3);
  font-size: 0.9rem;
  flex-shrink: 0;
  transition: all 0.5s ease;
}

.cmd-music-icon.playing {
  color: rgba(0, 255, 245, 0.6);
  animation: music-pulse 1.5s ease-in-out infinite;
}

@keyframes music-pulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.15); opacity: 1; }
}

.cmd-music-scroll {
  overflow: hidden;
  flex: 1;
}

.cmd-music-text {
  color: rgba(228, 236, 240, 0.55);
  font-size: clamp(0.5rem, 1vw, 0.6rem);
  font-weight: bold;
  white-space: nowrap;
  display: block;
  animation: music-scroll 6s linear infinite;
}

@keyframes music-scroll {
  0% { transform: translateX(100%); }
  100% { transform: translateX(-120%); }
}

/* 导航卡 */
.cmd-nav {
  display: flex;
  gap: 0.3rem;
  flex-shrink: 0;
}

.cmd-nav-card {
  flex: 1;
  aspect-ratio: 1.05;
  min-height: 60px;
  max-height: 90px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  padding: 0.35rem;
  background: rgba(34, 40, 49, 0.55);
  border: 1px solid rgba(0, 173, 181, 0.1);
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  font-family: inherit;
  color: inherit;
  overflow: hidden;
  position: relative;
  transform: rotateX(3deg) rotateY(-5deg);
  box-shadow:
    2px 4px 12px rgba(0, 0, 0, 0.3),
    0 1px 0 rgba(0, 173, 181, 0.06);
}

.cmd-nav-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(0, 255, 245, 0.06), transparent 60%);
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
}

.cmd-nav-card:hover {
  background: rgba(0, 173, 181, 0.18);
  transform: rotateX(1deg) rotateY(-8deg) scale(1.04) translateY(-3px);
  border-color: rgba(0, 255, 245, 0.3);
  box-shadow:
    3px 6px 20px rgba(0, 173, 181, 0.15),
    0 2px 0 rgba(0, 255, 245, 0.12);
}

.cmd-nav-card:active {
  transform: skewX(-5deg) scale(0.98);
  transition: transform 0.1s ease;
}

.cmd-nav-card:hover::before {
  opacity: 1;
}

.cmd-nav-icon {
  color: rgba(0, 255, 245, 0.3);
  font-size: clamp(0.6rem, 1.2vw, 0.8rem);
  margin-bottom: 0.15rem;
  transition: all 0.4s ease;
}

.cmd-nav-card:hover .cmd-nav-icon {
  color: rgba(0, 255, 245, 0.65);
  transform: scale(1.15);
}

.cmd-nav-title {
  color: #E4ECF0;
  font-size: clamp(0.7rem, 1.4vw, 0.9rem);
  font-weight: 700;
  margin-bottom: 0.25rem;
  transition: color 0.3s, text-shadow 0.3s;
}

.cmd-nav-card:hover .cmd-nav-title {
  text-shadow: 0 0 8px rgba(0, 255, 245, 0.2);
}

.cmd-nav-desc {
  color: rgba(228, 236, 240, 0.3);
  font-size: clamp(0.35rem, 0.7vw, 0.45rem);
  transition: color 0.3s;
}

.cmd-nav-card:hover .cmd-nav-desc {
  color: rgba(228, 236, 240, 0.55);
}

/* ═══ 左面板底部 (固定高度) ═══ */
.cmd-bottom-area {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding-top: 0.3rem;
}

/* Banner 图片轮播 */
.cmd-banner {
  display: flex;
  flex-direction: column;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(0, 173, 181, 0.04);
  flex-shrink: 0;
}

.cmd-banner:hover {
  border-color: rgba(0, 255, 245, 0.12);
}

.cmd-banner:hover .cmd-banner-img {
  filter: brightness(1.15);
}

.cmd-banner-track {
  width: 100%;
  aspect-ratio: 2.8 / 1;
  overflow: hidden;
  background: rgba(34, 40, 49, 0.4);
  position: relative;
}

.cmd-banner-slide {
  width: 100%;
  height: 100%;
}

.cmd-banner-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: filter 0.5s ease;
}

.cmd-banner-label {
  padding: 0.25rem 0.5rem;
  background: rgba(34, 40, 49, 0.35);
  min-height: 1.4em;
  display: flex;
  align-items: center;
}

.cmd-banner-text {
  color: rgba(0, 255, 245, 0.5);
  font-size: clamp(0.45rem, 0.9vw, 0.55rem);
  font-weight: 600;
  letter-spacing: 0.04em;
}

/* 轮播滑动动画 */
.banner-slide-enter-active {
  transition: all 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}
.banner-slide-leave-active {
  transition: all 0.5s cubic-bezier(0.22, 1, 0.36, 1);
  position: absolute;
}
.banner-slide-enter-from {
  opacity: 0;
  transform: translateX(30px);
}
.banner-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.banner-fade-enter-active,
.banner-fade-leave-active {
  transition: all 0.3s ease;
}
.banner-fade-enter-from,
.banner-fade-leave-to {
  opacity: 0;
}

/* 聊天区 */
.cmd-chat {
  display: flex;
  align-items: flex-start;
  background: rgba(34, 40, 49, 0.25);
  border: 1px solid rgba(0, 173, 181, 0.03);
  cursor: pointer;
  position: relative;
  flex-shrink: 0;
  transition: background 0.4s, border-color 0.4s;
}

.cmd-chat:hover {
  background: rgba(34, 40, 49, 0.4);
  border-color: rgba(0, 255, 245, 0.08);
}

.cmd-chat-icon {
  width: 28px;
  min-height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(0, 255, 245, 0.35);
  font-size: 0.75rem;
  flex-shrink: 0;
  transition: all 0.4s ease;
}

.cmd-chat-icon:hover {
  background: rgba(0, 173, 181, 0.12);
  color: rgba(0, 255, 245, 0.65);
}

.cmd-chat-text {
  flex: 1;
  max-height: 1.4em;
  overflow: hidden;
  padding: 0.15rem 0.5rem 0 0;
  transition: all 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}

.cmd-chat-line {
  display: block;
  color: rgba(228, 236, 240, 0.6);
  font-size: clamp(0.4rem, 0.85vw, 0.5rem);
  line-height: 1.4em;
}

.cmd-chat.expanded .cmd-chat-text {
  max-height: none;
  padding: 0.5rem;
  background: rgba(0, 0, 0, 0.5);
  position: relative;
  bottom: 140px;
  border: 1px solid rgba(0, 255, 245, 0.08);
}

/* ═══ 右面板: 资源栏 (固定高度) ═══ */
.cmd-resources {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  gap: 0.25rem;
  margin-bottom: 0.25rem;
}

.cmd-res-item {
  display: flex;
  align-items: center;
  height: clamp(24px, 3.5vh, 30px);
  flex: 1;
  background: rgba(34, 40, 49, 0.55);
  border: 1px solid rgba(0, 173, 181, 0.08);
  padding: 0 0.25rem;
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.22, 1, 0.36, 1);
  overflow: hidden;
  position: relative;
  transform: rotateX(1deg) rotateY(-3deg);
  box-shadow: 1px 2px 6px rgba(0, 0, 0, 0.25);
}

.cmd-res-item:hover {
  background: rgba(0, 173, 181, 0.14);
  border-color: rgba(0, 255, 245, 0.25);
  transform: rotateX(0deg) rotateY(-5deg) scale(1.03);
  box-shadow: 1px 3px 12px rgba(0, 173, 181, 0.12);
}

.cmd-res-item:active {
  transform: rotateX(1deg) rotateY(-3deg) scale(0.98);
  transition: transform 0.1s ease;
}

.cmd-res-icon {
  width: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(0, 255, 245, 0.4);
  font-size: 0.75rem;
  flex-shrink: 0;
  transition: all 0.4s ease;
}

.cmd-res-item:hover .cmd-res-icon {
  color: rgba(0, 255, 245, 0.65);
  transform: scale(1.15);
}

.cmd-res-val {
  flex: 1;
  color: #E4ECF0;
  font-size: clamp(0.65rem, 1.2vw, 0.8rem);
  font-family: 'JetBrains Mono', monospace;
  padding: 0 0.3rem;
  min-width: 0;
  transition: color 0.4s, text-shadow 0.4s;
}

.cmd-res-item:hover .cmd-res-val {
  text-shadow: 0 0 6px rgba(0, 255, 245, 0.2);
}

.time-font {
  font-size: clamp(0.5rem, 1vw, 0.65rem) !important;
}

.cmd-res-plus {
  width: 22px;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 173, 181, 0.18);
  color: #E4ECF0;
  font-size: 1.2rem;
  font-weight: 700;
  flex-shrink: 0;
  transition: all 0.4s ease;
}

.cmd-res-item:hover .cmd-res-plus {
  background: rgba(0, 173, 181, 0.35);
}

/* ═══ 右面板: 中间内容 (弹性) ═══ */
.cmd-right-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-height: 0;
  overflow: hidden;
}

/* 时间行 */
.cmd-time-row {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 0.05rem 0.4rem;
  gap: 0.3rem;
}

.cmd-time-icon {
  font-size: 0.9rem;
  color: rgba(0, 255, 245, 0.2);
  cursor: pointer;
  transition: all 0.4s ease;
  flex-shrink: 0;
}

.cmd-time-icon.active {
  color: rgba(0, 255, 245, 0.45);
}

.cmd-time-icon:hover {
  transform: skewX(-10deg) scale(1.1);
  color: rgba(0, 255, 245, 0.55);
}

.cmd-time-val {
  color: rgba(228, 236, 240, 0.75);
  font-size: clamp(0.8rem, 1.5vw, 1rem);
  font-family: 'JetBrains Mono', monospace;
  margin-right: auto;
  cursor: pointer;
  transition: all 0.5s ease;
}

.cmd-time-val:hover {
  color: rgba(0, 255, 245, 0.85);
  font-size: clamp(1rem, 2vw, 1.4rem);
  text-shadow: 0 0 10px rgba(0, 255, 245, 0.25);
}

.cmd-time-icons {
  display: flex;
  gap: 0.3rem;
}

.cmd-time-icn {
  width: 28px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  color: rgba(0, 173, 181, 0.25);
  cursor: pointer;
  transition: all 0.4s ease;
}

.cmd-time-icn:hover {
  color: rgba(0, 255, 245, 0.65);
  transform: skewX(-8deg) scale(1.1);
}

.cmd-hide-icn:hover {
  color: rgba(255, 150, 150, 0.65);
  transform: skewX(8deg) scale(1.1);
}

/* ── boxline 通用 ── */
.cmd-boxline {
  display: flex;
  align-items: center;
  min-height: 0;
}

/* boxline1: 看板娘卡 (flex: 3.5) */
.cmd-boxline1 {
  flex: 3.5;
  justify-content: center;
  gap: 0.25rem;
  overflow: hidden;
}

.cmd-portrait {
  width: 18%;
  min-width: 70px;
  max-width: 100px;
  height: 100%;
  position: relative;
  cursor: pointer;
  overflow: hidden;
  background: rgba(34, 40, 49, 0.3);
  border: 1px solid rgba(0, 173, 181, 0.06);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.4s;
}

.cmd-portrait-avatar {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(0, 173, 181, 0.12), rgba(0, 255, 245, 0.04));
  transition: transform 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}

.cmd-portrait:hover .cmd-portrait-avatar {
  transform: scale(1.08) rotateY(15deg);
}

.cmd-portrait-char {
  font-family: 'Noto Serif SC', serif;
  font-size: clamp(1.5rem, 3vw, 2rem);
  font-weight: 700;
  color: rgba(0, 255, 245, 0.65);
  text-shadow: 0 0 12px rgba(0, 255, 245, 0.25);
  transition: all 0.5s ease;
}

.cmd-portrait:hover .cmd-portrait-char {
  color: rgba(0, 255, 245, 0.9);
  text-shadow: 0 0 20px rgba(0, 255, 245, 0.4);
}

.cmd-portrait-gloss {
  position: absolute;
  top: -15%;
  left: -10%;
  width: 4px;
  height: 130%;
  background: rgba(255, 255, 255, 0.18);
  transform: skewX(-20deg);
  box-shadow: 0 0 20px rgba(255, 255, 255, 0.2);
  z-index: 1;
  filter: blur(4px);
  animation: gloss-sweep 2.5s ease-in-out infinite;
  pointer-events: none;
}

@keyframes gloss-sweep {
  0% { left: -10%; }
  50% { left: 130%; }
  100% { left: 130%; }
}

.cmd-portrait:not(:hover) :deep(canvas) {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain;
}

.cmd-portrait:hover {
  background: rgba(0, 173, 181, 0.08);
}

.cmd-battle-info {
  flex: 1;
  height: 100%;
  display: flex;
  background: rgba(34, 40, 49, 0.55);
  border: 1px solid rgba(0, 173, 181, 0.08);
  padding: 0.25rem 0.4rem;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  overflow: hidden;
  transform: rotateX(2deg) rotateY(-4deg);
  box-shadow:
    2px 3px 10px rgba(0, 0, 0, 0.3),
    0 1px 0 rgba(0, 173, 181, 0.06);
}

.cmd-battle-info:hover {
  background: rgba(0, 173, 181, 0.14);
  border-color: rgba(0, 255, 245, 0.25);
  transform: rotateX(1deg) rotateY(-7deg) scale(1.02);
  box-shadow:
    3px 5px 18px rgba(0, 173, 181, 0.12),
    0 2px 0 rgba(0, 255, 245, 0.12);
}

.cmd-battle-info:active {
  transform: rotateX(2deg) rotateY(-4deg) scale(0.98);
  transition: transform 0.1s ease;
}

.cmd-battle-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.cmd-battle-left h1 {
  color: #E4ECF0;
  font-size: clamp(1rem, 2vw, 1.4rem);
  font-weight: 700;
  line-height: 1.2;
  margin: 0;
  transition: color 0.3s, text-shadow 0.3s;
}

.cmd-battle-info:hover .cmd-battle-left h1 {
  text-shadow: 0 0 8px rgba(0, 255, 245, 0.2);
}

.cmd-battle-tip {
  color: rgba(228, 236, 240, 0.45);
  font-size: clamp(0.45rem, 0.9vw, 0.55rem);
  transition: color 0.3s;
}

.cmd-battle-info:hover .cmd-battle-tip {
  color: rgba(228, 236, 240, 0.65);
}

.cmd-battle-nd {
  font-size: clamp(0.4rem, 0.8vw, 0.5rem);
  transition: all 0.4s ease;
}

.cmd-battle-right {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: clamp(36px, 9%, 48px);
  height: clamp(36px, 9%, 48px);
  border: 2px solid rgba(0, 255, 245, 0.2);
  border-radius: 50%;
  flex-shrink: 0;
  transition: all 0.4s ease;
}

.cmd-battle-info:hover .cmd-battle-right {
  border-color: rgba(0, 255, 245, 0.45);
  box-shadow: 0 0 8px rgba(0, 255, 245, 0.15);
}

.cmd-battle-pct {
  color: #E4ECF0;
  font-size: clamp(0.7rem, 1.3vw, 0.9rem);
  font-weight: 700;
  margin: 0;
  line-height: 1;
}

.cmd-battle-right span {
  color: rgba(228, 236, 240, 0.3);
  font-size: clamp(0.35rem, 0.6vw, 0.45rem);
  transition: color 0.3s;
}

.cmd-battle-info:hover .cmd-battle-right span {
  color: rgba(228, 236, 240, 0.6);
}

.cmd-mascot {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 10%;
  min-width: 35px;
  max-width: 50px;
  height: 100%;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  gap: 0.1rem;
  flex-shrink: 0;
}

.cmd-mascot:hover {
  transform: scale(1.15);
}

.cmd-mascot-icon {
  color: rgba(0, 255, 245, 0.35);
  font-size: clamp(0.8rem, 1.5vw, 1.1rem);
  transition: all 0.4s ease;
}

.cmd-mascot:hover .cmd-mascot-icon {
  color: rgba(0, 255, 245, 0.7);
}

.cmd-mascot-label {
  color: rgba(228, 236, 240, 0.4);
  font-size: clamp(0.35rem, 0.6vw, 0.4rem);
  font-weight: bold;
  transition: color 0.3s;
}

.cmd-mascot:hover .cmd-mascot-label {
  color: rgba(228, 236, 240, 0.7);
}

.cmd-mascot-val {
  color: rgba(0, 255, 245, 0.4);
  font-size: clamp(0.35rem, 0.6vw, 0.4rem);
  font-family: 'JetBrains Mono', monospace;
  transition: color 0.3s;
}

.cmd-mascot:hover .cmd-mascot-val {
  color: rgba(0, 255, 245, 0.8);
}

/* boxline2: 任务卡 (flex: 1.3) */
.cmd-boxline2 {
  flex: 1.3;
  justify-content: center;
  gap: 0.25rem;
  overflow: hidden;
}

.cmd-quest {
  flex: 1;
  height: 100%;
  display: flex;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  overflow: hidden;
  transform: rotateX(2deg) rotateY(-3deg);
  box-shadow: 1px 2px 8px rgba(0, 0, 0, 0.25);
}

.cmd-quest:hover {
  background: rgba(0, 173, 181, 0.1);
  transform: rotateX(1deg) rotateY(-6deg) scale(1.02);
  box-shadow: 2px 4px 14px rgba(0, 173, 181, 0.1);
}

.cmd-quest:active {
  transform: rotateX(2deg) rotateY(-3deg) scale(0.98);
  transition: transform 0.1s ease;
}

.cmd-quest-left {
  width: 25%;
  background: rgba(0, 173, 181, 0.08);
  padding: 0.25rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  transition: background 0.4s;
}

.cmd-quest:hover .cmd-quest-left {
  background: rgba(0, 173, 181, 0.16);
}

.cmd-quest-left h2 {
  color: #E4ECF0;
  font-size: clamp(0.7rem, 1.3vw, 0.85rem);
  font-weight: 700;
  margin: 0;
}

.cmd-quest-left span {
  color: rgba(228, 236, 240, 0.3);
  font-size: clamp(0.35rem, 0.7vw, 0.45rem);
}

.cmd-quest:hover .cmd-quest-left span {
  color: rgba(228, 236, 240, 0.55);
}

.cmd-quest-right {
  flex: 1;
  background: rgba(34, 40, 49, 0.55);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0.4rem;
  position: relative;
  overflow: hidden;
  transition: background 0.4s;
}

.cmd-quest:hover .cmd-quest-right {
  background: rgba(34, 40, 49, 0.7);
}

.cmd-quest-right p {
  color: rgba(228, 236, 240, 0.5);
  font-size: clamp(0.4rem, 0.8vw, 0.5rem);
  font-weight: bold;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.3s;
}

.cmd-quest:hover .cmd-quest-right p {
  color: rgba(228, 236, 240, 0.75);
}

.cmd-quest-check {
  color: rgba(0, 255, 245, 0.4);
  font-size: clamp(0.7rem, 1.2vw, 0.85rem);
  position: absolute;
  right: 4px;
  bottom: 1px;
  flex-shrink: 0;
  transition: all 0.4s ease;
}

.cmd-quest:hover .cmd-quest-check {
  color: rgba(0, 255, 245, 0.75);
  transform: scale(1.2);
}

.cmd-quest-spacer {
  width: 12%;
  min-width: 45px;
  max-width: 70px;
  height: 60%;
  background: rgba(34, 40, 49, 0.2);
  border: 1px solid rgba(0, 173, 181, 0.02);
  align-self: flex-end;
  flex-shrink: 0;
  transition: background 0.4s;
}

/* boxline3: 功能区 (flex: 1.8) */
.cmd-boxline3 {
  flex: 1.8;
  justify-content: center;
  gap: 0.25rem;
  overflow: hidden;
}

.cmd-feat-card {
  flex: 1;
  height: 100%;
  background: rgba(34, 40, 49, 0.55);
  border: 1px solid rgba(0, 173, 181, 0.08);
  padding: 0.3rem;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  position: relative;
  font-family: inherit;
  color: inherit;
  text-align: left;
  overflow: hidden;
  transform: rotateX(3deg) rotateY(-4deg);
  box-shadow:
    2px 4px 10px rgba(0, 0, 0, 0.3),
    0 1px 0 rgba(0, 173, 181, 0.06);
}

.cmd-feat-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(0, 255, 245, 0.05), transparent 50%);
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
}

.cmd-feat-card:hover {
  background: rgba(0, 173, 181, 0.15);
  transform: rotateX(1deg) rotateY(-7deg) scale(1.03) translateY(-3px);
  border-color: rgba(0, 255, 245, 0.28);
  box-shadow:
    3px 6px 18px rgba(0, 173, 181, 0.12),
    0 2px 0 rgba(0, 255, 245, 0.12);
}

.cmd-feat-card:active {
  transform: rotateX(3deg) rotateY(-4deg) scale(0.98);
  transition: transform 0.1s ease;
}

.cmd-feat-card:hover::before { opacity: 1; }
.cmd-feat-card:hover h1 { color: #E4ECF0; text-shadow: 0 0 10px rgba(0, 255, 245, 0.25); }
.cmd-feat-card:hover span { color: rgba(228, 236, 240, 0.65); }

.cmd-feat-card h1 {
  color: #E4ECF0;
  font-size: clamp(0.65rem, 1.3vw, 0.85rem);
  font-weight: 700;
  margin: 0 0 0.1rem 0;
  transition: color 0.3s, text-shadow 0.3s;
}

.cmd-feat-card span {
  color: rgba(228, 236, 240, 0.3);
  font-size: clamp(0.35rem, 0.7vw, 0.45rem);
  transition: color 0.3s;
}

.cmd-feat-badge {
  position: absolute;
  right: 4px;
  top: 4px;
  background: rgba(0, 255, 245, 0.6);
  color: #111;
  font-size: clamp(0.3rem, 0.5vw, 0.35rem);
  font-weight: bold;
  padding: 1px 4px;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.cmd-feat-card:hover .cmd-feat-badge {
  background: rgba(0, 255, 245, 0.8);
  transform: scale(1.1);
}

.cmd-feat-spacer {
  width: 10%;
  min-width: 40px;
  max-width: 60px;
  height: 100%;
  background: rgba(34, 40, 49, 0.2);
  border: 1px solid rgba(0, 173, 181, 0.02);
  flex-shrink: 0;
}

/* boxline4: 社区 (flex: 1) */
.cmd-boxline4 {
  flex: 1;
  width: 70%;
  background: rgba(34, 40, 49, 0.5);
  border: 1px solid rgba(0, 173, 181, 0.08);
  padding: 0 0.6rem;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  align-self: flex-end;
  overflow: hidden;
}

.cmd-boxline4:hover {
  background: rgba(0, 173, 181, 0.14);
  border-color: rgba(0, 255, 245, 0.2);
  width: 100%;
  box-shadow: 0 0 14px rgba(0, 173, 181, 0.08);
}

.cmd-guild-title {
  color: #E4ECF0;
  font-size: clamp(0.6rem, 1.1vw, 0.7rem);
  font-weight: 700;
  transition: color 0.3s, text-shadow 0.3s;
}

.cmd-boxline4:hover .cmd-guild-title {
  text-shadow: 0 0 10px rgba(0, 255, 245, 0.3);
}

.cmd-guild-desc {
  color: rgba(228, 236, 240, 0.3);
  font-size: clamp(0.4rem, 0.75vw, 0.5rem);
  transition: color 0.3s;
}

.cmd-boxline4:hover .cmd-guild-desc {
  color: rgba(228, 236, 240, 0.65);
}

/* ═══ 底部导航 (固定高度) ═══ */
.cmd-bottom-nav {
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.15rem;
  padding-top: 0.2rem;
}

.cmd-bottom-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0.3rem 0.15rem;
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.22, 1, 0.36, 1);
  background: rgba(34, 40, 49, 0.4);
  border: 1px solid rgba(0, 173, 181, 0.06);
  font-family: inherit;
  color: inherit;
  overflow: hidden;
  gap: 0.08rem;
  transform: rotateX(2deg) rotateY(-3deg);
  box-shadow: 1px 2px 6px rgba(0, 0, 0, 0.25);
}

.cmd-bottom-item:hover {
  background: rgba(0, 173, 181, 0.15);
  border-color: rgba(0, 255, 245, 0.2);
  box-shadow: 3px 5px 16px rgba(0, 0, 0, 0.35), 0 0 10px rgba(0, 173, 181, 0.1);
  transform: rotateX(1deg) rotateY(-6deg) translateY(-3px);
}

.cmd-bottom-item:active {
  transform: rotateX(2deg) rotateY(-3deg) scale(0.97);
  transition: transform 0.1s ease;
}

.cmd-bottom-item:hover h1 {
  text-shadow: 0 0 12px rgba(0, 255, 245, 0.35);
}

.cmd-bottom-icon {
  color: rgba(0, 255, 245, 0.25);
  font-size: clamp(0.5rem, 0.9vw, 0.6rem);
  transition: all 0.4s ease;
}

.cmd-bottom-item:hover .cmd-bottom-icon {
  color: rgba(0, 255, 245, 0.6);
  transform: scale(1.1);
}

.cmd-bottom-item h1 {
  color: #E4ECF0;
  font-size: clamp(0.5rem, 1vw, 0.6rem);
  font-weight: 700;
  margin: 0;
  transition: text-shadow 0.4s;
}

.cmd-bottom-item span {
  color: rgba(228, 236, 240, 0.3);
  font-size: clamp(0.35rem, 0.7vw, 0.45rem);
  transition: color 0.4s;
}

.cmd-bottom-item:hover span {
  color: rgba(228, 236, 240, 0.65);
}
</style>
