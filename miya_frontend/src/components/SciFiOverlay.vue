<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { onMounted, onUnmounted, ref } from 'vue'

const colorMode = useStorage('miya-hud-color', 'mixed')

const hudTextL = ref('SYS.OK')
const hudValsL = ref(['01', '7F', '3A', '88'])
const scanDots = ref<Array<{ x: number, y: number, size: number, delay: number }>>([])
const glitchBlock = ref({ visible: false, top: 0, height: 0 })
const driftChars = ref<Array<{ x: number, y: number, c: string, delay: number, size: number }>>([])
const driftBars = ref<Array<{ top: number, left: number, width: number, delay: number }>>([])
const driftWords = ref<Array<{ text: string, top: number, left: number, delay: number }>>([])

let textTimerL: ReturnType<typeof setInterval> | null = null
let valTimerL: ReturnType<typeof setInterval> | null = null
let glitchTimer: ReturnType<typeof setInterval> | null = null
let driftCharTimer: ReturnType<typeof setInterval> | null = null

const TEXTS = ['SYS.OK', 'LINK', 'NODE.1', 'MIYA', 'ACTV', 'SYNC', 'READY']
const HEX = '0123456789ABCDEF'

function randomHex(len: number) {
  let s = ''
  for (let i = 0; i < len; i++) s += HEX[Math.floor(Math.random() * 16)]
  return s
}

onMounted(() => {
  const dots = []
  for (let i = 0; i < 70; i++) {
    dots.push({
      x: Math.random() * 70 + 2,
      y: Math.random() * 85 + 8,
      size: Math.random() * 2.5 + 0.8,
      delay: Math.random() * 4,
    })
  }
  scanDots.value = dots

  // 全屏数据扰动 - 生成 150 个散落 HEX 字符
  const chars = []
  for (let i = 0; i < 150; i++) {
    chars.push({
      x: Math.random() * 96 + 2,
      y: Math.random() * 92 + 4,
      c: randomHex(1),
      delay: Math.random() * 3,
      size: Math.random() > 0.6 ? 14 : Math.random() > 0.3 ? 10 : 7,
    })
  }
  driftChars.value = chars

  // 随机闪烁横条
  const bars = []
  for (let i = 0; i < 40; i++) {
    bars.push({
      top: Math.random() * 90 + 5,
      left: Math.random() * 80 + 2,
      width: 30 + Math.random() * 120,
      delay: Math.random() * 3,
    })
  }
  driftBars.value = bars

  // 散落关键词
  const WORDS = ['SYS.OK', 'LINK', 'NODE.1', 'MIYA', 'ACTV', 'SYNC', 'READY', 'CORE', 'MEM', 'NET', 'DATA', 'FLOW', 'PULSE', 'ECHO', 'VOID']
  const wordsArr = []
  for (let i = 0; i < 25; i++) {
    wordsArr.push({
      text: WORDS[Math.floor(Math.random() * WORDS.length)]!,
      top: Math.random() * 88 + 6,
      left: Math.random() * 85 + 5,
      delay: Math.random() * 4,
    })
  }
  driftWords.value = wordsArr

  textTimerL = setInterval(() => { hudTextL.value = TEXTS[Math.floor(Math.random() * TEXTS.length)]! }, 2500)
  valTimerL = setInterval(() => { hudValsL.value = [randomHex(2), randomHex(2), randomHex(2), randomHex(2)] }, 1200)

  glitchTimer = setInterval(() => {
    glitchBlock.value = {
      visible: Math.random() > 0.5,
      top: Math.random() * 65 + 20,
      height: Math.random() * 4 + 1,
    }
  }, 700)

  // 全屏 HEX 字符随机刷新
  driftCharTimer = setInterval(() => {
    const idx = Math.floor(Math.random() * driftChars.value.length)
    driftChars.value[idx] = {
      ...driftChars.value[idx]!,
      c: randomHex(1),
    }
  }, 300)
})

onUnmounted(() => {
  if (textTimerL) clearInterval(textTimerL)
  if (valTimerL) clearInterval(valTimerL)
  if (glitchTimer) clearInterval(glitchTimer)
  if (driftCharTimer) clearInterval(driftCharTimer)
})
</script>

