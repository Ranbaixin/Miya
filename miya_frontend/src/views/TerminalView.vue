<script setup lang="ts">
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { onMounted, onUnmounted, ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const terminalEl = ref<HTMLDivElement>()
const statusText = ref('● 就绪')
const exitCode = ref<number | null>(null)

let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let unsubscribeData: (() => void) | null = null
let unsubscribeExit: (() => void) | null = null
let resizeObserver: ResizeObserver | null = null
let resizeTimer: ReturnType<typeof setTimeout> | null = null

const THEME = {
  background: '#0a0a14',
  foreground: '#d4d4e8',
  cursor: '#a78bfa',
  cursorAccent: '#0a0a14',
  selectionBackground: '#a78bfa44',
  black: '#1a1a2e',
  red: '#f87171',
  green: '#34d399',
  yellow: '#fbbf24',
  blue: '#818cf8',
  magenta: '#c084fc',
  cyan: '#22d3ee',
  white: '#e2e8f0',
  brightBlack: '#334155',
  brightRed: '#fca5a5',
  brightGreen: '#6ee7b7',
  brightYellow: '#fde68a',
  brightBlue: '#a5b4fc',
  brightMagenta: '#d8b4fe',
  brightCyan: '#67e8f9',
  brightWhite: '#f8fafc',
}

function startResizeObserver() {
  if (!terminalEl.value || !term) return
  resizeTimer = null
  resizeObserver = new ResizeObserver(() => {
    if (resizeTimer) clearTimeout(resizeTimer)
    resizeTimer = setTimeout(() => {
      try {
        fitAddon?.fit()
        if (term) {
          window.electronAPI?.terminal.resize(term.cols, term.rows)
        }
      }
      catch (_) { /* ignore */ }
    }, 100)
  })
  resizeObserver.observe(terminalEl.value)
}

function createXterm(): boolean {
  if (!terminalEl.value) return false
  if (term) return true

  term = new Terminal({
    theme: THEME,
    fontSize: 14,
    fontFamily: "'Cascadia Code', 'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
    cursorBlink: true,
    cursorStyle: 'bar',
    allowProposedApi: true,
    disableStdin: false,
    rows: 40,
    cols: 120,
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(terminalEl.value)

  startResizeObserver()

  term.onData((data: string) => {
    window.electronAPI?.terminal.write(data)
  })

  return true
}

function attachToRunning() {
  if (!term) return
  unsubscribeData = window.electronAPI?.terminal.onData((data: string) => {
    term?.write(data)
  }) ?? null

  unsubscribeExit = window.electronAPI?.terminal.onExit((code: number) => {
    exitCode.value = code
    statusText.value = code === 0 ? '● 已退出' : `● 退出 (code ${code})`
    term?.write(`\r\n\x1b[33m── 终端会话结束 (exit code: ${code}) ──\x1b[0m\r\n`)
  }) ?? null
}

function detachFromRunning() {
  unsubscribeData?.()
  unsubscribeExit?.()
  unsubscribeData = null
  unsubscribeExit = null
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeObserver?.disconnect()
  resizeObserver = null
}

function destroyXterm() {
  detachFromRunning()
  term?.dispose()
  term = null
  fitAddon = null
}

async function initTerminal() {
  if (createXterm()) {
    const running = await window.electronAPI?.terminal.isRunning()

    if (running) {
      attachToRunning()
      statusText.value = '● 运行中'

      nextTick(() => {
        try {
          fitAddon?.fit()
          if (term) window.electronAPI?.terminal.resize(term.cols, term.rows)
        } catch (_) { /* ignore */ }
      })

      // Replay buffer
      const buffer = await window.electronAPI?.terminal.getBuffer()
      if (buffer) term?.write(buffer)
    }
    else {
      try {
        statusText.value = '● 启动中...'
        attachToRunning()
        await window.electronAPI?.terminal.start()
        statusText.value = '● 运行中'

        nextTick(() => {
          try { fitAddon?.fit() } catch (_) { /* ignore */ }
        })
      }
      catch (err) {
        statusText.value = `● 启动失败: ${err}`
        term?.write(`\r\n\x1b[31m启动失败: ${err}\x1b[0m\r\n`)
      }
    }
  }
}

function goHome() {
  // Detach xterm but keep the process alive
  detachFromRunning()
  term?.dispose()
  term = null
  fitAddon = null
  router.push('/')
}

function restartTerminal() {
  exitCode.value = null
  window.electronAPI?.terminal.stop()
  destroyXterm()
  nextTick(() => initTerminal())
}

onMounted(() => {
  nextTick(() => initTerminal())
})

onUnmounted(() => {
  destroyXterm()
  // DO NOT stop the terminal process - keep alive for when user returns
})
</script>

<template>
  <div class="terminal-view">
    <div class="terminal-header">
      <div class="header-left">
        <span class="header-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M12 8v8M8 12h8" /></svg>
        </span>
        <span class="header-title">Claude Code Engine v2.4.2</span>
        <span class="header-status" :class="{ running: exitCode === null && statusText.includes('运行'), error: statusText.includes('失败'), exited: exitCode !== null }">
          {{ statusText }}
        </span>
      </div>
      <div class="header-right">
        <button class="header-btn" title="返回主页 (进程保持运行)" @click="goHome">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></svg>
        </button>
        <button class="header-btn" title="重启终端" @click="restartTerminal">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14"><path d="M1 4v6h6M23 20v-6h-6" /><path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15" /></svg>
        </button>
      </div>
    </div>
    <div ref="terminalEl" class="terminal-container" />
  </div>
</template>

<style scoped>
.terminal-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0a0a14;
  border-radius: 8px;
  overflow: hidden;
}

.terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 1rem;
  background: rgba(167, 139, 250, 0.06);
  border-bottom: 1px solid rgba(167, 139, 250, 0.12);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.header-icon {
  color: var(--miya-primary, #a78bfa);
  display: flex;
}

.header-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #d4d4e8;
  letter-spacing: 0.05em;
}

.header-status {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: #64748b;
}

.header-status.running {
  color: rgba(34, 211, 238, 0.8);
}

.header-status.error {
  color: rgba(248, 113, 113, 0.8);
}

.header-status.exited {
  color: rgba(251, 191, 36, 0.8);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.header-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid rgba(167, 139, 250, 0.15);
  background: transparent;
  color: var(--miya-text-dim, #94a3b8);
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
}

.header-btn:hover {
  background: rgba(167, 139, 250, 0.12);
  color: #d4d4e8;
  border-color: rgba(167, 139, 250, 0.3);
}

.terminal-container {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

:deep(.xterm) {
  width: 100%;
  height: 100%;
}

:deep(.xterm-screen) {
  width: 100% !important;
  height: 100% !important;
}

:deep(.xterm-viewport) {
  scrollbar-width: thin;
  scrollbar-color: rgba(167, 139, 250, 0.2) transparent;
}

:deep(.xterm-viewport::-webkit-scrollbar) {
  width: 6px;
}

:deep(.xterm-viewport::-webkit-scrollbar-track) {
  background: transparent;
}

:deep(.xterm-viewport::-webkit-scrollbar-thumb) {
  background: rgba(167, 139, 250, 0.2);
  border-radius: 3px;
}

:deep(.xterm-viewport::-webkit-scrollbar-thumb:hover) {
  background: rgba(167, 139, 250, 0.4);
}
</style>
