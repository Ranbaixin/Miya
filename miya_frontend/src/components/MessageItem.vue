<script setup lang="ts">
import type { Message, ToolEvent } from '@/utils/session'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { CONFIG } from '@/utils/config'
import Markdown from './Markdown.vue'
import SoulCard from './SoulCard.vue'

const props = defineProps<Message>()

const ROLE_MAP: Record<string, string> = {
  assistant: '弥娅',
  user: CONFIG.value.ui.user_name || '我',
  system: 'SYS',
  error: 'ERR',
}
const ROLE_PREFIX: Record<string, string> = {
  assistant: 'AI',
  user: 'USR',
  system: 'SYS',
  error: 'ERR',
}
const ROLE_COLOR_VAR: Record<string, string> = {
  assistant: '--miya-chat-ai',
  user: '--miya-chat-user',
  system: '--miya-chat-ai',
  error: '#f87171',
}

const reasoningExpanded = ref(true)
const detailOpen = ref(false)

// 情绪数据
const EMOTION_COLORS: Record<string, string> = {
  'joy': '#ffd700', '喜悦': '#ffd700', '爱': '#ff6b9d', '心动': '#ff6b9d',
  '温暖': '#ff8c69', '安心': '#7dd3fc', '满足': '#a78bfa',
  '挂念': '#b44dff', '思念': '#c084fc', '害羞': '#fbbfca',
  '期待': '#facc15', '依恋': '#e879f9', '忧伤': '#38bdf8',
  'sadness': '#38bdf8', 'anger': '#ef4444', 'fear': '#7c3aed',
  'surprise': '#fbbf24', 'disgust': '#94a3b8', '幸福': '#ff8c69',
  '甜蜜': '#f472b6', '温柔': '#a5b4fc', '感动': '#c4b5fd',
  '好奇': '#67e8f9', '怀旧': '#d8b4fe', '心疼': '#fb7185',
}

const soulBars = computed(() => {
  const emos = props.soulData?.emotions
  if (!emos?.length) return []
  const total = emos.reduce((s, e) => s + e.intensity, 1) || 1
  return emos.slice(0, 5).map(e => ({
    name: e.name, intensity: e.intensity,
    color: EMOTION_COLORS[e.name] || '#00e5ff',
    width: Math.round((e.intensity / total) * 100),
  }))
})

const emotionList = computed(() => {
  const emos = props.soulData?.emotions
  if (emos?.length) return emos.slice(0, 5).map(e => ({ name: e.name, pct: e.intensity, color: EMOTION_COLORS[e.name] || '#00e5ff' }))
  return []
})

const emotionText = computed(() => {
  const emos = props.soulData?.emotions
  if (!emos?.length) return ''
  return emos.slice(0, 6).map(e => `${e.name} ${e.intensity}%`).join(' · ')
})

const soulDetail = computed(() => props.soulData || null)

const displaySource = computed(() => {
  if (typeof props.content === 'string') return props.content
  return JSON.stringify(props.content, null, 2)
})

function formatToolPayload(value: any): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  try { return JSON.stringify(value, null, 2) } catch { return String(value) }
}
function toolSummary(event: ToolEvent): string {
  const name = event.name || '工具'
  if (event.type === 'tool_call') return `▸ ${name}`
  return `${event.isError ? '✕' : '✓'} ${name}`
}
function toolBody(event: ToolEvent): string {
  if (event.type === 'tool_call') return formatToolPayload(event.args)
  return formatToolPayload(event.result)
}

const scanLine = ref(false)
let scanTimer: ReturnType<typeof setInterval> | null = null