<template>
  <div class="sci-fi-overlay" :class="`mode-${colorMode}`">
    <!-- 左上 HUD -->
    <div class="hud-corner tl">
      <div class="hud-line line-h" />
      <div class="hud-line line-v" />
      <div class="hud-label">{{ hudTextL }}</div>
      <div class="hud-hex">
        <span v-for="v in hudValsL" :key="v" class="hex-val">{{ v }}</span>
      </div>
      <div class="hud-indicators">
        <span class="hud-dot on" /><span class="hud-dot on" />
        <span class="hud-dot" /><span class="hud-dot on" />
      </div>
    </div>

    <!-- 全屏数据扰动 -->
    <div class="hud-drift fullscreen">
      <div v-for="(dc, i) in driftChars" :key="'dc'+i" class="drift-block" :style="{ top: `${dc.y}%`, left: `${dc.x}%`, animationDelay: `${dc.delay}s` }">
        <span class="drift-char" :style="{ fontSize: `${dc.size}px` }">{{ dc.c }}</span>
      </div>
      <span v-for="(dw, i) in driftWords" :key="'dw'+i" class="drift-word" :style="{ top: `${dw.top}%`, left: `${dw.left}%`, animationDelay: `${dw.delay}s` }">{{ dw.text }}</span>
      <div v-for="(bar, i) in driftBars" :key="'drb'+i" class="drift-bar" :style="{ top: `${bar.top}%`, left: `${bar.left}%`, width: `${bar.width}px`, animationDelay: `${bar.delay}s` }" />
    </div>

    <!-- 左下数据流 -->
    <div class="data-stream bl">
      <div class="scan-lines">
        <div class="scan-line" v-for="i in 6" :key="i" :style="{ animationDelay: `${i * 0.4}s` }" />
      </div>
      <div v-for="(dot, i) in scanDots" :key="i" class="scan-dot" :style="{ left: `${dot.x}%`, top: `${dot.y}%`, width: `${dot.size}px`, height: `${dot.size}px`, animationDelay: `${dot.delay}s` }" />
      <div v-if="glitchBlock.visible" class="glitch-bar" :style="{ top: `${glitchBlock.top}%`, height: `${glitchBlock.height}px` }" />
    </div>

    <!-- 右下横向流动 -->
    <div class="hud-flow br">
      <div class="flow-line" v-for="i in 5" :key="i" :style="{ animationDelay: `${i * 0.5}s`, top: `${i * 18}%` }">
        <div class="flow-dash" />
      </div>
      <div class="flow-label">
        <span class="flow-hex">{{ randomHex(8) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ═══ 颜色模式 ═══ */
.sci-fi-overlay {
  position: fixed; inset: 0; pointer-events: none; z-index: 100; overflow: hidden;
  /* default cyan */
  --c1: 0,229,255; --c2: 0,229,255; --c3: 0,229,255; --c4: 180,77,255;
}

/* 暖色: 粉+红+橙 */
.sci-fi-overlay.mode-warm {
  --c1: 255,107,157; --c2: 255,68,136; --c3: 255,140,100; --c4: 255,180,200;
}

/* 混色: 不同元素不同色 */
.sci-fi-overlay.mode-mixed {
  --c1: 0,229,255;    /* 左上 - 青色 */
  --c2: 255,107,157;   /* 右上 - 粉色 */
  --c3: 180,77,255;    /* 左下 - 紫色 */
  --c4: 255,68,136;    /* 右下 - 红粉 */
}

/* 紫色 */
.sci-fi-overlay.mode-purple {
  --c1: 167,139,250; --c2: 180,77,255; --c3: 167,139,250; --c4: 200,150,255;
}

/* 紫色 */
.sci-fi-overlay.mode-purple {
  --c1: 167,139,250; --c2: 180,77,255; --c3: 167,139,250; --c4: 200,150,255;
}

/* 蓝色 */
.sci-fi-overlay.mode-blue {
  --c1: 68,136,255; --c2: 100,160,255; --c3: 68,136,255; --c4: 130,180,255;
}

/* ═══ 颜色覆盖: 暖色 ═══ */
.mode-warm .hud-line { background: rgba(255,107,157,.2); }
.mode-warm .hud-label { color: rgba(255,107,157,.55); }
.mode-warm .hex-val { color: rgba(255,107,157,.35); }
.mode-warm .hud-dot { background: rgba(255,107,157,.12); }
.mode-warm .hud-dot.on { background: rgba(255,107,157,.55); box-shadow: 0 0 6px rgba(255,107,157,.4); }
.mode-warm .drift-char { color: rgba(255,68,136,.35); }
.mode-warm .drift-word { color: rgba(255,68,136,.22); }
.mode-warm .drift-bar { background: rgba(255,68,136,.2); }
.mode-warm .scan-line { background: linear-gradient(90deg,transparent,rgba(255,140,100,.07),transparent); }
.mode-warm .scan-dot { background: rgba(255,140,100,.25); }
.mode-warm .glitch-bar { background: rgba(255,140,100,.03); }
.mode-warm .flow-dash { background: linear-gradient(90deg,transparent,rgba(255,180,200,.3),transparent); }
.mode-warm .flow-hex { border-bottom-color: rgba(255,180,200,.12); }
.mode-warm .flow-label { color: rgba(255,180,200,.3); }

/* ═══ 颜色覆盖: 混色 ═══ */
.mode-mixed .hud-line { background: rgba(0,229,255,.2); }
.mode-mixed .hud-label { color: rgba(0,229,255,.55); }
.mode-mixed .hex-val { color: rgba(0,229,255,.35); }
.mode-mixed .hud-dot { background: rgba(0,229,255,.12); }
.mode-mixed .hud-dot.on { background: rgba(0,229,255,.55); box-shadow: 0 0 6px rgba(0,229,255,.4); }
.mode-mixed .drift-char { color: rgba(255,107,157,.35); }
.mode-mixed .drift-word { color: rgba(255,107,157,.22); }
.mode-mixed .drift-bar { background: rgba(255,107,157,.2); }
.mode-mixed .scan-line { background: linear-gradient(90deg,transparent,rgba(180,77,255,.07),transparent); }
.mode-mixed .scan-dot { background: rgba(180,77,255,.25); }
.mode-mixed .glitch-bar { background: rgba(180,77,255,.03); }
.mode-mixed .flow-dash { background: linear-gradient(90deg,transparent,rgba(255,68,136,.3),transparent); }
.mode-mixed .flow-hex { border-bottom-color: rgba(255,68,136,.12); }
.mode-mixed .flow-label { color: rgba(255,68,136,.3); }

/* ═══ 颜色覆盖: 紫色 ═══ */
.mode-purple .hud-line { background: rgba(167,139,250,.2); }
.mode-purple .hud-label { color: rgba(167,139,250,.55); }
.mode-purple .hex-val { color: rgba(167,139,250,.35); }
.mode-purple .hud-dot { background: rgba(167,139,250,.12); }
.mode-purple .hud-dot.on { background: rgba(167,139,250,.55); box-shadow: 0 0 6px rgba(167,139,250,.4); }
.mode-purple .drift-char { color: rgba(180,77,255,.35); }
.mode-purple .drift-word { color: rgba(180,77,255,.22); }
.mode-purple .drift-bar { background: rgba(180,77,255,.2); }
.mode-purple .scan-line { background: linear-gradient(90deg,transparent,rgba(167,139,250,.07),transparent); }
.mode-purple .scan-dot { background: rgba(167,139,250,.25); }
.mode-purple .glitch-bar { background: rgba(167,139,250,.03); }
.mode-purple .flow-dash { background: linear-gradient(90deg,transparent,rgba(200,150,255,.3),transparent); }
.mode-purple .flow-hex { border-bottom-color: rgba(200,150,255,.12); }
.mode-purple .flow-label { color: rgba(200,150,255,.3); }

/* ═══ 颜色覆盖: 蓝色 ═══ */
.mode-blue .hud-line { background: rgba(68,136,255,.2); }
.mode-blue .hud-label { color: rgba(68,136,255,.55); }
.mode-blue .hex-val { color: rgba(68,136,255,.35); }
.mode-blue .hud-dot { background: rgba(68,136,255,.12); }
.mode-blue .hud-dot.on { background: rgba(68,136,255,.55); box-shadow: 0 0 6px rgba(68,136,255,.4); }
.mode-blue .drift-char { color: rgba(100,160,255,.35); }
.mode-blue .drift-word { color: rgba(100,160,255,.22); }
.mode-blue .drift-bar { background: rgba(100,160,255,.2); }
.mode-blue .scan-line { background: linear-gradient(90deg,transparent,rgba(68,136,255,.07),transparent); }
.mode-blue .scan-dot { background: rgba(68,136,255,.25); }
.mode-blue .glitch-bar { background: rgba(68,136,255,.03); }
.mode-blue .flow-dash { background: linear-gradient(90deg,transparent,rgba(130,180,255,.3),transparent); }
.mode-blue .flow-hex { border-bottom-color: rgba(130,180,255,.12); }
.mode-blue .flow-label { color: rgba(130,180,255,.3); }

/* ── 共享线条 ── */
.hud-line { position: absolute; background: rgba(0,229,255 0.2); }
.line-h { top: 0; left: 0; width: 72px; height: 1px; }
.line-v { top: 0; left: 0; width: 1px; height: 32px; }

/* ═══ 左上 HUD ═══ */
.tl { position: absolute; top: 38px; left: 32px; }

.hud-label {
  position: absolute; top: -20px; left: 12px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 11px; color: rgba(0,229,2550.55); letter-spacing: 0.2em;
  animation: flicker 2.5s ease-in-out infinite;
}

.hud-hex { position: absolute; top: 8px; left: 18px; display: flex; gap: 8px; }
.hex-val {
  font-family: 'JetBrains Mono', monospace; font-size: 9px;
  color: rgba(0,229,2550.35); transition: color 0.3s;
}

.hud-indicators { position: absolute; top: 5px; left: 78px; display: flex; gap: 4px; }
.hud-dot { width: 4px; height: 4px; border-radius: 50%; background: rgba(0,229,2550.12); }
.hud-dot.on { background: rgba(0,229,2550.55); box-shadow: 0 0 6px rgba(0,229,2550.4); }

/* ═══ 全屏数据扰动 ═══ */
.hud-drift {
  position: absolute; inset: 0;
  pointer-events: none; overflow: hidden;
}

/* 游离 HEX 字符块 */
.drift-block {
  position: absolute;
  width: 18px; height: 16px;
  display: flex; align-items: center; justify-content: center;
  animation: drift-flicker 1.8s ease-in-out infinite;
}

.drift-char {
  font-family: 'JetBrains Mono', monospace; font-size: 10px;
  color: rgba(0,229,2550.35);
  transition: all 0.1s;
}

@keyframes drift-flicker {
  0%, 100% { opacity: 0; }
  10% { opacity: 0.5; }
  12% { opacity: 0; }
  15% { opacity: 0.7; }
  17% { opacity: 0.15; }
  25% { opacity: 0; }
  50% { opacity: 0; }
  55% { opacity: 0.3; }
  57% { opacity: 0; }
  80% { opacity: 0; }
  82% { opacity: 0.55; }
  84% { opacity: 0; }
}

/* 断续字幕 */
.drift-word {
  position: absolute;
  font-family: 'JetBrains Mono', monospace; font-size: 8px;
  color: rgba(0,229,2550.22);
  letter-spacing: 0.2em;
  animation: drift-text 3s ease-in-out infinite;
}

@keyframes drift-text {
  0%, 100% { opacity: 0; }
  20% { opacity: 0.4; }
  22% { opacity: 0; }
  35% { opacity: 0.5; }
  36% { opacity: 0.1; }
  38% { opacity: 0.5; }
  40% { opacity: 0; }
  70% { opacity: 0; }
  72% { opacity: 0.35; }
  74% { opacity: 0; }
}

/* 随机横条 */
.drift-bar {
  position: absolute;
  height: 1px;
  background: rgba(0,229,2550.2);
  animation: drift-bar 2.5s ease-in-out infinite;
}

@keyframes drift-bar {
  0%, 100% { opacity: 0; transform: scaleX(0.2); }
  15% { opacity: 0.5; transform: scaleX(1); }
  30% { opacity: 0.1; transform: scaleX(0.5); }
  50% { opacity: 0; transform: scaleX(0); }
  65% { opacity: 0.4; transform: scaleX(0.8); }
  80% { opacity: 0; transform: scaleX(0); }
}

/* ═══ 左下数据流 ═══ */
.data-stream { position: absolute; bottom: 0; left: 0; width: 220px; height: 260px; }
.scan-lines { position: absolute; inset: 0; }
.scan-line {
  position: absolute; left: 0; width: 100%; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0,229,2550.07), transparent);
  animation: scan-up 2.4s linear infinite;
}
@keyframes scan-up { 0%{top:100%;opacity:1} 90%{opacity:1} 100%{top:-1%;opacity:0} }

