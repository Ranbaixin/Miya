<script setup lang="ts">
import { useStorage, useWindowSize } from '@vueuse/core'
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import API from '@/api/core'
import { CONFIG } from '@/utils/config'

const router = useRouter()

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

// ─── Wing layout — 左翼 4 张 + 右翼 4 张 ──────────────────────────
// radii: tip 羽尖 / inner 内羽 — staggered for feather look
const cards = [
  // ═══ 左翼（扇展 150°→210°）═══
  { id: 'community', label: '娜迦社区', desc: '发帖 · 交友 · 互动', path: '/community', angle: 150, radius: 1, varName: '--miya-comp-panel-card-1', fallback: '#ff77aa', emoji: '✧' },
  { id: 'screen',    label: '屏幕视觉', desc: '截图 · AI 分析',       path: '/screen',    angle: 167, radius: 2, varName: '--miya-comp-panel-card-2', fallback: '#ff9944', emoji: '⊙' },
  { id: 'terminal',  label: '终端引擎', desc: 'Claude Code · 代码',   path: '/terminal',  angle: 193, radius: 2, varName: '--miya-comp-panel-card-3', fallback: '#00e88f', emoji: '⬡' },
  { id: 'openclaw',  label: '电脑控制', desc: 'OpenClaw · AI 操作',   path: '/openclaw',  angle: 210, radius: 1, varName: '--miya-comp-panel-card-4', fallback: '#ff5577', emoji: '⬢' },
  // ═══ 右翼（扇展 -30°→30°）═══
  { id: 'chat',      label: '弥娅对话', desc: '决策层 · 感知 · 协作', path: '/chat',      angle: -30, radius: 1, varName: '--miya-comp-panel-card-5', fallback: '#b44dff', emoji: '◆' },
  { id: 'mind',      label: '记忆星河', desc: '认知引擎 · 记忆网络',  path: '/mind',      angle: -13, radius: 2, varName: '--miya-comp-panel-card-6', fallback: '#00e5ff', emoji: '◇' },
  { id: 'config',    label: '灵魂调谐', desc: '人格 · 情绪 · 模型池', path: '/config',    angle:  13, radius: 2, varName: '--miya-comp-panel-card-7', fallback: '#d4af37', emoji: '❖' },
  { id: 'floating',  label: '铃音守护', desc: '轻量陪伴 · 悬浮球',   icon: 'floating',  angle:  30, radius: 1, varName: '--miya-comp-panel-card-8', fallback: '#4da6ff', emoji: '◈' },
]

// ─── Mouse tracking ──────────────────────────────────────────────────
const mouse = reactive({ x: 0.5, y: 0.5 })
function onMouseMove(e: MouseEvent) { mouse.x = e.clientX / window.innerWidth; mouse.y = e.clientY / window.innerHeight }
const hoveredCard = ref<string | null>(null)
onMounted(() => window.addEventListener('mousemove', onMouseMove))
onUnmounted(() => window.removeEventListener('mousemove', onMouseMove))

// ─── Wing geometry ───────────────────────────────────────────────────
const cardScale = useStorage('miya-panel-card-scale', 1.0)
// 半径随缩放自适应：卡片越大，轨道越远，减少重叠
const gapFactor = computed(() => 0.5 + cardScale.value * 0.6) // scale 1.0→1.1, scale 2.0→1.7
const tipRadius   = computed(() => Math.min(340, height.value * 0.38) * gapFactor.value)
const innerRadius = computed(() => Math.min(260, height.value * 0.32) * gapFactor.value)
const rotationRx  = computed(() => (mouse.y - 0.5) * -5)
const rotationRy  = computed(() => (mouse.x - 0.5) * 8)
const SCALE       = computed(() => Math.min(1.08, Math.max(0.72, height.value / 900)) * cardScale.value)

const cardPositions = computed(() =>
  cards.map(c => {
    const rad = (c.angle * Math.PI) / 180
    const r = c.radius === 1 ? tipRadius.value : innerRadius.value
    return { x: Math.cos(rad) * r, y: Math.sin(rad) * r }
  }),
)