// 使用消息携带的灵魂数据（来自 API 响应）
const soulData = computed(() => {
  if (props.role !== 'assistant') return null
  const sd = (props as any).soulData
  // 总是展示灵魂卡片（即使数据为空也至少有情绪）
  if (sd?.emotions?.length) return sd
  // 降级：从 emotion data 生成
  const emo = (props as any).emotionDataRaw || (props as any).soulRaw || {}
  const emotions = Object.entries(emo.current || emo)
    .filter(([k]) => !['dominant', 'intensity'].includes(k))
    .map(([name, val]: any) => ({ name, intensity: typeof val === 'number' ? Math.round(val * 100) : 50 }))
  if (emotions.length) return { emotions }
  return null
})
onMounted(() => {
  if (props.generating) {
    scanTimer = setInterval(() => { scanLine.value = !scanLine.value }, 600)
  }
})
onUnmounted(() => { if (scanTimer) clearInterval(scanTimer) })
watch(() => props.generating, (v) => {
  if (v && !scanTimer) scanTimer = setInterval(() => { scanLine.value = !scanLine.value }, 600)
  else if (!v && scanTimer) { clearInterval(scanTimer); scanTimer = null }
})
</script>

<template>
  <div v-if="role === 'info'" class="info-divider">
    <span class="info-text">{{ content }}</span>
  </div>
  <div v-else class="msg-card" :class="[role, { generating }]" :style="{ '--role-color': ROLE_COLOR_VAR[role] || 'var(--miya-chat-ai)' }">
    <!-- 角 bracket -->
    <div class="card-bracket tl" />
    <div class="card-bracket br" />

    <!-- 情绪条 + 数据条 -->
    <div class="card-bar row-group">
      <span class="bar-id">{{ ROLE_PREFIX[role] }}</span>
      <span class="bar-sender">{{ sender ?? ROLE_MAP[role] }}</span>

      <!-- 情绪光带 (仅 AI) -->
      <div v-if="role === 'assistant' && soulBars.length" class="bar-emotion-strip">
        <div
          v-for="b in soulBars" :key="b.name"
          class="bar-emotion-seg"
          :style="{ background: b.color, width: `${b.width}%` }"
          :title="`${b.name} ${b.intensity}%`"
        />
      </div>

      <span v-if="generating" class="bar-status">
        <span class="bar-pulse" />
        <span>{{ status || 'LINK' }}</span>
      </span>

      <!-- 展开按钮 -->
      <button
        v-if="role === 'assistant' && !generating"
        class="bar-expand-btn"
        @click="detailOpen = !detailOpen"
        :title="detailOpen ? '收起' : '查看灵魂'"
      >{{ detailOpen ? '▲' : '▼' }}</button>
    </div>

    <!-- 扫描线 (生成中) -->
    <div v-if="generating" class="card-scan" :class="{ flicker: scanLine }" />

    <!-- 思考过程 -->
    <div v-if="reasoning" class="card-reason">
      <div class="reason-toggle" @click="reasoningExpanded = !reasoningExpanded">
        <span class="reason-dot" :class="{ pulse: generating }" />
        <span class="reason-label">{{ generating ? '◈ PROCESSING' : '◈ COGNITION' }}</span>
        <span v-if="!generating" class="reason-arrow">{{ reasoningExpanded ? '▲' : '▼' }}</span>
      </div>
      <div v-show="reasoningExpanded" class="reason-body">
        <Markdown :source="reasoning" />
      </div>
    </div>

    <!-- 消息内容 -->
    <div class="card-body" :class="{ wait: !content && !reasoning && generating }">
      <div v-if="!content && !reasoning && generating && status" class="card-waiting">
        <span class="wait-cursor">▌</span>
        <span>{{ status }}</span>
      </div>
      <Markdown v-else :source="displaySource" />

      <!-- 工具事件 -->
      <div v-if="toolEvents?.length" class="card-tools">
        <details v-for="(event, idx) in toolEvents" :key="idx" class="tool-block">
          <summary>{{ toolSummary(event) }}</summary>
          <pre v-if="toolBody(event)">{{ toolBody(event) }}</pre>
        </details>
      </div>
    </div>

    <!-- 灵魂详情面板 -->
    <div v-if="role === 'assistant' && detailOpen" class="soul-detail">
      <div class="soul-section emotion-section">
        <div class="soul-section-title">♥ 情绪分析</div>
        <div v-if="emotionList.length" class="soul-emotion-list">
          <div v-for="e in emotionList" :key="e.name" class="soul-emotion-row">
            <span class="soul-em-name">{{ e.name }}</span>
            <div class="soul-em-bar">
              <div class="soul-em-fill" :style="{ width: `${e.pct}%`, background: e.color }" />
            </div>
            <span class="soul-em-val">{{ e.pct }}%</span>
          </div>
        </div>
        <div v-else class="soul-section-text dim">加载中...</div>
      </div>
      <div v-if="soulDetail?.innerThought && soulDetail.innerThought !== '正常对话互动'" class="soul-section thought-section">
        <div class="soul-section-title">✦ 内心独白</div>
        <div class="soul-section-text thought-text">{{ soulDetail.innerThought }}</div>
      </div>
      <div v-if="soulDetail?.attribution && soulDetail.attribution !== '正常对话互动'" class="soul-section attrib-section">
        <div class="soul-section-title">→ 归因</div>
        <div class="soul-section-text dim">{{ soulDetail.attribution }}</div>
      </div>
      <div v-if="soulDetail?.reflection" class="soul-section reflection-section">
        <div class="soul-section-title">↻ 反思</div>
        <div class="soul-section-text dim">{{ soulDetail.reflection }}</div>
      </div>
      <div v-if="soulDetail?.thinking" class="soul-section thinking-section">
        <div class="soul-section-title">◇ 思考过程</div>
        <div class="soul-section-text code">{{ soulDetail.thinking }}</div>
      </div>

      <!-- SoulCard 浮动卡片 -->
      <SoulCard
        v-if="role === 'assistant' && soulDetail"
        :emotions="soulDetail.emotions"
        :inner-thought="soulDetail.innerThought"
        :attribution="soulDetail.attribution"
        :reflection="soulDetail.reflection"
        :thinking="soulDetail.thinking"
        :generating="generating"
      />
    </div>
  </div>
