<script setup lang="ts">
import { ref } from 'vue'
defineProps<{
  emotions?: Array<{ name: string, intensity: number }>
  innerThought?: string
  attribution?: string
  reflection?: string
  thinking?: string
  generating?: boolean
}>()
const thinkingExpanded = ref(false)

const EMOTION_GRADIENTS: Record<string, string> = {
  '喜悦': 'linear-gradient(90deg, #ffd700, #ff8c00)',
  '爱': 'linear-gradient(90deg, #ff6b9d, #ff4488)',
  '温暖': 'linear-gradient(90deg, #ff8c69, #ff6b9d)',
  '满足': 'linear-gradient(90deg, #7dd3fc, #00e5ff)',
  '思念': 'linear-gradient(90deg, #b44dff, #c084fc)',
  '忧伤': 'linear-gradient(90deg, #7dd3fc, #38bdf8)',
  '烦躁': 'linear-gradient(90deg, #f87171, #fb923c)',
  '无奈': 'linear-gradient(90deg, #94a3b8, #cbd5e1)',
  '依恋': 'linear-gradient(90deg, #c084fc, #e879f9)',
  '愤怒': 'linear-gradient(90deg, #ef4444, #f87171)',
  '恐惧': 'linear-gradient(90deg, #a78bfa, #7c3aed)',
  '惊讶': 'linear-gradient(90deg, #facc15, #fbbf24)',
}
</script>

<template>
  <div v-if="emotions?.length || innerThought || generating" class="soul-card" :class="{ loading: generating }">
    <!-- 情绪条 -->
    <div v-if="emotions?.length" class="soul-emotions">
      <div v-for="e in emotions.slice(0, 4)" :key="e.name" class="soul-emotion-item">
        <div class="soul-emotion-bar">
          <div
            class="soul-emotion-fill"
            :style="{
              width: `${e.intensity}%`,
              background: EMOTION_GRADIENTS[e.name] || 'linear-gradient(90deg, #00e5ff, #7dd3fc)',
            }"
          />
        </div>
        <span class="soul-emotion-label">{{ e.name }}</span>
      </div>
    </div>
    <!-- 加载占位 -->
    <div v-if="generating && !emotions?.length" class="soul-loading">
      <span class="soul-pulse" />
      <span>灵魂响应中...</span>
    </div>
    <!-- 内心独白 -->
    <div v-if="innerThought" class="soul-thought">
      <span class="soul-quote">"</span>{{ innerThought }}<span class="soul-quote">"</span>
    </div>
    <!-- 归因+反思 -->
    <div v-if="attribution || reflection" class="soul-meta">
      <div v-if="attribution" class="soul-attribution">→ {{ attribution }}</div>
      <div v-if="reflection" class="soul-reflection">{{ reflection }}</div>
    </div>
    <!-- 思考过程 -->
    <div v-if="thinking" class="soul-thinking">
      <div class="thinking-toggle" @click="thinkingExpanded = !thinkingExpanded">
        <span class="thinking-icon">◇</span>
        <span>{{ thinkingExpanded ? '收起思考' : '展开思考' }}</span>
      </div>
      <div v-if="thinkingExpanded" class="thinking-body">{{ thinking }}</div>
    </div>
  </div>
</template>

<style scoped>
.soul-card {
  position: absolute;
  right: -180px;
  top: 0;
  width: 160px;
  max-height: 200px;
  overflow-y: auto;
  background: rgba(8, 14, 26, 0.92);
  border: 1px solid rgba(0, 229, 255, 0.1);
  padding: 0.6rem;
  font-size: 0.65rem;
  z-index: 5;
  clip-path: polygon(0 4px, 4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%);
  pointer-events: auto;
  opacity: 0.9;
  transition: opacity 0.3s;
}
.soul-card:hover { opacity: 1; }
.soul-card.loading { border-color: rgba(0, 229, 255, 0.25); }

.soul-emotions { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.4rem; }
.soul-emotion-item { display: flex; align-items: center; gap: 0.3rem; }
.soul-emotion-bar { flex: 1; height: 4px; background: rgba(0, 229, 255, 0.06); border-radius: 2px; overflow: hidden; }
.soul-emotion-fill { height: 100%; border-radius: 2px; transition: width 0.5s ease; }
.soul-emotion-label { font-size: 0.55rem; color: rgba(180, 200, 220, 0.5); min-width: 2rem; text-align: right; }

.soul-loading { display: flex; align-items: center; gap: 0.3rem; color: rgba(0, 229, 255, 0.4); font-size: 0.6rem; margin-bottom: 0.3rem; }
.soul-pulse { width: 4px; height: 4px; border-radius: 50%; background: rgba(0, 229, 255, 0.6); animation: soul-dot 1s ease-in-out infinite; }
@keyframes soul-dot { 0%,100%{opacity:.2} 50%{opacity:1;box-shadow:0 0 4px rgba(0,229,255,.6)} }

.soul-thought { font-family: 'Noto Serif SC', serif; font-size: 0.65rem; color: rgba(200, 210, 230, 0.7); line-height: 1.5; margin-bottom: 0.3rem; font-style: italic; }
.soul-quote { color: rgba(0, 229, 255, 0.3); font-size: 0.8rem; }

.soul-meta { display: flex; flex-direction: column; gap: 0.15rem; }
.soul-attribution { color: rgba(0, 229, 255, 0.35); font-size: 0.55rem; line-height: 1.3; }
.soul-reflection { color: rgba(180, 77, 255, 0.3); font-size: 0.55rem; line-height: 1.3; }

.soul-thinking { margin-top: 0.4rem; border-top: 1px solid rgba(0,229,255,0.06); padding-top: 0.3rem; }
.thinking-toggle { display: flex; align-items: center; gap: 0.3rem; cursor: pointer; color: rgba(0,229,255,0.3); font-size: 0.55rem; transition: color 0.2s; }
.thinking-toggle:hover { color: rgba(0,229,255,0.6); }
.thinking-icon { font-size: 0.65rem; }
.thinking-body { margin-top: 0.3rem; font-family: 'JetBrains Mono', monospace; font-size: 0.55rem; color: rgba(160,190,220,0.5); line-height: 1.4; white-space: pre-wrap; word-break: break-word; }
</style>