// ─── Constellation ───────────────────────────────────────────────────
const wingLines = computed(() => {
  const pos = cardPositions.value
  const lines: { x1: number; y1: number; x2: number; y2: number; cls: string }[] = []
  // Left wing: feather chain (0→1→2→3)
  for (let i = 0; i < 3; i++) lines.push({ x1: pos[i].x, y1: pos[i].y, x2: pos[i + 1].x, y2: pos[i + 1].y, cls: 'wing-feather' })
  // Right wing: feather chain (4→5→6→7)
  for (let i = 4; i < 7; i++) lines.push({ x1: pos[i].x, y1: pos[i].y, x2: pos[i + 1].x, y2: pos[i + 1].y, cls: 'wing-feather' })
  // Each feather to center
  for (let i = 0; i < cards.length; i++) lines.push({ x1: 0, y1: 0, x2: pos[i].x, y2: pos[i].y, cls: 'feather-to-center' })
  // Wing root connectors (tip feathers → center with highlight)
  lines.push({ x1: 0, y1: 0, x2: pos[0].x, y2: pos[0].y, cls: 'wing-root' })
  lines.push({ x1: 0, y1: 0, x2: pos[3].x, y2: pos[3].y, cls: 'wing-root' })
  lines.push({ x1: 0, y1: 0, x2: pos[4].x, y2: pos[4].y, cls: 'wing-root' })
  lines.push({ x1: 0, y1: 0, x2: pos[7].x, y2: pos[7].y, cls: 'wing-root' })
  return lines
})

// ─── Per-card tilt ───────────────────────────────────────────────────
const TILT = 10
function cardTilt(idx: number) {
  const pos = cardPositions.value[idx]
  if (!pos) return { rx: 0, ry: 0 }
  return { rx: (mouse.y - 0.5) * -TILT, ry: (mouse.x - 0.5) * TILT }
}
function cardTransform(i: number) {
  const t = cardTilt(i)
  const s = hoveredCard.value === cards[i].id ? SCALE.value * 1.12 : SCALE.value
  return `translate(-50%,-50%) perspective(800px) rotateX(${t.rx}deg) rotateY(${t.ry}deg) scale(${s})`
}

function navigate(card: typeof cards[0]) {
  if (card.id === 'floating') return enterFloatingMode()
  if (card.path) router.push(card.path)
}
function enterFloatingMode() {
  CONFIG.value.floating.enabled = true
  window.electronAPI?.floating.enter()
}
</script>