</template>

<style scoped>
.msg-card {
  position: relative; padding: .8rem 1rem .6rem;
  background: linear-gradient(135deg, rgba(8,16,28,.7), rgba(10,20,35,.5));
  border: 1px solid rgba(0,229,255,.12);
  clip-path: polygon(0 8px, 6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%);
  overflow: visible;
  transition: border-color .4s;
}
.msg-card.user { background: linear-gradient(135deg, rgba(15,10,25,.7), rgba(20,12,30,.5)); border-color: rgba(180,77,255,.12); }
.msg-card.generating { border-color: rgba(0,229,255,.45); animation: card-glow 2.5s ease-in-out infinite; }
.msg-card.user.generating { border-color: rgba(180,77,255,.45); animation: card-glow-u 2.5s ease-in-out infinite; }
@keyframes card-glow { 0%,100%{border-color:rgba(0,229,255,.18)} 50%{border-color:rgba(0,229,255,.5)} }
@keyframes card-glow-u { 0%,100%{border-color:rgba(180,77,255,.18)} 50%{border-color:rgba(180,77,255,.5)} }

/* bracket */
.card-bracket { position:absolute; z-index:1; pointer-events:none; }
.card-bracket.tl { top:1px; left:1px; width:10px; height:10px; border-top:1px solid rgba(0,229,255,.45); border-left:1px solid rgba(0,229,255,.45); }
.card-bracket.br { bottom:1px; right:1px; width:6px; height:6px; border-bottom:1px solid rgba(0,229,255,.2); border-right:1px solid rgba(0,229,255,.2); }
.msg-card.user .card-bracket.tl { border-color: rgba(180,77,255,.45) rgba(180,77,255,.45) transparent transparent; }

/* bar */
.card-bar { display:flex; align-items:center; gap:.5rem; padding-bottom:.4rem; margin-bottom:.5rem; border-bottom:1px solid rgba(0,229,255,.08); font-family:'JetBrains Mono',monospace; font-size:.65rem; }
.msg-card.user .card-bar { border-color: rgba(180,77,255,.08); }
.bar-id { color:rgba(0,229,255,.65); font-weight:700; letter-spacing:.1em; border-right:1px solid rgba(0,229,255,.12); padding-right:.5rem; }
.msg-card.user .bar-id { color: rgba(180,77,255,.65); border-color: rgba(180,77,255,.12); }
.bar-sender { color:rgba(0,229,255,.85); letter-spacing:.05em; }
.msg-card.user .bar-sender { color: rgba(180,77,255,.85); }
.bar-status { display:flex; align-items:center; gap:.3rem; margin-left:auto; color:rgba(0,229,255,.35); font-size:.6rem; }
.bar-pulse { width:4px; height:4px; border-radius:50%; background:rgba(0,229,255,.6); animation:dot-pulse 1s ease-in-out infinite; }
@keyframes dot-pulse { 0%,100%{opacity:.25;box-shadow:none} 50%{opacity:1;box-shadow:0 0 6px rgba(0,229,255,.7)} }

