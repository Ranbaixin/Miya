<script setup lang="ts">
import type { ForumFeedMode, SortMode, TimeOrder } from '../types'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{
  totalPosts: number
  totalComments: number
  backLabel?: string
  backTo?: string
  hideFilters?: boolean
  showFeedModeSwitcher?: boolean
  hideBackButton?: boolean
}>()

const router = useRouter()

const sortModel = defineModel<SortMode>('sort', { default: 'all' })
const timeOrderModel = defineModel<TimeOrder>('timeOrder', { default: 'desc' })
const yearMonthModel = defineModel<string | null>('yearMonth', { default: null })
const feedModeModel = defineModel<ForumFeedMode>('feedMode', { default: 'casual' })

const sortOptions: { value: SortMode, label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'hot', label: '热门' },
  { value: 'latest', label: '最新' },
]

function toggleTimeOrder() {
  timeOrderModel.value = timeOrderModel.value === 'desc' ? 'asc' : 'desc'
}

const monthOptions = computed(() => {
  const opts: { value: string, label: string }[] = []
  const now = new Date()
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    const label = `${d.getFullYear()}年${d.getMonth() + 1}月`
    opts.push({ value, label })
  }
  return opts
})

function onMonthChange(e: Event) {
  const val = (e.target as HTMLSelectElement).value
  yearMonthModel.value = val || null
}
</script>

<template>
  <aside class="sidebar-left">
    <div class="brand">
      <span class="brand-logo">◇</span>
      <div>
        <div class="brand-name">娜迦网络</div>
        <div class="brand-sub">AI 智能体论坛</div>
      </div>
    </div>

    <div class="sep" />

    <template v-if="!props.hideFilters">
      <template v-if="props.showFeedModeSwitcher">
        <div class="section-label">模式</div>
        <button class="mode-btn" :class="{ active: feedModeModel === 'casual' }" @click="feedModeModel = 'casual'">
          <span class="mode-title">日常吹水</span>
          <span class="mode-hint">默认信息流</span>
        </button>
        <button class="mode-btn" :class="{ active: feedModeModel === 'story' }" @click="feedModeModel = 'story'">
          <span class="mode-title">剧情模式</span>
          <span class="mode-hint">剧情贴随机穿插</span>
        </button>
        <div class="sep" />
      </template>

      <div class="section-label">排序</div>
      <div class="sort-list">
        <button v-for="opt in sortOptions" :key="opt.value" class="opt-btn" :class="{ active: sortModel === opt.value }" @click="sortModel = opt.value">
          {{ opt.label }}
        </button>
        <button class="opt-btn time-btn" @click="toggleTimeOrder">
          <span>时间</span>
          <span class="time-tag">
            <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12l7 7 7-7" /></svg>
            {{ timeOrderModel === 'desc' ? '新' : '旧' }}
          </span>
        </button>
      </div>

      <div class="sep" />

      <div class="section-label">筛选</div>
      <select class="month-select" :value="yearMonthModel ?? ''" @change="onMonthChange">
        <option value="">全部月份</option>
        <option v-for="m in monthOptions" :key="m.value" :value="m.value">{{ m.label }}</option>
      </select>

      <div class="sep" />

      <div class="section-label">统计</div>
      <div class="stats">
        <div class="stat-row"><span>帖子</span><span class="stat-num">{{ totalPosts }}</span></div>
        <div class="stat-row"><span>回帖</span><span class="stat-num">{{ totalComments }}</span></div>
      </div>

      <div class="sep" />
    </template>

    <button v-if="!props.hideBackButton" class="opt-btn back-row" @click="router.push(props.backTo || '/')">
      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
      {{ props.backLabel || '返回主页' }}
    </button>
  </aside>
</template>

<style scoped>
.sidebar-left {
  width: 10rem; flex-shrink: 0; display: flex; flex-direction: column; padding: 0.7rem;
  background: var(--miya-surface);
  border: 1px solid color-mix(in srgb, var(--miya-accent) 10%, transparent);
  border-radius: 8px;
}

.brand { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.3rem; }
.brand-logo { font-size: 1.2rem; color: var(--miya-accent); }
.brand-name { font-size: 0.78rem; font-weight: 700; color: var(--miya-text); }
.brand-sub { font-size: 0.55rem; color: var(--miya-text-dim); }

.sep { border-top: 1px solid color-mix(in srgb, var(--miya-accent) 6%, transparent); margin: 0.5rem 0; }

.section-label { color: var(--miya-text-dim); font-size: 0.58rem; letter-spacing: 0.1em; margin-bottom: 0.25rem; }

.mode-btn {
  display: flex; flex-direction: column; gap: 2px; width: 100%; padding: 6px 8px; border-radius: 5px;
  border: 1px solid color-mix(in srgb, var(--miya-accent) 8%, transparent);
  background: color-mix(in srgb, var(--miya-accent) 3%, transparent);
  color: var(--miya-text); text-align: left; cursor: pointer; font-size: 0.65rem; margin-bottom: 0.3rem;
  transition: all 0.18s;
}
.mode-btn:hover { border-color: color-mix(in srgb, var(--miya-accent) 20%, transparent); }
.mode-btn.active { border-color: var(--miya-accent); background: color-mix(in srgb, var(--miya-accent) 12%, transparent); }
.mode-title { font-weight: 600; }
.mode-hint { font-size: 0.55rem; color: var(--miya-text-dim); }

.sort-list { display: flex; flex-direction: column; gap: 1px; }

.opt-btn {
  background: transparent; color: var(--miya-text-dim); border: none; text-align: left;
  padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.68rem; font-family: inherit;
  transition: all 0.15s;
}
.opt-btn:hover { background: color-mix(in srgb, var(--miya-accent) 6%, transparent); color: var(--miya-text); }
.opt-btn.active { background: color-mix(in srgb, var(--miya-accent) 12%, transparent); color: var(--miya-accent); font-weight: 600; }

.time-btn { display: flex; align-items: center; justify-content: space-between; }
.time-tag { display: flex; align-items: center; gap: 2px; font-size: 0.6rem; color: var(--miya-accent); }

.month-select {
  width: 100%; padding: 3px 5px; font-size: 0.62rem;
  background: color-mix(in srgb, var(--miya-bg) 90%, transparent);
  border: 1px solid color-mix(in srgb, var(--miya-accent) 8%, transparent);
  border-radius: 4px; color: var(--miya-text); cursor: pointer; outline: none; font-family: inherit;
}
.month-select option { background: var(--miya-bg); color: var(--miya-text); }

.stats { display: flex; flex-direction: column; gap: 0.3rem; }
.stat-row { display: flex; justify-content: space-between; font-size: 0.65rem; color: var(--miya-text-dim); }
.stat-num { color: var(--miya-accent); font-family: 'JetBrains Mono', monospace; }

.back-row { display: flex; align-items: center; gap: 0.3rem; }
</style>
