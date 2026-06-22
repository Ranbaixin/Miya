<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import API from '@/api/core'

const router = useRouter()

const backendOnline = ref(false)
const miyaPersona = ref('默认')
const soulActive = ref(87)
const currentTime = ref('')
const miyaThought = ref('佳，今天的星空很美呢...')
const currentBgm = ref('快乐的小曲')
const miyaPlatforms = ref(3)
let timer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  try {
    const health = await API.health()
    backendOnline.value = health.status === 'healthy'
    const persona = await API.getCurrentPersona()
    miyaPersona.value = persona?.persona?.name || persona?.persona?.id || '默认'
    soulActive.value = persona?.soul?.activity || 87
  } catch { backendOnline.value = false }
  updateTime()
  timer = setInterval(updateTime, 10000)
})

onUnmounted(() => { if (timer) clearInterval(timer) })

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
  { id: 'screen', label: '视觉', desc: '截图', path: '/screen' },
]

const banners = ['弥娅 v2.0 · 全新看板娘上线', '新增记忆星河 3D 可视化', '安全中心 · 漏洞扫描引擎']
const bannerIdx = ref(0)
const bannerText = ref(banners[0])
let bannerTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  bannerTimer = setInterval(() => {
    bannerIdx.value = (bannerIdx.value + 1) % banners.length
    bannerText.value = banners[bannerIdx.value]!
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
    <div class="cmd-panel cmd-left">
      <div class="cmd-top">
        <div class="cmd-level">
          <div class="cmd-level-head">
            <span class="cmd-level-label">灵魂活跃度</span>
            <span class="cmd-level-val">{{ soulActive }}</span>
          </div>
          <div class="cmd-level-bar">
            <div class="cmd-level-fill" :style="{ width: `${soulActive}%` }" />
          </div>
        </div>
        <div class="cmd-name">
          <span class="cmd-name-main">弥娅</span>
          <span class="cmd-name-sub">MIYA · {{ miyaPersona }}</span>
        </div>
      </div>

      <div class="cmd-center">
        <div class="cmd-music">
          <span class="cmd-music-icon">♪</span>
          <div class="cmd-music-scroll">
            <span class="cmd-music-text">正在播放 — {{ currentBgm }}</span>
          </div>
        </div>

        <div class="cmd-nav">
          <button
            v-for="card in leftCards" :key="card.id"
            class="cmd-nav-card"
            @click="navigate(card.path)"
          >
            <span class="cmd-nav-title">{{ card.label }}</span>
            <span class="cmd-nav-desc">{{ card.desc }}</span>
          </button>
        </div>
      </div>

      <div class="cmd-bottom-area">
        <div class="cmd-banner" @click="navigate('/chat')">
          <Transition name="banner-fade" mode="out-in">
            <span :key="bannerText" class="cmd-banner-text">{{ bannerText }}</span>
          </Transition>
        </div>
        <div class="cmd-chat" :class="{ expanded: chatExpanded }" @click="toggleChat">
          <div class="cmd-chat-icon">💬</div>
          <div class="cmd-chat-text">
            <span class="cmd-chat-line">✦「{{ miyaThought }}」</span>
            <span class="cmd-chat-line">✨ 佳，有什么需要帮忙的吗？</span>
            <span class="cmd-chat-line">💭 今天的系统状态一切正常哦~</span>
            <span class="cmd-chat-line">🎵 BGM: {{ currentBgm }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ 右面板 ═══ -->
    <div class="cmd-panel cmd-right">
      <div class="cmd-resources">
        <div class="cmd-res-item">
          <span class="cmd-res-icon">◆</span>
          <span class="cmd-res-val">{{ soulActive }}</span>
          <span class="cmd-res-plus">+</span>
        </div>
        <div class="cmd-res-item">
          <span class="cmd-res-icon">⬢</span>
          <span class="cmd-res-val">{{ miyaPlatforms }}</span>
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
          <span class="cmd-time-icon">🔋</span>
          <span class="cmd-time-val">{{ currentTime }}</span>
          <div class="cmd-time-icons">
            <span class="cmd-time-icn" title="消息" @click="navigate('/chat')">✉</span>
            <span class="cmd-time-icn" title="设置" @click="navigate('/config')">⚙</span>
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
              <span class="cmd-battle-nd">弥娅在线</span>
            </div>
            <div class="cmd-battle-right">
              <h2 class="cmd-battle-pct">∞</h2>
              <span>陪伴</span>
            </div>
          </div>
          <div class="cmd-mascot" @click="navigate('/mind')">
            <span class="cmd-mascot-icon">◆</span>
            <span class="cmd-mascot-label">记忆</span>
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
          <h1>{{ link.label }}</h1>
          <span>{{ link.desc }}</span>
        </button>
      </div>
    </div>
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
  overflow: hidden;
  padding: 0 5%;
}

@keyframes cmd-enter {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ═══ 面板容器 ═══ */
.cmd-panel {
  height: 90%;
  display: flex;
  flex-direction: column;
  transition: transform 0.3s ease-out;
  will-change: transform;
  overflow: hidden;
  background: transparent; /* 去掉自带背景 */
}

.cmd-left {
  width: 28%;
  min-width: 200px;
  transform: rotateY(30deg);
  padding: 0.5rem 0.5rem 0.2rem;
}

.cmd-right {
  width: 32%;
  min-width: 240px;
  transform: rotateY(-30deg);
  padding: 0.5rem 0.5rem 0.2rem;
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
  transition: 0.8s;
}

.cmd-level:hover {
  letter-spacing: 0.12em;
  background: rgba(0, 173, 181, 0.08);
}

.cmd-level-head {
  display: flex;
  align-items: baseline;
  gap: 0.3rem;
}

.cmd-level-label {
  color: rgba(228, 236, 240, 0.5);
  font-size: clamp(0.45rem, 1.2vw, 0.6rem);
  font-family: 'Noto Sans SC', sans-serif;
}

.cmd-level-val {
  color: #E4ECF0;
  font-size: clamp(1.2rem, 2.5vw, 1.8rem);
  font-weight: 700;
  font-family: 'Noto Serif SC', serif;
  line-height: 1;
}

.cmd-level-bar {
  width: 28%;
  height: 3px;
  background: linear-gradient(90deg, rgba(0, 255, 245, 0.4) 50%, rgba(57, 62, 70, 0.4) 50%);
  margin-top: 0.15rem;
}

.cmd-level-fill {
  height: 100%;
  background: rgba(0, 255, 245, 0.55);
  transition: width 0.6s ease;
}

.cmd-name {
  display: flex;
  flex-direction: column;
  cursor: pointer;
}

.cmd-name-main {
  color: #E4ECF0;
  font-size: clamp(1rem, 2.2vw, 1.3rem);
  font-weight: 700;
  font-family: 'Noto Serif SC', serif;
  letter-spacing: 0.1em;
  transition: letter-spacing 1s;
  line-height: 1.3;
}

.cmd-name:hover .cmd-name-main {
  letter-spacing: 0.3em;
}

.cmd-name-sub {
  color: rgba(0, 173, 181, 0.5);
  font-size: clamp(0.4rem, 0.9vw, 0.55rem);
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.06em;
  transition: letter-spacing 0.5s;
}

.cmd-name:hover .cmd-name-sub {
  letter-spacing: 0.15em;
}

/* ═══ 左面板: 中间 (弹性填充) ═══ */
.cmd-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 0.4rem;
  min-height: 0;
  overflow: hidden;
}

.cmd-music {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  cursor: pointer;
  transition: 0.8s;
  padding: 0.15rem 0;
  margin-left: 0.8rem;
  flex-shrink: 0;
}

.cmd-music:hover {
  background: rgba(0, 173, 181, 0.1);
}

.cmd-music-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(0, 255, 245, 0.45);
  font-size: 0.9rem;
  flex-shrink: 0;
  transition: 1.5s;
}

.cmd-music-scroll {
  overflow: hidden;
  flex: 1;
}

.cmd-music-text {
  color: rgba(228, 236, 240, 0.65);
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
  padding: 0.35rem;
  background: rgba(34, 40, 49, 0.4);
  border: 1px solid rgba(0, 173, 181, 0.05);
  cursor: pointer;
  transition: all 0.5s ease;
  font-family: inherit;
  color: inherit;
  overflow: hidden;
}

.cmd-nav-card:hover {
  background: rgba(0, 173, 181, 0.15);
  transform: skewX(-6deg);
}

.cmd-nav-title {
  color: #E4ECF0;
  font-size: clamp(0.7rem, 1.4vw, 0.9rem);
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.cmd-nav-desc {
  color: rgba(228, 236, 240, 0.35);
  font-size: clamp(0.35rem, 0.7vw, 0.45rem);
}

/* ═══ 左面板底部 (固定高度) ═══ */
.cmd-bottom-area {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding-top: 0.3rem;
}

.cmd-banner {
  padding: 0.4rem 0.6rem;
  background: rgba(34, 40, 49, 0.35);
  border: 1px solid rgba(0, 173, 181, 0.05);
  cursor: pointer;
  transition: background 0.4s;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.cmd-banner:hover {
  background: rgba(0, 173, 181, 0.08);
}

.cmd-banner-text {
  color: rgba(0, 255, 245, 0.55);
  font-size: clamp(0.45rem, 0.9vw, 0.55rem);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.banner-fade-enter-active,
.banner-fade-leave-active {
  transition: all 0.4s ease;
}
.banner-fade-enter-from,
.banner-fade-leave-to {
  opacity: 0;
}

/* 聊天区 */
.cmd-chat {
  display: flex;
  align-items: flex-start;
  background: rgba(34, 40, 49, 0.3);
  border: 1px solid rgba(0, 173, 181, 0.03);
  cursor: pointer;
  position: relative;
  flex-shrink: 0;
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
  transition: 0.4s;
}

.cmd-chat-icon:hover {
  background: rgba(0, 173, 181, 0.15);
}

.cmd-chat-text {
  flex: 1;
  max-height: 1.4em;
  overflow: hidden;
  padding: 0.15rem 0.5rem 0 0;
  transition: all 0.5s ease;
}

.cmd-chat-line {
  display: block;
  color: rgba(228, 236, 240, 0.65);
  font-size: clamp(0.4rem, 0.85vw, 0.5rem);
  line-height: 1.35em;
}

.cmd-chat.expanded .cmd-chat-text {
  max-height: none;
  padding-bottom: 0.5rem;
  background: rgba(0, 0, 0, 0.55);
  position: relative;
  bottom: 140px;
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
  background: rgba(34, 40, 49, 0.38);
  border: 1px solid rgba(0, 173, 181, 0.04);
  padding: 0 0.25rem;
  cursor: pointer;
  transition: 0.4s;
  overflow: hidden;
}

.cmd-res-item:hover {
  background: rgba(0, 173, 181, 0.12);
}

.cmd-res-icon {
  width: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(0, 255, 245, 0.45);
  font-size: 0.75rem;
  flex-shrink: 0;
}

.cmd-res-val {
  flex: 1;
  color: #E4ECF0;
  font-size: clamp(0.65rem, 1.2vw, 0.8rem);
  font-family: 'JetBrains Mono', monospace;
  padding: 0 0.3rem;
  min-width: 0;
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
  background: rgba(0, 173, 181, 0.2);
  color: #E4ECF0;
  font-size: 1.2rem;
  font-weight: 700;
  flex-shrink: 0;
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
  color: rgba(0, 255, 245, 0.25);
  cursor: pointer;
  transition: 0.4s;
  flex-shrink: 0;
}

.cmd-time-icon:hover {
  transform: skewX(-10deg);
  color: rgba(0, 255, 245, 0.55);
}

.cmd-time-val {
  color: rgba(228, 236, 240, 0.75);
  font-size: clamp(0.8rem, 1.5vw, 1rem);
  font-family: 'JetBrains Mono', monospace;
  margin-right: auto;
  cursor: pointer;
  transition: 1.5s;
}

.cmd-time-val:hover {
  color: rgba(0, 255, 245, 0.85);
  font-size: clamp(1rem, 2vw, 1.4rem);
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
  color: rgba(0, 173, 181, 0.3);
  cursor: pointer;
  transition: 0.4s;
}

.cmd-time-icn:hover {
  color: rgba(0, 255, 245, 0.65);
  transform: skewX(-8deg) scale(1.1);
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
}

.cmd-portrait-avatar {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(0, 173, 181, 0.15), rgba(0, 255, 245, 0.05));
  transition: transform 0.4s ease;
}

.cmd-portrait:hover .cmd-portrait-avatar {
  transform: scale(1.08);
}

.cmd-portrait-char {
  font-family: 'Noto Serif SC', serif;
  font-size: clamp(1.5rem, 3vw, 2rem);
  font-weight: 700;
  color: rgba(0, 255, 245, 0.7);
  text-shadow: 0 0 12px rgba(0, 255, 245, 0.3);
}

.cmd-portrait-gloss {
  position: absolute;
  top: -15%;
  left: -10%;
  width: 4px;
  height: 130%;
  background: rgba(255, 255, 255, 0.2);
  transform: skewX(-20deg);
  box-shadow: 0 0 20px rgba(255, 255, 255, 0.25);
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

.cmd-portrait :deep(canvas) {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain;
}

.cmd-portrait:hover {
  background: rgba(0, 173, 181, 0.1);
}

.cmd-battle-info {
  flex: 1;
  height: 100%;
  display: flex;
  background: rgba(34, 40, 49, 0.4);
  border: 1px solid rgba(0, 173, 181, 0.05);
  padding: 0.25rem 0.4rem;
  cursor: pointer;
  transition: 0.6s;
  overflow: hidden;
}

.cmd-battle-info:hover {
  background: rgba(0, 173, 181, 0.1);
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
}

.cmd-battle-tip {
  color: rgba(228, 236, 240, 0.45);
  font-size: clamp(0.45rem, 0.9vw, 0.55rem);
}

.cmd-battle-nd {
  color: rgba(0, 255, 245, 0.5);
  font-size: clamp(0.4rem, 0.8vw, 0.5rem);
}

.cmd-battle-right {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: clamp(36px, 9%, 48px);
  height: clamp(36px, 9%, 48px);
  border: 2px solid rgba(0, 255, 245, 0.25);
  border-radius: 50%;
  flex-shrink: 0;
}

.cmd-battle-pct {
  color: #E4ECF0;
  font-size: clamp(0.7rem, 1.3vw, 0.9rem);
  font-weight: 700;
  margin: 0;
  line-height: 1;
}

.cmd-battle-right span {
  color: rgba(228, 236, 240, 0.35);
  font-size: clamp(0.35rem, 0.6vw, 0.45rem);
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
  transition: 0.4s;
  gap: 0.15rem;
  flex-shrink: 0;
}

.cmd-mascot:hover {
  transform: scale(1.15);
}

.cmd-mascot-icon {
  color: rgba(0, 255, 245, 0.4);
  font-size: clamp(0.8rem, 1.5vw, 1.1rem);
}

.cmd-mascot-label {
  color: rgba(228, 236, 240, 0.45);
  font-size: clamp(0.35rem, 0.6vw, 0.4rem);
  font-weight: bold;
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
  transition: 0.6s;
  overflow: hidden;
}

.cmd-quest:hover {
  background: rgba(0, 173, 181, 0.08);
}

.cmd-quest-left {
  width: 25%;
  background: rgba(0, 173, 181, 0.06);
  padding: 0.25rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.cmd-quest-left h2 {
  color: #E4ECF0;
  font-size: clamp(0.7rem, 1.3vw, 0.85rem);
  font-weight: 700;
  margin: 0;
}

.cmd-quest-left span {
  color: rgba(228, 236, 240, 0.35);
  font-size: clamp(0.35rem, 0.7vw, 0.45rem);
}

.cmd-quest-right {
  flex: 1;
  background: rgba(34, 40, 49, 0.38);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0.4rem;
  position: relative;
  overflow: hidden;
}

.cmd-quest-right p {
  color: rgba(228, 236, 240, 0.55);
  font-size: clamp(0.4rem, 0.8vw, 0.5rem);
  font-weight: bold;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cmd-quest-check {
  color: rgba(0, 255, 245, 0.45);
  font-size: clamp(0.7rem, 1.2vw, 0.85rem);
  position: absolute;
  right: 4px;
  bottom: 1px;
  flex-shrink: 0;
}

.cmd-quest-spacer {
  width: 12%;
  min-width: 45px;
  max-width: 70px;
  height: 60%;
  background: rgba(34, 40, 49, 0.25);
  border: 1px solid rgba(0, 173, 181, 0.03);
  align-self: flex-end;
  flex-shrink: 0;
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
  background: rgba(34, 40, 49, 0.38);
  border: 1px solid rgba(0, 173, 181, 0.04);
  padding: 0.3rem;
  cursor: pointer;
  transition: 0.6s;
  position: relative;
  font-family: inherit;
  color: inherit;
  text-align: left;
  overflow: hidden;
}

.cmd-feat-card:hover {
  background: rgba(0, 173, 181, 0.1);
  transform: rotateY(4deg);
  text-shadow: 0 0 6px rgba(0, 255, 245, 0.25);
}
.cmd-feat-card:hover h1 { color: #E4ECF0; }
.cmd-feat-card:hover span { color: rgba(228, 236, 240, 0.65); }

.cmd-feat-card h1 {
  color: #E4ECF0;
  font-size: clamp(0.65rem, 1.3vw, 0.85rem);
  font-weight: 700;
  margin: 0 0 0.1rem 0;
}

.cmd-feat-card span {
  color: rgba(228, 236, 240, 0.35);
  font-size: clamp(0.35rem, 0.7vw, 0.45rem);
}

.cmd-feat-badge {
  position: absolute;
  right: 4px;
  top: 4px;
  background: rgba(0, 255, 245, 0.65);
  color: #111;
  font-size: clamp(0.3rem, 0.5vw, 0.35rem);
  font-weight: bold;
  padding: 1px 4px;
  border-radius: 2px;
}

.cmd-feat-spacer {
  width: 10%;
  min-width: 40px;
  max-width: 60px;
  height: 100%;
  background: rgba(34, 40, 49, 0.25);
  border: 1px solid rgba(0, 173, 181, 0.03);
  flex-shrink: 0;
}

/* boxline4: 社区 (flex: 1) */
.cmd-boxline4 {
  flex: 1;
  width: 70%;
  background: rgba(34, 40, 49, 0.3);
  border: 1px solid rgba(0, 173, 181, 0.04);
  padding: 0 0.6rem;
  cursor: pointer;
  transition: 0.5s;
  display: flex;
  align-items: center;
  justify-content: space-between;
  align-self: flex-end;
  overflow: hidden;
}

.cmd-boxline4:hover {
  background: rgba(0, 173, 181, 0.1);
  width: 100%;
}

.cmd-guild-title {
  color: #E4ECF0;
  font-size: clamp(0.6rem, 1.1vw, 0.7rem);
  font-weight: 700;
}

.cmd-guild-desc {
  color: rgba(228, 236, 240, 0.35);
  font-size: clamp(0.4rem, 0.75vw, 0.5rem);
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
  transition: 0.5s;
  background: transparent;
  border: none;
  font-family: inherit;
  color: inherit;
  overflow: hidden;
}

.cmd-bottom-item:hover {
  background: rgba(0, 173, 181, 0.1);
  box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.4);
}

.cmd-bottom-item:hover h1 {
  text-shadow: 0 0 8px rgba(0, 255, 245, 0.35);
}

.cmd-bottom-item h1 {
  color: #E4ECF0;
  font-size: clamp(0.5rem, 1vw, 0.6rem);
  font-weight: 700;
  margin: 0;
  transition: text-shadow 0.4s;
}

.cmd-bottom-item span {
  color: rgba(228, 236, 240, 0.35);
  font-size: clamp(0.35rem, 0.7vw, 0.45rem);
  transition: 0.4s;
}

.cmd-bottom-item:hover span {
  color: rgba(228, 236, 240, 0.65);
}
</style>
