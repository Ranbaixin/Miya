import { useStorage } from '@vueuse/core'
import { watch } from 'vue'

export interface ThemeColors {
  accent: string
  home: string
  chatAi: string
  chatUser: string
  chatBg: string
  border: string
}

const DEFAULTS: ThemeColors = {
  accent: '#a78bfa',
  home: '#a78bfa',
  chatAi: '#00e5ff',
  chatUser: '#b44dff',
  chatBg: '#0a0815',
  border: '#00e5ff',
}

const theme = useStorage<ThemeColors>('miya-theme-colors', { ...DEFAULTS })

function applyColors(colors: ThemeColors) {
  const root = document.documentElement
  root.style.setProperty('--miya-accent', colors.accent)
  root.style.setProperty('--miya-home', colors.home)
  root.style.setProperty('--miya-chat-ai', colors.chatAi)
  root.style.setProperty('--miya-chat-user', colors.chatUser)
  root.style.setProperty('--miya-chat-bg', colors.chatBg)
  root.style.setProperty('--miya-border', colors.border)
}

watch(theme, applyColors, { deep: true, immediate: true })

export function useThemeColors() {
  return {
    theme,
    resetTheme() {
      theme.value = { ...DEFAULTS }
      applyColors(DEFAULTS)
    },
  }
}