/* scan */
.card-scan { position:absolute; left:0; width:100%; height:1px; background:linear-gradient(90deg,transparent,rgba(0,229,255,.12),transparent); transition:top .4s,opacity .2s; top:0; opacity:0; }
.card-scan.flicker { top:50%; opacity:1; }

/* reason */
.card-reason { margin:0 0 .6rem; border:1px solid rgba(0,229,255,.06); background:rgba(0,8,20,.5); clip-path:polygon(0 4px,4px 0,100% 0,100% 100%,0 100%); }
.reason-toggle { display:flex; align-items:center; gap:.4rem; padding:.35rem .6rem; cursor:pointer; user-select:none; font-family:'JetBrains Mono',monospace; font-size:.65rem; color:rgba(0,229,255,.35); transition:color .2s; }
.reason-toggle:hover { color:rgba(0,229,255,.7); }
.reason-dot { width:4px; height:4px; border-radius:50%; background:rgba(0,229,255,.35); }
.reason-dot.pulse { animation:dot-pulse 1s ease-in-out infinite; }
.reason-arrow { margin-left:auto; font-size:.55rem; }
.reason-body { padding:.2rem .6rem .5rem; border-top:1px solid rgba(0,229,255,.04); font-size:.75rem; color:rgba(180,200,220,.65); line-height:1.5; }

/* body */
.card-body { font-size:.88rem; line-height:1.7; color:rgba(210,225,245,.9); overflow-wrap:break-word; word-break:break-word; min-width:0; }
.card-body :deep(pre) { background:rgba(0,8,18,.8); border:1px solid rgba(0,229,255,.1); border-left:2px solid rgba(0,229,255,.25); padding:.6rem .8rem; overflow-x:auto; font-family:'JetBrains Mono',monospace; font-size:.75rem; color:rgba(160,200,240,.85); }
.msg-card.user .card-body :deep(pre) { border-color:rgba(180,77,255,.1); border-left-color:rgba(180,77,255,.25); }
.card-body :deep(code) { background:rgba(0,229,255,.05); color:rgba(0,229,255,.8); padding:.12em .35em; font-size:.85em; }
.card-body :deep(pre code) { background:none; color:inherit; padding:0; }
.msg-card.user .card-body :deep(code) { background:rgba(180,77,255,.05); color:rgba(180,77,255,.8); }
.card-body :deep(blockquote) { border-left:2px solid rgba(0,229,255,.3); background:rgba(0,229,255,.025); padding:.35rem .7rem; margin:.4rem 0; }
.msg-card.user .card-body :deep(blockquote) { border-left-color:rgba(180,77,255,.3); }

/* wait */
.card-waiting { display:flex; align-items:center; gap:.4rem; color:rgba(0,229,255,.35); font-family:'JetBrains Mono',monospace; font-size:.75rem; }
.wait-cursor { animation:blinker .7s step-end infinite; color:rgba(0,229,255,.55); }
@keyframes blinker { 0%,100%{opacity:1} 50%{opacity:0} }

/* tools */
.card-tools { margin-top:.5rem; padding-top:.3rem; border-top:1px solid rgba(0,229,255,.05); }
.tool-block { margin:.15rem 0; font-size:.7rem; color:rgba(0,229,255,.35); }
.tool-block summary { cursor:pointer; padding:.15rem 0; }
.tool-block summary:hover { color:rgba(0,229,255,.65); }
.tool-block pre { background:rgba(0,5,15,.8); border:1px solid rgba(0,229,255,.06); padding:.4rem; font-size:.65rem; color:rgba(140,190,230,.6); overflow-x:auto; white-space:pre-wrap; font-family:'JetBrains Mono',monospace; }