<template>
  <div class="star-orbit">
    <!-- ── Center Logo ── -->
    <div class="logo-center">
      <div class="logo-ring">
        <svg viewBox="0 0 100 100" fill="none">
          <circle cx="50" cy="42" r="40" stroke="var(--miya-primary)" stroke-width="0.8" opacity="0.18" />
          <circle cx="50" cy="42" r="36" stroke="var(--miya-primary)" stroke-width="1.0" opacity="0.25" />
          <circle cx="50" cy="42" r="28" stroke="var(--miya-accent)" stroke-width="1.5" opacity="0.35" />
          <circle cx="50" cy="42" r="18" stroke="var(--miya-primary)" stroke-width="1.8" opacity="0.4" />
          <circle cx="50" cy="42" r="8" stroke="var(--miya-accent)" stroke-width="2" opacity="0.5" />
          <path d="M50 5C50 5 22 25 22 50C22 68 50 85 50 85" stroke="var(--miya-primary)" stroke-width="1.2" stroke-linecap="round" opacity="0.35" />
          <path d="M50 5C50 5 78 25 78 50C78 68 50 85 50 85" stroke="var(--miya-primary)" stroke-width="1.2" stroke-linecap="round" opacity="0.25" />
          <circle cx="50" cy="42" r="2" fill="var(--miya-accent)" opacity="0.9" />
          <circle cx="38" cy="36" r="1.5" fill="var(--miya-gold)" opacity="0.7" />
          <circle cx="62" cy="36" r="1.2" fill="var(--miya-gold)" opacity="0.6" />
          <circle cx="30" cy="52" r="1" fill="var(--miya-gold)" opacity="0.4" />
          <circle cx="70" cy="52" r="0.8" fill="var(--miya-gold)" opacity="0.35" />
          <circle cx="50" cy="58" r="1" fill="var(--miya-gold)" opacity="0.3" />
        </svg>
      </div>
      <div class="logo-title">弥娅</div>
      <div class="logo-sub">MIYA · AI COMPANION</div>
      <div class="logo-pulse" />
    </div>

    <!-- ── Wing system ── -->
    <div
      class="orbit-system"
      :style="{ transform: `perspective(1000px) rotateX(${rotationRx}deg) rotateY(${rotationRy}deg)` }"
    >
      <!-- Wing SVG overlay -->
      <svg class="wing-svg" viewBox="-350 -350 700 700">
        <defs>
          <filter id="wing-glow">
            <feGaussianBlur stdDeviation="1.5" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <linearGradient id="left-wing-grad" x1="1" y1="0.5" x2="0" y2="0.5">
            <stop offset="0%" stop-color="rgba(167,139,250,0)" />
            <stop offset="100%" stop-color="rgba(167,139,250,0.18)" />
          </linearGradient>
          <linearGradient id="right-wing-grad" x1="0" y1="0.5" x2="1" y2="0.5">
            <stop offset="0%" stop-color="rgba(167,139,250,0.18)" />
            <stop offset="100%" stop-color="rgba(167,139,250,0)" />
          </linearGradient>
        </defs>
        <!-- Left wing energy field -->
        <polygon
          :points="`0,0 ${cardPositions[0].x},${cardPositions[0].y} ${cardPositions[1].x},${cardPositions[1].y} ${cardPositions[2].x},${cardPositions[2].y} ${cardPositions[3].x},${cardPositions[3].y}`"
          fill="url(#left-wing-grad)" opacity="0.15" stroke="var(--miya-accent)" stroke-width="0.4" stroke-dasharray="3 5" />
        <!-- Right wing energy field -->
        <polygon
          :points="`0,0 ${cardPositions[4].x},${cardPositions[4].y} ${cardPositions[5].x},${cardPositions[5].y} ${cardPositions[6].x},${cardPositions[6].y} ${cardPositions[7].x},${cardPositions[7].y}`"
          fill="url(#right-wing-grad)" opacity="0.15" stroke="var(--miya-accent)" stroke-width="0.4" stroke-dasharray="3 5" />
        <!-- Lines -->
        <g opacity="0.3">
          <line v-for="(l,i) in wingLines.filter(l=>l.cls==='feather-to-center')" :key="'fc'+i"
            :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2"
            stroke="var(--miya-accent,#a78bfa)" stroke-width="0.35" stroke-dasharray="2 6" opacity="0.3" />
          <line v-for="(l,i) in wingLines.filter(l=>l.cls==='wing-feather')" :key="'wf'+i"
            :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2"
            stroke="var(--miya-accent,#a78bfa)" stroke-width="0.4" stroke-dasharray="3 4" opacity="0.35" />
          <line v-for="(l,i) in wingLines.filter(l=>l.cls==='wing-root')" :key="'wr'+i"
            :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2"
            stroke="var(--miya-gold,#d4af37)" stroke-width="0.8" opacity="0.4" filter="url(#wing-glow)" />
        </g>
      </svg>

      <!-- Orbit cards (wings) -->
      <div
        v-for="(card, i) in cards"
        :key="card.id"
        class="orbit-card"
        :class="[{ 'is-hovered': hoveredCard === card.id }, `wing-${i < 4 ? 'left' : 'right'}`]"
        :style="{
          '--card-color': `var(${card.varName}, ${card.fallback})`,
          left: `calc(50% + ${cardPositions[i].x}px)`,
          top: `calc(50% + ${cardPositions[i].y}px)`,
          transform: cardTransform(i),
          transition: hoveredCard === card.id
            ? 'transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.35s, border-color 0.3s'
            : 'transform 0.18s ease-out, box-shadow 0.35s, border-color 0.3s',
        }"
        @click="navigate(card)"
        @mouseenter="hoveredCard = card.id"
        @mouseleave="hoveredCard = null"
      >
        <div class="card-track" />
        <div class="card-corners" />
        <div class="card-sheen" />
        <div class="card-aurora" />
        <div class="card-particles">
          <span v-for="n in 6" :key="n" class="particle-dot" :style="{ '--i': n }" />
        </div>
        <div class="card-inner">
          <span class="card-emoji">{{ card.emoji }}</span>
          <div class="card-text">
            <span class="card-label">{{ card.label }}</span>
            <span class="card-desc">{{ card.desc }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="orbit-verse">雪落无声 — 愿系铃中</div>
    <!-- 卡片尺寸调节 -->
    <div class="card-scale-bar">
      <span class="scale-icon">◈</span>
      <input
        type="range"
        :min="0.6"
        :max="2.0"
        :step="0.05"
        v-model="cardScale"
        class="scale-slider"
        title="调节卡片大小"
      >
      <span class="scale-val">{{ Math.round(cardScale * 100) }}%</span>
      <button
        class="scale-reset"
        :class="{ active: cardScale === 1.0 }"
        @click="cardScale = 1.0"
        title="恢复默认"
      >↺</button>
    </div>
    <div v-if="miyaBackendOnline" class="orbit-status">
      <span class="status-dot" />
      <span class="status-item">在线</span>
      <span class="status-sep">·</span>
      <span class="status-item">{{ miyaPlatforms }} 平台</span>
      <span class="status-sep">·</span>
      <span class="status-item">人格：{{ miyaPersona }}</span>
    </div>
  </div>
</template>

<style scoped>
/* ─── Container ───────────────────────────────────── */
.star-orbit {
  position: relative; width: 100%; height: 100%;
  overflow: hidden; user-select: none;
  font-family: 'Noto Serif SC','Inter',system-ui,sans-serif;
}
.orbit-system { position: relative; width: 100%; height: 100%; will-change: transform; }

/* ─── Wing SVG ────────────────────────────────────── */
.wing-svg {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%,-50%);
  width: 700px; height: 700px; pointer-events: none; z-index: 0;
}

