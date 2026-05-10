import { useStorage } from '@vueuse/core'
import { watch } from 'vue'

export interface ComponentColorDef {
  key: string
  label: string
  cssVar: string
  default: string
}

export interface ColorGroup {
  id: string
  label: string
  icon: string
  colors: ComponentColorDef[]
}

// ─── 全部组件调色定义 ─────────────────────────────────
const COLOR_GROUPS: ColorGroup[] = [
  {
    id: 'message',
    label: '消息卡片',
    icon: '◆',
    colors: [
      { key: 'aiPrimary', label: 'AI 消息主色', cssVar: '--miya-comp-message-ai', default: '#00e5ff' },
      { key: 'userPrimary', label: '用户消息主色', cssVar: '--miya-comp-message-user', default: '#b44dff' },
      { key: 'cardBg', label: '卡片背景', cssVar: '--miya-comp-message-bg', default: '#0a0815' },
      { key: 'inputPrimary', label: '输入框主色', cssVar: '--miya-comp-message-input', default: '#00e5ff' },
      { key: 'textPrimary', label: '文字色', cssVar: '--miya-comp-message-text', default: '#e8d5f5' },
    ],
  },
  {
    id: 'soul',
    label: '灵魂卡片',
    icon: '♥',
    colors: [
      { key: 'cardPrimary', label: '卡片主色', cssVar: '--miya-comp-soul-primary', default: '#00e5ff' },
      { key: 'emotionPositive', label: '积极情绪', cssVar: '--miya-comp-soul-positive', default: '#ff6b9d' },
      { key: 'emotionNegative', label: '消极情绪', cssVar: '--miya-comp-soul-negative', default: '#7dd3fc' },
      { key: 'emotionSurprise', label: '惊喜情绪', cssVar: '--miya-comp-soul-surprise', default: '#facc15' },
      { key: 'thoughtColor', label: '内心独白', cssVar: '--miya-comp-soul-thought', default: '#00e5ff' },
      { key: 'thinkColor', label: '思考过程', cssVar: '--miya-comp-soul-think', default: '#4ade80' },
    ],
  },
  {
    id: 'hud',
    label: 'HUD 覆盖层',
    icon: '◎',
    colors: [
      { key: 'primary', label: '主色调', cssVar: '--miya-comp-hud-primary', default: '#00e5ff' },
      { key: 'secondary', label: '辅色调', cssVar: '--miya-comp-hud-secondary', default: '#b44dff' },
      { key: 'particle', label: '粒子色', cssVar: '--miya-comp-hud-particle', default: '#00e5ff' },
    ],
  },
  {
    id: 'floating',
    label: '悬浮窗',
    icon: '◈',
    colors: [
      { key: 'ballPrimary', label: '球体主色', cssVar: '--miya-comp-floating-ball', default: '#00e5ff' },
      { key: 'ringColor', label: '光环色', cssVar: '--miya-comp-floating-ring', default: '#ac45f1' },
      { key: 'bgColor', label: '背景色', cssVar: '--miya-comp-floating-bg', default: '#110901' },
    ],
  },
  {
    id: 'panel',
    label: '首页面板',
    icon: '✦',
    colors: [
      { key: 'cardBorder', label: '卡片边框', cssVar: '--miya-comp-panel-border', default: '#a78bfa' },
      { key: 'buttonPrimary', label: '按钮主色', cssVar: '--miya-comp-panel-btn', default: '#a78bfa' },
      { key: 'iconColor', label: '图标色', cssVar: '--miya-comp-panel-icon', default: '#a78bfa' },
    ],
  },
  {
    id: 'mind',
    label: '记忆星图',
    icon: '◆',
    colors: [
      { key: 'nodeLine', label: '节点连线', cssVar: '--miya-comp-mind-line', default: '#00e5ff' },
      { key: 'anchorColor', label: '锚点色', cssVar: '--miya-comp-mind-anchor', default: '#ffd700' },
      { key: 'highlightColor', label: '高亮色', cssVar: '--miya-comp-mind-highlight', default: '#00e5ff' },
    ],
  },
  {
    id: 'splash',
    label: '启动画面',
    icon: '◇',
    colors: [
      { key: 'particle', label: '粒子色', cssVar: '--miya-comp-splash-particle', default: '#d4af37' },
      { key: 'progressBar', label: '进度条色', cssVar: '--miya-comp-splash-progress', default: '#d4af37' },
      { key: 'titleGold', label: '标题金色', cssVar: '--miya-comp-splash-title', default: '#d4af37' },
    ],
  },
]

// 扁平化 colors → key→default 映射（供 storage）
function buildDefaults(): Record<string, string> {
  const map: Record<string, string> = {}
  for (const group of COLOR_GROUPS) {
    for (const c of group.colors) {
      map[c.key] = c.default
    }
  }
  return map
}

// ─── 持久化存储 ────────────────────────────────────────
export const componentColors = useStorage<Record<string, string>>(
  'miya-component-colors',
  buildDefaults(),
)

// ─── 注入 CSS custom properties ────────────────────────
function applyComponentColors(colors: Record<string, string>) {
  const root = document.documentElement
  for (const group of COLOR_GROUPS) {
    for (const c of group.colors) {
      root.style.setProperty(c.cssVar, colors[c.key] || c.default)
    }
  }
}

watch(componentColors, applyComponentColors, { deep: true, immediate: true })

// ─── 导出给 ConfigView 使用 ────────────────────────────
export { COLOR_GROUPS }

export function useComponentColors() {
  return {
    groups: COLOR_GROUPS,
    colors: componentColors,
    resetAll() {
      componentColors.value = buildDefaults()
      applyComponentColors(buildDefaults())
    },
    resetGroup(groupId: string) {
      const group = COLOR_GROUPS.find(g => g.id === groupId)
      if (!group) return
      const updated = { ...componentColors.value }
      for (const c of group.colors) {
        updated[c.key] = c.default
      }
      componentColors.value = updated
    },
  }
}
