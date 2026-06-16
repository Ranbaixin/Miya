<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useTemplateRef } from 'vue'
import { playWakeVoice } from '@/composables/useAudio'
import { CONFIG } from '@/utils/config'

const props = defineProps<{
  progress: number
  phase: string
  modelReady: boolean
  stallHint: boolean
  live2dVisible: boolean
}>()

const emit = defineEmits<{
  dismiss: []
  titleDone: []
}>()

function getSplashColor(varName: string, fallback: string): string {
  const val = getComputedStyle(document.documentElement).getPropertyValue(varName).trim()
  return val || fallback
}

const titleOverlayVisible = ref(true)

onMounted(() => {
  playWakeVoice()
})

function onTitleAnimEnd() {
  // 标题图片动画结束 → 淡出黑色遮罩
  titleOverlayVisible.value = false
}

function onOverlayAfterLeave() {
  // 黑色遮罩完全淡出 → 标题阶段结束（粒子继续，直到用户点击唤醒）
  emit('titleDone')
}

// ─── 标题粒子效果（从下往上飘） ──────────────────
const particleCanvas = useTemplateRef<HTMLCanvasElement>('particleCanvas')
let particleRaf = 0

interface Particle {
  x: number
  y: number
  vy: number // 上升速度
  vx: number // 微小水平漂移
  size: number
  alpha: number
  maxAlpha: number
  life: number // 剩余帧
  maxLife: number
}

function initParticles() {
  const canvas = particleCanvas.value
  if (!canvas)
    return

  const ctx = canvas.getContext('2d')!
  if (!ctx)
    return

  const dpr = window.devicePixelRatio || 1
  canvas.width = canvas.clientWidth * dpr
  canvas.height = canvas.clientHeight * dpr
  ctx.scale(dpr, dpr)

  const w = canvas.clientWidth
  const h = canvas.clientHeight
  const particles: Particle[] = []
  const PARTICLE_COUNT = 40

  function spawnParticle(): Particle {
    return {
      x: Math.random() * w,
      y: h + Math.random() * 20, // 从底部稍下方生成
      vy: -(0.3 + Math.random() * 0.8), // 上升速度
      vx: (Math.random() - 0.5) * 0.3, // 微小水平漂移
      size: 1 + Math.random() * 2.5,
      alpha: 0,
      maxAlpha: 0.2 + Math.random() * 0.5,
      life: 200 + Math.random() * 200,
      maxLife: 0, // 在生成后设置
    }
  }

  // 初始化粒子（分散在不同高度）
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const p = spawnParticle()
    p.y = Math.random() * h // 初始分散
    p.life = Math.random() * 300
    p.maxLife = p.life
    particles.push(p)
  }

  function animate() {
    const particleHex = getSplashColor('--miya-comp-splash-particle', '#d4af37')
    ctx.clearRect(0, 0, w, h)

    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i]!
      p.x += p.vx
      p.y += p.vy
      p.life--

      // 淡入淡出
      const lifeRatio = p.maxLife > 0 ? p.life / p.maxLife : 0
      if (lifeRatio > 0.8) {
        // 前 20%: 淡入
        p.alpha = p.maxAlpha * ((1 - lifeRatio) / 0.2)
      }
      else if (lifeRatio < 0.3) {
        // 后 30%: 淡出
        p.alpha = p.maxAlpha * (lifeRatio / 0.3)
      }
      else {
        p.alpha = p.maxAlpha
      }

      // 绘制发光粒子
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
      ctx.fillStyle = particleHex.replace('#', '').replace(
        /^([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$/,
        (_, r, g, b) => `rgba(${parseInt(r, 16)}, ${parseInt(g, 16)}, ${parseInt(b, 16)}, ${p.alpha})`,
      )
      ctx.fill()

      if (p.size > 1.5) {
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size * 2.5, 0, Math.PI * 2)
        ctx.fillStyle = particleHex.replace('#', '').replace(
          /^([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$/,
          (_, r, g, b) => `rgba(${parseInt(r, 16)}, ${parseInt(g, 16)}, ${parseInt(b, 16)}, ${p.alpha * 0.15})`,
        )
        ctx.fill()
      }

      // 回收并重新生成
      if (p.life <= 0 || p.y < -10) {
        const np = spawnParticle()
        np.maxLife = np.life
        particles[i] = np
      }
    }

    particleRaf = requestAnimationFrame(animate)
  }

  particleRaf = requestAnimationFrame(animate)
}

