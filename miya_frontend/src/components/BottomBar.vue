<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

interface Shortcut {
  id: string
  label: string
  icon: string
  path?: string
  action?: () => void
}

const shortcuts: Shortcut[] = [
  { id: 'home', label: '首页', icon: '⌂', path: '/' },
  { id: 'chat', label: '对话', icon: '◆', path: '/chat' },
  { id: 'voice', label: '语音', icon: '♪', action: () => {} },
  { id: 'float', label: '悬浮', icon: '◈', action: () => {
    window.electronAPI?.floating?.enter()
  } },
  { id: 'config', label: '调谐', icon: '❖', path: '/config' },
]

function handleShortcut(s: Shortcut) {
  if (s.path) router.push(s.path)
  else if (s.action) s.action()
}
</script>

<template>
  <footer class="bottom-bar">
    <button
      v-for="s in shortcuts"
      :key="s.id"
      class="bottom-item"
      :title="s.label"
      @click="handleShortcut(s)"
    >
      <span class="bottom-icon">{{ s.icon }}</span>
      <span class="bottom-label">{{ s.label }}</span>
    </button>
  </footer>
</template>

<style scoped>
.bottom-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.1rem;
  height: 40px;
  min-height: 40px;
  padding: 0 1rem;
  background: transparent;
  border-top: 1px solid rgba(0, 173, 181, 0.04);
  z-index: 60;
  user-select: none;
}

.bottom-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.05rem;
  width: 52px;
  height: 34px;
  background: none;
  border: none;
  cursor: pointer;
  color: rgba(0, 173, 181, 0.35);
  transition: all 0.25s ease;
  position: relative;
}

.bottom-item:hover {
  color: rgba(0, 255, 245, 0.75);
}

.bottom-item::after {
  content: '';
  position: absolute;
  bottom: 2px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 1px;
  background: rgba(0, 255, 245, 0.4);
  transition: width 0.3s ease;
}

.bottom-item:hover::after {
  width: 40%;
}

.bottom-icon {
  font-size: 0.85rem;
  line-height: 1;
}

.bottom-label {
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 0.42rem;
  letter-spacing: 0.05em;
  line-height: 1;
}
</style>