/* divider */
.info-divider { display:flex; align-items:center; gap:.6rem; padding:.3rem 0; }
.info-divider::before,.info-divider::after { content:''; flex:1; height:1px; background:linear-gradient(90deg,transparent,rgba(0,229,255,.12),transparent); }
.info-text { font-family:'JetBrains Mono',monospace; font-size:.6rem; color:rgba(0,229,255,.25); white-space:nowrap; }

/* 情绪光带 */
.bar-emotion-strip { display:flex; flex:1; min-width:60px; height:3px; border-radius:2px; overflow:hidden; gap:1px; opacity:.8; margin:0 .25rem; }
.bar-emotion-seg { height:100%; border-radius:1px; transition:width .5s ease; }
.bar-expand-btn { margin-left:auto; padding:0 4px; border:1px solid rgba(0,229,255,.15); border-radius:3px; background:rgba(0,229,255,.04); color:rgba(0,229,255,.4); cursor:pointer; font-size:.55rem; line-height:1.2; transition:all .2s; }
.bar-expand-btn:hover { border-color:rgba(0,229,255,.4); color:rgba(0,229,255,.7); background:rgba(0,229,255,.08); }

/* 灵魂详情面板 */
.soul-detail {
  margin: 0.5rem 0 0;
  padding: 0.6rem;
  border: 1px solid rgba(0, 229, 255, 0.1);
  background: linear-gradient(135deg, rgba(0, 6, 16, 0.7), rgba(4, 10, 22, 0.5));
  border-radius: 4px;
  font-size: 0.7rem;
  transition: all 0.3s ease;
  overflow: hidden;
}
.soul-section {
  margin-bottom: 0.6rem;
  padding-left: 0.5rem;
  border-left: 2px solid rgba(0, 229, 255, 0.15);
}
.soul-section:last-child {
  margin-bottom: 0;
}
.soul-section.emotion-section { border-left-color: rgba(255, 170, 80, 0.3); }
.soul-section.thought-section { border-left-color: rgba(160, 180, 255, 0.3); }
.soul-section.attrib-section { border-left-color: rgba(0, 229, 255, 0.3); }
.soul-section.reflection-section { border-left-color: rgba(180, 77, 255, 0.3); }
.soul-section.thinking-section { border-left-color: rgba(80, 200, 120, 0.3); }

.soul-section-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  color: rgba(0, 229, 255, 0.45);
  letter-spacing: 0.08em;
  margin-bottom: 0.3rem;
}
.soul-section-text {
  color: rgba(200, 215, 240, 0.7);
  line-height: 1.55;
  font-size: 0.72rem;
}
.soul-section-text.dim {
  color: rgba(0, 229, 255, 0.35);
  font-size: 0.67rem;
}
.soul-section-text.code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  color: rgba(160, 200, 180, 0.6);
  background: rgba(0, 8, 16, 0.5);
  border: 1px solid rgba(0, 229, 255, 0.06);
  border-radius: 3px;
  padding: 0.4rem 0.5rem;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
}
.thought-text {
  font-family: 'Noto Serif SC', serif;
  font-style: italic;
  color: rgba(200, 215, 240, 0.75);
  padding: 0.3rem 0.4rem;
  background: rgba(160, 180, 255, 0.04);
  border-radius: 3px;
}
/* 情绪可视化条 */
.soul-emotion-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.soul-emotion-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.soul-em-name {
  font-size: 0.6rem;
  color: rgba(200, 215, 240, 0.55);
  width: 2.5rem;
  text-align: right;
  flex-shrink: 0;
}
.soul-em-bar {
  flex: 1;
  height: 5px;
  background: rgba(0, 229, 255, 0.06);
  border-radius: 3px;
  overflow: hidden;
}
.soul-em-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.soul-em-val {
  font-size: 0.55rem;
  color: rgba(0, 229, 255, 0.3);
  width: 2rem;
  text-align: right;
  font-family: 'JetBrains Mono', monospace;
  flex-shrink: 0;
}
</style>