function stopParticles() {
  if (particleRaf) {
    cancelAnimationFrame(particleRaf)
    particleRaf = 0
  }
}

onMounted(() => {
  initParticles()
})

onBeforeUnmount(() => {
  stopParticles()
})

// ─── 进度 ─────────────────────────────────
const canDismiss = computed(() => props.progress >= 100)
const displayProgress = computed(() => Math.min(100, Math.round(props.progress)))
</script>

<template>
  <div class="fixed inset-0 z-50 overflow-hidden select-none">
    <!-- 上升光粒层（clip-path 镂空，不遮挡 L2D 窗口；z-index 高于 frame-mask 暗层） -->

    <!-- clip-path evenodd 开洞遮罩：中间矩形区域透明，四周深色 -->
    <div class="frame-mask" />

    <!-- 矩形框金色边框 -->
    <div class="frame-border" />

    <!-- 上升光粒（clip-path 镂空，不遮挡 L2D 窗口；z-index 高于 frame-mask 暗层） -->
    <div class="particle-layer">
      <canvas ref="particleCanvas" class="absolute inset-0 w-full h-full" />
    </div>

    <!-- 底部进度区域 -->
    <div class="absolute bottom-12 left-1/2 -translate-x-1/2 w-60% flex flex-col items-center gap-2">
      <!-- 阶段文字 + 百分比 -->
      <div
        class="flex justify-between w-full px-1 text-xs tracking-widest"
        :style='{ color: `color-mix(in srgb, ${getSplashColor("--miya-comp-splash-progress", "#d4af37")} 70%, transparent)`, fontFamily: "Segoe UI, sans-serif" }'
      >
        <span>{{ phase }}</span>
        <span>{{ displayProgress }}%</span>
      </div>
      <!-- 进度条轨道 -->
      <div class="w-full h-0.5 rounded-full" :style="{ background: `color-mix(in srgb, ${getSplashColor('--miya-comp-splash-progress', '#d4af37')} 15%, transparent)` }">
        <div
          class="h-full rounded-full transition-all duration-300 ease-out"
          :style="{
            background: `linear-gradient(90deg, color-mix(in srgb, ${getSplashColor('--miya-comp-splash-progress', '#d4af37')} 40%, transparent), color-mix(in srgb, ${getSplashColor('--miya-comp-splash-progress', '#d4af37')} 90%, transparent))`,
            width: `${displayProgress}%`,
          }"
        />
      </div>
      <!-- 停滞提示 -->
      <Transition name="fade">
        <span v-if="stallHint" class="stall-hint">如果中途卡死，请重启应用</span>
      </Transition>
    </div>

    <!-- 左下角版本号 -->
    <div class="version-label">
      v{{ CONFIG.system.version }}
    </div>

    <!-- 点击进入提示 -->
    <Transition name="fade">
      <div
        v-if="canDismiss"
        class="absolute inset-0 flex items-end justify-center pb-28 cursor-pointer clickable"
        @click="emit('dismiss')"
      >
        <span class="click-hint text-sm tracking-[0.3em]" :style="{ color: `color-mix(in srgb, ${getSplashColor('--miya-comp-splash-title', '#d4af37')} 80%, transparent)` }">
          点 击 唤 醒
        </span>
      </div>
    </Transition>

    <!-- 标题阶段：纯黑遮罩 + 标题图片 + 上升粒子 -->
    <Transition name="title-overlay" @after-leave="onOverlayAfterLeave">
      <div v-if="titleOverlayVisible" class="title-overlay">
        <!-- 标题图片 -->
        <div class="title-content" @animationend="onTitleAnimEnd">
          <img src="/assets/title.png" alt="弥娅 AI" class="title-img">
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* ── 组件调色变量 ── */
.frame-mask, .particle-layer {
  --splash-particle: var(--miya-comp-splash-particle, #d4af37);
  --splash-progress: var(--miya-comp-splash-progress, #d4af37);
  --splash-title: var(--miya-comp-splash-title, #d4af37);
}
/* 光粒层：与 frame-mask 相同 clip-path，只在四周暗区显示粒子，不遮挡 L2D 窗口 */
.particle-layer {
  position: absolute;
  inset: 0;
  z-index: 101;
  pointer-events: none;
  --frame-w: 36vw;
  --frame-h: 52vh;
  --frame-x: calc(50% - var(--frame-w) / 2);
  --frame-y: calc(38% - var(--frame-h) / 2);
  clip-path: polygon(
    evenodd,
    0% 0%, 100% 0%, 100% 100%, 0% 100%,
    var(--frame-x) var(--frame-y),
    var(--frame-x) calc(var(--frame-y) + var(--frame-h)),
    calc(var(--frame-x) + var(--frame-w)) calc(var(--frame-y) + var(--frame-h)),
    calc(var(--frame-x) + var(--frame-w)) var(--frame-y)
  );
}

.frame-mask {
  position: absolute;
  inset: 0;
  /* 居中矩形开洞 - 宽度约36vw, 高度约52vh, 稍偏上 */
  --frame-w: 36vw;
  --frame-h: 52vh;
  --frame-x: calc(50% - var(--frame-w) / 2);
  --frame-y: calc(38% - var(--frame-h) / 2);
  /* evenodd 填充规则：内外路径交叉区域镂空 */
  clip-path: polygon(
    evenodd,
    0% 0%, 100% 0%, 100% 100%, 0% 100%,
    var(--frame-x) var(--frame-y),
    var(--frame-x) calc(var(--frame-y) + var(--frame-h)),
    calc(var(--frame-x) + var(--frame-w)) calc(var(--frame-y) + var(--frame-h)),
    calc(var(--frame-x) + var(--frame-w)) var(--frame-y)
  );
  background: rgba(0, 0, 0, 0.85);
  pointer-events: none;
}

.frame-border {
  position: absolute;
  width: 36vw;
  height: 52vh;
  left: 50%;
  top: 38%;
  transform: translate(-50%, -50%);
  border: 1px solid color-mix(in srgb, var(--splash-title) 40%, transparent);
  box-shadow: 0 0 15px color-mix(in srgb, var(--splash-title) 15%, transparent), inset 0 0 15px color-mix(in srgb, var(--splash-title) 5%, transparent);
  pointer-events: none;
}

/* 停滞提示 */
.stall-hint {
  margin-top: 0.5rem;
  font-size: 0.65rem;
  color: color-mix(in srgb, var(--splash-progress) 45%, transparent);
  letter-spacing: 0.05em;
}

.version-label {
  position: absolute;
  bottom: 1.2rem;
  left: 1.5rem;
  font-size: 0.75rem;
  color: color-mix(in srgb, var(--splash-title) 35%, transparent);
  letter-spacing: 0.08em;
  font-family: 'Segoe UI', sans-serif;
}

/* 点击进入脉冲动画 */
.click-hint {
  animation: pulse-gold 2s ease-in-out infinite;
}

@keyframes pulse-gold {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; text-shadow: 0 0 12px color-mix(in srgb, var(--splash-title) 50%, transparent); }
}

/* 内部元素淡入 */
.fade-enter-active {
  transition: opacity 0.6s ease;
}
.fade-enter-from {
  opacity: 0;
}

/* ─── 标题阶段 ─────────────────────────────── */
.title-overlay {
  position: absolute;
  inset: 0;
  z-index: 100;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.title-content {
  position: relative;
  z-index: 1;
  /* 0→0.6s 渐入, 0.6→1.6s 保持, 1.6→2.4s 渐出 */
  animation: title-sequence 2.4s ease-in-out forwards;
}

.title-img {
  width: min(60vw, 500px);
  height: auto;
  filter: drop-shadow(0 0 30px color-mix(in srgb, var(--splash-title) 25%, transparent));
  image-rendering: -webkit-optimize-contrast;
}

@keyframes title-sequence {
  0%   { opacity: 0; transform: scale(0.96); }
  25%  { opacity: 1; transform: scale(1); }     /* 0.6s — 渐入完成 */
  67%  { opacity: 1; transform: scale(1); }     /* 1.6s — 保持至少 1 秒 */
  100% { opacity: 0; transform: scale(1.02); }  /* 2.4s — 渐出完成 */
}

/* 黑色遮罩淡出 */
.title-overlay-leave-active {
  transition: opacity 0.8s ease;
}
.title-overlay-leave-to {
  opacity: 0;
}
</style>