/* ─── Center Logo ─────────────────────────────────── */
.logo-center {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%,-50%);
  display: flex; flex-direction: column; align-items: center; gap: 0.25rem; z-index: 10;
  filter: drop-shadow(0 0 40px var(--miya-glow,rgba(167,139,250,0.3)));
}
.logo-ring { width: 130px; height: 130px; animation: logo-glow 4s ease-in-out infinite; }
.logo-title {
  font-family: 'Noto Serif SC',serif; font-size: 2.6rem; font-weight: 700;
  background: linear-gradient(135deg,#e8d5f5 0%,var(--miya-accent) 35%,var(--miya-primary,#a78bfa) 70%,#bae6fd 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  letter-spacing: 0.25em;
  filter: drop-shadow(0 0 14px var(--miya-glow,rgba(167,139,250,0.35)));
}
.logo-sub { font-size: 0.58rem; color: var(--miya-text-dim,#888); letter-spacing: 0.55em; opacity: 0.6; }
.logo-pulse {
  position: absolute; width: 200px; height: 200px; border-radius: 50%;
  background: radial-gradient(circle,rgba(167,139,250,0.06) 0%,transparent 70%);
  animation: pulse-ring 3s ease-in-out infinite; pointer-events: none;
}
@keyframes logo-glow {
  0%,100% { filter: drop-shadow(0 0 20px var(--miya-glow,rgba(167,139,250,0.25))); }
  50% { filter: drop-shadow(0 0 45px var(--miya-glow,rgba(167,139,250,0.5))); }
}
@keyframes pulse-ring {
  0%,100% { transform: scale(0.92); opacity: 0.25; }
  50% { transform: scale(1.08); opacity: 0.08; }
}

/* ─── Orbit Cards — 透明浮空 + 双层轨线 ──────────── */
.orbit-card {
  --card-color: #a78bfa;
  position: absolute; cursor: pointer;
  width: 162px; padding: 1rem 1.1rem;
  background: rgba(10, 8, 21, 0.06);
  border: 1px solid color-mix(in srgb, var(--card-color) 20%, transparent);
  border-radius: 12px;
  overflow: visible; z-index: 5;
  will-change: transform, box-shadow;
}
.orbit-card.is-hovered {
  background: rgba(10, 8, 21, 0.15);
  border-color: color-mix(in srgb, var(--card-color) 65%, transparent);
  box-shadow: 0 0 26px color-mix(in srgb, var(--card-color) 38%, transparent), 0 6px 34px rgba(0,0,0,0.35);
  z-index: 20;
}

/* Inner track */
.card-track {
  position: absolute; inset: 3px; border-radius: 9px;
  border: 0.5px solid color-mix(in srgb, var(--card-color) 8%, transparent);
  pointer-events: none; z-index: 0; opacity: 0.5;
  transition: border-color 0.35s, opacity 0.35s;
}
.orbit-card.is-hovered .card-track { border-color: color-mix(in srgb, var(--card-color) 35%, transparent); opacity: 0.9; }

/* Corner dots */
.card-corners {
  position: absolute; inset: -3px; border-radius: 14px;
  background:
    radial-gradient(1.8px, var(--card-color) 100%, transparent) 0 0,
    radial-gradient(1.8px, var(--card-color) 100%, transparent) 100% 0,
    radial-gradient(1.8px, var(--card-color) 100%, transparent) 0 100%,
    radial-gradient(1.8px, var(--card-color) 100%, transparent) 100% 100%;
  background-size: 4px 4px; background-repeat: no-repeat;
  opacity: 0; transition: opacity 0.35s; pointer-events: none; z-index: 4;
  filter: drop-shadow(0 0 3px var(--card-color));
}
.orbit-card.is-hovered .card-corners { opacity: 0.85; }

/* Glass sheen */
.card-sheen {
  position: absolute; inset: 0; border-radius: inherit;
  background: linear-gradient(135deg, transparent 0%, rgba(255,255,255,0.03) 38%, rgba(255,255,255,0.07) 50%, rgba(255,255,255,0.02) 62%, transparent 100%);
  opacity: 0.3; transition: opacity 0.4s; pointer-events: none; z-index: 1;
}
.orbit-card.is-hovered .card-sheen { opacity: 0.65; }

/* Aurora */
.card-aurora {
  position: absolute; inset: 0; border-radius: inherit;
  background: linear-gradient(120deg, transparent 0%, color-mix(in srgb, var(--card-color) 5%, transparent) 25%, color-mix(in srgb, var(--miya-gold,#d4af37) 3%, transparent) 50%, color-mix(in srgb, var(--card-color) 5%, transparent) 75%, transparent 100%);
  background-size: 300% 100%;
  animation: aurora-sweep 5s ease-in-out infinite;
  pointer-events: none; z-index: 0; opacity: 0.55;
}
.orbit-card.is-hovered .card-aurora { animation-duration: 2s; opacity: 1; }
@keyframes aurora-sweep { 0%,100% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } }

/* Particles */
.card-particles { position: absolute; inset: -10px; pointer-events: none; opacity: 0; transition: opacity 0.4s; z-index: 0; }
.orbit-card.is-hovered .card-particles { opacity: 1; }
.particle-dot {
  --i: 1; position: absolute; width: 2.5px; height: 2.5px; border-radius: 50%;
  background: var(--card-color); box-shadow: 0 0 4px var(--card-color);
  top: 50%; left: 50%;
  animation: particle-orbit 2.8s linear infinite;
  animation-delay: calc(var(--i) * -0.45s);
}
@keyframes particle-orbit {
  0% { transform: translate(-50%,-50%) rotate(calc(var(--i)*60deg)) translateX(80px) rotate(calc(var(--i)*-60deg)); }
  to { transform: translate(-50%,-50%) rotate(calc(var(--i)*60deg + 360deg)) translateX(80px) rotate(calc(var(--i)*-60deg - 360deg)); }
}

/* Inner content */
.card-inner { position: relative; z-index: 2; display: flex; align-items: center; gap: 0.7rem; }
.card-emoji {
  font-size: 1.3rem; flex-shrink: 0;
  transition: transform 0.35s cubic-bezier(0.34,1.56,0.64,1), filter 0.3s;
  filter: drop-shadow(0 0 4px color-mix(in srgb,var(--card-color) 40%,transparent));
}
.orbit-card.is-hovered .card-emoji { transform: scale(1.25) rotate(-5deg); filter: drop-shadow(0 0 10px var(--card-color)); }
.card-text { display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; }
.card-label { font-size: 0.85rem; font-weight: 600; letter-spacing: 0.06em; color: var(--miya-text,#e8d5f5); white-space: nowrap; }
.card-desc {
  font-size: 0.58rem; color: var(--miya-text-dim,#666); letter-spacing: 0.05em; white-space: nowrap;
  max-height: 0; opacity: 0; overflow: hidden;
  transition: max-height 0.4s ease, opacity 0.35s ease, margin 0.35s ease;
}
.orbit-card.is-hovered .card-desc { max-height: 1.2em; opacity: 0.8; margin-top: 2px; }

/* ─── Bottom ──────────────────────────────────────── */
.orbit-verse {
  position: absolute; bottom: 38px; left: 50%; transform: translateX(-50%);
  font-family: 'Noto Serif SC',serif; font-size: 0.72rem; color: var(--miya-text-dim,#666);
  letter-spacing: 0.25em; opacity: 0.35; white-space: nowrap;
}
.orbit-status {
  position: absolute; bottom: 14px; left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: 0.5rem;
  font-family: 'JetBrains Mono',monospace; font-size: 0.6rem; color: var(--miya-text-dim,#666); opacity: 0.5;
}
.status-dot { width: 5px; height: 5px; border-radius: 50%; background: rgba(0,229,255,0.6); box-shadow: 0 0 6px rgba(0,229,255,0.3); }
.status-sep { opacity: 0.3; }
.status-item { opacity: 0.7; }

/* ── 卡片尺寸调节条 ────────────────────────────── */
.card-scale-bar {
  position: absolute;
  bottom: 64px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: rgba(8, 14, 24, 0.45);
  backdrop-filter: blur(6px);
  border: 1px solid color-mix(in srgb, var(--miya-accent, #a78bfa) 10%, transparent);
  border-radius: 1rem;
  padding: 0.3rem 0.7rem;
  opacity: 0.7;
  transition: opacity 0.3s, border-color 0.3s;
  z-index: 15;
}
.card-scale-bar:hover {
  opacity: 1;
  border-color: color-mix(in srgb, var(--miya-accent, #a78bfa) 25%, transparent);
}
.scale-icon {
  font-size: 0.55rem;
  color: var(--miya-text-dim);
}
.scale-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100px;
  height: 4px;
  border-radius: 2px;
  background: rgba(0, 229, 255, 0.18);
  outline: none;
  cursor: pointer;
}
.scale-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--miya-accent, #a78bfa);
  box-shadow: 0 0 6px var(--miya-glow, rgba(167, 139, 250, 0.3));
  cursor: pointer;
  transition: transform 0.2s;
}
.scale-slider::-webkit-slider-thumb:hover {
  transform: scale(1.3);
}
.scale-val {
  font-size: 0.55rem;
  color: var(--miya-text-dim);
  font-family: 'JetBrains Mono', monospace;
  min-width: 2.2rem;
}
.scale-reset {
  padding: 0;
  width: 16px;
  height: 16px;
  border: 1px solid rgba(0, 229, 255, 0.12);
  border-radius: 50%;
  background: transparent;
  color: var(--miya-text-dim);
  font-size: 0.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  line-height: 1;
}
.scale-reset:hover,
.scale-reset.active {
  border-color: rgba(0, 229, 255, 0.3);
  color: var(--miya-accent);
  background: rgba(0, 229, 255, 0.06);
}
</style>