.scan-dot {
  position: absolute; border-radius: 50%;
  background: rgba(0,229,2550.25);
  animation: dot-beat 3s ease-in-out infinite;
}
@keyframes dot-beat {
  0%,100%{opacity:0;transform:scale(.5)} 20%{opacity:.4} 50%{opacity:.15;transform:scale(1.2)} 80%{opacity:.5}
}

.glitch-bar {
  position: absolute; left: 0; width: 100%;
  background: rgba(0,229,2550.03);
  animation: glitch-pop 0.3s ease-out;
}
@keyframes glitch-pop { 0%{opacity:0;transform:scaleX(.3)} 100%{opacity:1;transform:scaleX(1)} }

/* ═══ 右下横向流动 ═══ */
.hud-flow { position: absolute; bottom: 18px; right: 24px; width: 180px; height: 100px; }
.flow-line {
  position: absolute; left: 0; width: 100%; height: 1px;
  overflow: hidden;
}
.flow-dash {
  position: absolute; top: 0; height: 1px;
  width: 24px; background: linear-gradient(90deg, transparent, rgba(180,77,2550.3), transparent);
  animation: flow-right 2s linear infinite;
}
@keyframes flow-right { 0%{left:-30px} 100%{left:100%} }

.flow-label {
  position: absolute; bottom: 0; right: 0;
  font-family: 'JetBrains Mono', monospace; font-size: 8px;
  color: rgba(180,77,2550.3); letter-spacing: 0.2em;
  animation: flicker 3s ease-in-out infinite;
}
.flow-hex { 
  display: block;
  border-bottom: 1px solid rgba(180,77,2550.12);
  padding-bottom: 2px;
}
</style>
