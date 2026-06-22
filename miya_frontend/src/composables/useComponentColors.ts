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
    id: 'global',
    label: '全局',
    icon: '⬡',
    colors: [
      { key: 'accent', label: '全局主色', cssVar: '--miya-accent', default: '#00ADB5' },
      { key: 'home', label: '首页按钮', cssVar: '--miya-home', default: '#00ADB5' },
      { key: 'chatAi', label: 'AI 消息', cssVar: '--miya-chat-ai', default: '#00FFF5' },
      { key: 'chatUser', label: '用户消息', cssVar: '--miya-chat-user', default: '#00ADB5' },
      { key: 'chatBg', label: '聊天背景', cssVar: '--miya-chat-bg', default: '#222831' },
      { key: 'border', label: '边框光', cssVar: '--miya-border', default: '#00ADB5' },
      { key: 'bg', label: '全局背景', cssVar: '--miya-bg', default: '#222831' },
      { key: 'surface', label: '卡片表面', cssVar: '--miya-surface', default: 'rgba(57, 62, 70, 0.85)' },
      { key: 'gold', label: '金色', cssVar: '--miya-gold', default: 'rgba(0, 255, 245, 0.35)' },
      { key: 'text', label: '主文字', cssVar: '--miya-text', default: '#E4ECF0' },
      { key: 'textDim', label: '次文字', cssVar: '--miya-text-dim', default: 'rgba(228, 236, 240, 0.45)' },
    ],
  },
  {
    id: 'message',
    label: '消息卡片',
    icon: '◆',
    colors: [
      { key: 'aiPrimary', label: 'AI 消息主色', cssVar: '--miya-comp-message-ai', default: '#00FFF5' },
      { key: 'userPrimary', label: '用户消息主色', cssVar: '--miya-comp-message-user', default: '#00ADB5' },
      { key: 'cardBg', label: '卡片背景', cssVar: '--miya-comp-message-bg', default: '#222831' },
      { key: 'inputPrimary', label: '输入框主色', cssVar: '--miya-comp-message-input', default: '#00ADB5' },
      { key: 'textPrimary', label: '文字色', cssVar: '--miya-comp-message-text', default: '#E4ECF0' },
    ],
  },
  {
    id: 'soul',
    label: '灵魂卡片',
    icon: '♥',
    colors: [
      { key: 'cardPrimary', label: '卡片主色', cssVar: '--miya-comp-soul-primary', default: '#00FFF5' },
      { key: 'emotionPositive', label: '积极情绪', cssVar: '--miya-comp-soul-positive', default: '#ff6b9d' },
      { key: 'emotionNegative', label: '消极情绪', cssVar: '--miya-comp-soul-negative', default: '#7dd3fc' },
      { key: 'emotionSurprise', label: '惊喜情绪', cssVar: '--miya-comp-soul-surprise', default: '#facc15' },
      { key: 'thoughtColor', label: '内心独白', cssVar: '--miya-comp-soul-thought', default: '#00ADB5' },
      { key: 'thinkColor', label: '思考过程', cssVar: '--miya-comp-soul-think', default: '#4ade80' },
    ],
  },
  {
    id: 'emotion',
    label: '情绪谱系',
    icon: '♡',
    colors: [
      { key: 'joy', label: '喜悦', cssVar: '--miya-comp-emotion-joy', default: '#ffd700' },
      { key: 'sadness', label: '忧伤', cssVar: '--miya-comp-emotion-sadness', default: '#7dd3fc' },
      { key: 'anger', label: '愤怒', cssVar: '--miya-comp-emotion-anger', default: '#ef4444' },
      { key: 'fear', label: '恐惧', cssVar: '--miya-comp-emotion-fear', default: '#b44dff' },
      { key: 'love', label: '爱', cssVar: '--miya-comp-emotion-love', default: '#ff6b9d' },
      { key: 'surprise', label: '惊喜', cssVar: '--miya-comp-emotion-surprise', default: '#fbbf24' },
      { key: 'neutral', label: '中性', cssVar: '--miya-comp-emotion-neutral', default: '#94a3b8' },
      { key: 'warm', label: '温暖', cssVar: '--miya-comp-emotion-warm', default: '#ff8c69' },
      { key: 'calm', label: '安心', cssVar: '--miya-comp-emotion-calm', default: '#67e8f9' },
      { key: 'sweet', label: '甜蜜', cssVar: '--miya-comp-emotion-sweet', default: '#f472b6' },
      { key: 'nostalgic', label: '怀旧', cssVar: '--miya-comp-emotion-nostalgic', default: '#d8b4fe' },
      { key: 'shy', label: '害羞', cssVar: '--miya-comp-emotion-shy', default: '#fbcfe8' },
      { key: 'anticipation', label: '期待', cssVar: '--miya-comp-emotion-anticipation', default: '#facc15' },
      { key: 'attachment', label: '依恋', cssVar: '--miya-comp-emotion-attachment', default: '#c084fc' },
      { key: 'moved', label: '感动', cssVar: '--miya-comp-emotion-moved', default: '#c4b5fd' },
      { key: 'tender', label: '温柔', cssVar: '--miya-comp-emotion-tender', default: '#a5b4fc' },
      { key: 'curious', label: '好奇', cssVar: '--miya-comp-emotion-curious', default: '#67e8f9' },
    ],
  },
  {
    id: 'hud',
    label: 'HUD 覆盖层',
    icon: '◎',
    colors: [
      { key: 'primary', label: '主色调', cssVar: '--miya-comp-hud-primary', default: '#00FFF5' },
      { key: 'secondary', label: '辅色调', cssVar: '--miya-comp-hud-secondary', default: '#00ADB5' },
      { key: 'particle', label: '粒子色', cssVar: '--miya-comp-hud-particle', default: '#00FFF5' },
    ],
  },
  {
    id: 'floating',
    label: '悬浮窗',
    icon: '◈',
    colors: [
      { key: 'ballPrimary', label: '球体主色', cssVar: '--miya-comp-floating-ball', default: '#00FFF5' },
      { key: 'ringColor', label: '光环色', cssVar: '--miya-comp-floating-ring', default: '#00ADB5' },
      { key: 'bgColor', label: '背景色', cssVar: '--miya-comp-floating-bg', default: '#222831' },
    ],
  },
  {
    id: 'panel',
    label: '首页面板',
    icon: '✦',
    colors: [
      { key: 'cardBorder', label: '卡片边框', cssVar: '--miya-comp-panel-border', default: '#00ADB5' },
      { key: 'buttonPrimary', label: '按钮主色', cssVar: '--miya-comp-panel-btn', default: '#00ADB5' },
      { key: 'iconColor', label: '图标色', cssVar: '--miya-comp-panel-icon', default: '#00ADB5' },
      { key: 'card1', label: '轨道卡 1', cssVar: '--miya-comp-panel-card-1', default: '#ff77aa' },
      { key: 'card2', label: '轨道卡 2', cssVar: '--miya-comp-panel-card-2', default: '#ff9944' },
      { key: 'card3', label: '轨道卡 3', cssVar: '--miya-comp-panel-card-3', default: '#00e88f' },
      { key: 'card4', label: '轨道卡 4', cssVar: '--miya-comp-panel-card-4', default: '#ff5577' },
      { key: 'card5', label: '轨道卡 5', cssVar: '--miya-comp-panel-card-5', default: '#00FFF5' },
      { key: 'card6', label: '轨道卡 6', cssVar: '--miya-comp-panel-card-6', default: '#00ADB5' },
      { key: 'card7', label: '轨道卡 7', cssVar: '--miya-comp-panel-card-7', default: '#00FFF5' },
      { key: 'card8', label: '轨道卡 8', cssVar: '--miya-comp-panel-card-8', default: '#4da6ff' },
      { key: 'card9', label: '轨道卡 9', cssVar: '--miya-comp-panel-card-9', default: '#ff5555' },
      { key: 'card10', label: '轨道卡 10', cssVar: '--miya-comp-panel-card-10', default: '#f59e0b' },
    ],
  },
  {
    id: 'mind',
    label: '记忆星图',
    icon: '◆',
    colors: [
      { key: 'nodeLine', label: '节点连线', cssVar: '--miya-comp-mind-line', default: '#00ADB5' },
      { key: 'anchorColor', label: '锚点色', cssVar: '--miya-comp-mind-anchor', default: '#00FFF5' },
      { key: 'highlightColor', label: '高亮色', cssVar: '--miya-comp-mind-highlight', default: '#00FFF5' },
      { key: 'levelLongTerm', label: '长期记忆', cssVar: '--miya-comp-mind-long-term', default: '#00ADB5' },
      { key: 'levelShortTerm', label: '短期记忆', cssVar: '--miya-comp-mind-short-term', default: '#7dd3fc' },
      { key: 'levelDialogue', label: '对话记忆', cssVar: '--miya-comp-mind-dialogue', default: '#00ADB5' },
      { key: 'levelSemantic', label: '语义记忆', cssVar: '--miya-comp-mind-semantic', default: '#ff6b9d' },
      { key: 'levelKnowledge', label: '知识记忆', cssVar: '--miya-comp-mind-knowledge', default: '#ffd700' },
    ],
  },
  {
    id: 'terminal',
    label: '终端引擎',
    icon: '▸',
    colors: [
      { key: 'bg', label: '背景', cssVar: '--miya-comp-terminal-bg', default: '#0a0a14' },
      { key: 'fg', label: '前景文字', cssVar: '--miya-comp-terminal-fg', default: '#d4d4e8' },
      { key: 'cursor', label: '光标', cssVar: '--miya-comp-terminal-cursor', default: '#00FFF5' },
      { key: 'selection', label: '选区', cssVar: '--miya-comp-terminal-selection', default: '#00FFF544' },
      { key: 'black', label: 'ANSI 黑', cssVar: '--miya-comp-terminal-black', default: '#1a1a2e' },
      { key: 'red', label: 'ANSI 红', cssVar: '--miya-comp-terminal-red', default: '#f87171' },
      { key: 'green', label: 'ANSI 绿', cssVar: '--miya-comp-terminal-green', default: '#34d399' },
      { key: 'yellow', label: 'ANSI 黄', cssVar: '--miya-comp-terminal-yellow', default: '#fbbf24' },
      { key: 'blue', label: 'ANSI 蓝', cssVar: '--miya-comp-terminal-blue', default: '#818cf8' },
      { key: 'magenta', label: 'ANSI 紫', cssVar: '--miya-comp-terminal-magenta', default: '#c084fc' },
      { key: 'cyan', label: 'ANSI 青', cssVar: '--miya-comp-terminal-cyan', default: '#22d3ee' },
      { key: 'white', label: 'ANSI 白', cssVar: '--miya-comp-terminal-white', default: '#e2e8f0' },
      { key: 'brightBlack', label: '亮黑', cssVar: '--miya-comp-terminal-bright-black', default: '#334155' },
      { key: 'brightRed', label: '亮红', cssVar: '--miya-comp-terminal-bright-red', default: '#fca5a5' },
      { key: 'brightGreen', label: '亮绿', cssVar: '--miya-comp-terminal-bright-green', default: '#6ee7b7' },
      { key: 'brightYellow', label: '亮黄', cssVar: '--miya-comp-terminal-bright-yellow', default: '#fde68a' },
      { key: 'brightBlue', label: '亮蓝', cssVar: '--miya-comp-terminal-bright-blue', default: '#a5b4fc' },
      { key: 'brightMagenta', label: '亮紫', cssVar: '--miya-comp-terminal-bright-magenta', default: '#d8b4fe' },
      { key: 'brightCyan', label: '亮青', cssVar: '--miya-comp-terminal-bright-cyan', default: '#67e8f9' },
      { key: 'brightWhite', label: '亮白', cssVar: '--miya-comp-terminal-bright-white', default: '#f8fafc' },
    ],
  },
  {
    id: 'splash',
    label: '启动画面',
    icon: '◇',
    colors: [
      { key: 'particle', label: '粒子色', cssVar: '--miya-comp-splash-particle', default: '#00FFF5' },
      { key: 'progressBar', label: '进度条色', cssVar: '--miya-comp-splash-progress', default: '#00FFF5' },
      { key: 'titleGold', label: '标题金色', cssVar: '--miya-comp-splash-title', default: '#00FFF5' },
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
  // 同步派生变量（依赖 global 组）
  const accent = colors.accent || '#00ADB5'
  root.style.setProperty('--miya-primary', accent)
  root.style.setProperty('--miya-glow', `color-mix(in srgb, ${accent} 30%, transparent)`)
}

watch(componentColors, applyComponentColors, { deep: true, immediate: true })

// ─── 导出给 ConfigView / 消费侧使用 ─────────────────────
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
