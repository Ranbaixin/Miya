<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import API from '@/api/core'

const router = useRouter()

// === Gateway 状态 ===
const gwRunning = ref(false)
const gwChecking = ref(true)
const gwPort = ref(20789)
const result = ref('')
const resultType = ref<'success' | 'error' | ''>('')
const loading = ref(false)
const taskInput = ref('')
const sessionKey = ref('')
const workspace = ref('')
const sessions = ref<{ key: string; label: string }[]>([{ key: '', label: '新会话' }])
const copHistory = ref<{ role: string; content: string; time: string }[]>([])
const showHistory = ref(false)

// === 统一 MCP 调用 ===
async function callMcp(tool: string, params: Record<string, any> = {}) {
  try {
    const resp = await API.mcpCall('openclaw', tool, params)
    return resp
  } catch (e: any) {
    return { success: false, error: e.message }
  }
}

// === 检查状态 ===
async function checkStatus() {
  gwChecking.value = true
  try {
    const res = await callMcp('get_status')
    if (res?.result) {
      const r = typeof res.result === 'string' ? JSON.parse(res.result) : res.result
      gwRunning.value = r?.runtime?.running || false
    }
  } catch { gwRunning.value = false }
  gwChecking.value = false
}

// === 启动 ===
async function startGateway() {
  loading.value = true
  result.value = '正在启动 OpenClaw Gateway...'
  resultType.value = ''
  const res = await callMcp('start_gateway')
  const r = typeof res?.result === 'string' ? JSON.parse(res.result) : res?.result
  if (r?.success) {
    result.value = 'Gateway 已启动成功！端口 ' + gwPort.value
    resultType.value = 'success'
    gwRunning.value = true
  } else {
    result.value = '启动失败: ' + (r?.message || r?.error || '未知错误')
    resultType.value = 'error'
  }
  loading.value = false
}

// === 停止 ===
async function stopGateway() {
  loading.value = true
  result.value = '正在停止 Gateway...'
  resultType.value = ''
  const res = await callMcp('stop_gateway')
  const r = typeof res?.result === 'string' ? JSON.parse(res.result) : res?.result
  if (r?.success) {
    result.value = 'Gateway 已停止'
    resultType.value = 'success'
    gwRunning.value = false
  } else {
    result.value = '停止失败'
    resultType.value = 'error'
  }
  loading.value = false
}

// === 发送任务 ===
async function sendTask() {
  if (!taskInput.value.trim()) return
  loading.value = true
  result.value = '正在执行任务...'
  resultType.value = ''

  copHistory.value.push({ role: 'user', content: taskInput.value, time: new Date().toLocaleTimeString() })

  const params: Record<string, any> = {
    message: taskInput.value,
    timeout: 120,
  }
  if (sessionKey.value) params.session_key = sessionKey.value
  if (workspace.value) params.workspace = workspace.value

  const res = await callMcp('send_message', params)
  const r = typeof res?.result === 'string' ? JSON.parse(res.result) : res?.result

  if (r?.success) {
    result.value = r?.reply || '任务执行完成'
    resultType.value = 'success'
    copHistory.value.push({ role: 'assistant', content: result.value, time: new Date().toLocaleTimeString() })
    if (r?.session_key) {
      sessionKey.value = r.session_key
      const exists = sessions.value.find(s => s.key === r.session_key)
      if (!exists) sessions.value.push({ key: r.session_key, label: `会话 ${sessions.value.length}` })
    }
  } else {
    result.value = '执行失败: ' + (r?.error || '未知错误')
    resultType.value = 'error'
  }
  taskInput.value = ''
  loading.value = false
}

// === 获取历史 ===
async function loadHistory(key: string) {
  if (!key) return
  showHistory.value = true
  copHistory.value = []
  const res = await callMcp('get_history', { session_key: key, limit: 20 })
  const r = typeof res?.result === 'string' ? JSON.parse(res.result) : res?.result
  if (r?.success && r?.messages) {
    for (const m of (r.messages as any[])) {
      const role = m.role === 'user' ? 'user' : 'assistant'
      const content = typeof m.content === 'string' ? m.content : (m.content?.text || JSON.stringify(m.content))
      copHistory.value.push({ role, content, time: '' })
    }
  }
}

onMounted(() => checkStatus())
</script>

<template>
  <div class="ocv-root">
    <!-- 顶栏 -->
    <header class="ocv-header">
      <button class="back-btn" @click="router.push('/')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
      </button>
      <div class="ocv-title-group">
        <span class="ocv-title">OpenClaw 引擎</span>
        <span class="ocv-sub">AI 电脑控制</span>
      </div>
      <div class="ocv-status-row">
        <span class="status-dot" :class="{ online: gwRunning, offline: !gwRunning && !gwChecking, checking: gwChecking }" />
        <span class="status-text">{{ gwChecking ? '检测中' : (gwRunning ? '运行中' : '未启动') }}</span>
      </div>
    </header>

    <!-- 主体 -->
    <div class="ocv-body">
      <!-- 左侧控制面板 -->
      <aside class="ocv-panel">
        <!-- Gateway 控制 -->
        <div class="ocv-card">
          <div class="ocv-card-title">
            <span>⚙ Gateway 控制</span>
            <span class="ocv-card-badge">{{ gwPort }}</span>
          </div>
          <div class="ocv-btn-row">
            <button class="miya-btn primary" :disabled="loading || gwRunning" @click="startGateway">启动</button>
            <button class="miya-btn danger" :disabled="loading || !gwRunning" @click="stopGateway">停止</button>
          </div>
        </div>

        <!-- 会话 -->
        <div class="ocv-card">
          <div class="ocv-card-title">💬 会话</div>
          <select v-model="sessionKey" class="ocv-select" @change="loadHistory(sessionKey)">
            <option v-for="s in sessions" :key="s.key" :value="s.key">{{ s.label }}</option>
          </select>
          <input v-model="workspace" class="ocv-input" placeholder="工作目录 (可选)" />
        </div>

        <!-- 会话历史 -->
        <div v-if="showHistory && copHistory.length" class="ocv-card ocv-mini-history">
          <div class="ocv-card-title">📜 本会话</div>
          <div class="mini-list">
            <div v-for="(m, i) in copHistory.slice(-6)" :key="i" class="mini-item" :class="m.role">
              <span class="mini-role">{{ m.role === 'user' ? '你' : 'AI' }}</span>
              <span class="mini-text">{{ m.content.slice(0, 50) }}{{ m.content.length > 50 ? '...' : '' }}</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 右侧任务区 -->
      <main class="ocv-main">
        <!-- 任务输入 -->
        <div class="ocv-input-area">
          <textarea
            v-model="taskInput"
            class="ocv-textarea"
            placeholder="描述你想让 AI 在电脑上执行的操作..."
            rows="3"
            :disabled="!gwRunning || loading"
            @keydown.ctrl.enter="sendTask"
          />
          <button class="miya-btn primary send-btn" :disabled="!gwRunning || loading || !taskInput.trim()" @click="sendTask">
            {{ loading ? '执行中...' : '发送任务' }}
            <span class="key-hint">Ctrl+Enter</span>
          </button>
        </div>

        <!-- 结果区域 -->
        <div v-if="result" class="ocv-result" :class="resultType">
          <div class="result-label">{{ resultType === 'success' ? '✓ 结果' : resultType === 'error' ? '✗ 错误' : '⟳ 执行中' }}</div>
          <pre class="result-content">{{ result }}</pre>
        </div>

        <!-- 空状态 -->
        <div v-if="!result && gwRunning" class="ocv-empty">
          <span class="empty-icon">⌨</span>
          <span class="empty-text">输入任务描述，让 AI 帮你操作电脑</span>
          <span class="empty-hint">支持: 读写文件 · 执行命令 · 代码生成 · 浏览器自动化 · 应用控制</span>
        </div>

        <div v-if="!gwRunning && !gwChecking" class="ocv-empty">
          <span class="empty-icon">⚡</span>
          <span class="empty-text">Gateway 未启动</span>
          <span class="empty-hint">请先安装 openclaw: npm install -g openclaw<br/>然后点击「启动」按钮</span>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.ocv-root {
  display: flex; flex-direction: column; height: 100%;
  background: var(--miya-bg); color: var(--miya-text);
  font-family: 'Noto Sans SC', sans-serif;
}

/* ── 顶栏 ── */
.ocv-header {
  display: flex; align-items: center; gap: 1rem;
  padding: 0.6rem 1.2rem;
  border-bottom: 1px solid color-mix(in srgb, var(--miya-accent) 10%, transparent);
  background: var(--miya-surface);
  -webkit-app-region: drag;
  flex-shrink: 0;
}
.ocv-header button { -webkit-app-region: no-drag; }

.back-btn {
  width: 2rem; height: 2rem; display: flex; align-items: center; justify-content: center;
  background: transparent; border: 1px solid color-mix(in srgb, var(--miya-accent) 15%, transparent);
  border-radius: 0.5rem; color: var(--miya-text-dim); cursor: pointer;
  transition: all 0.2s; padding: 0;
}
.back-btn:hover { border-color: var(--miya-primary); color: var(--miya-primary); }
.back-btn svg { width: 1rem; height: 1rem; }

.ocv-title-group { display: flex; flex-direction: column; }
.ocv-title { font-size: 0.95rem; font-weight: 600; letter-spacing: 0.05em; }
.ocv-sub { font-size: 0.6rem; color: var(--miya-text-dim); letter-spacing: 0.1em; }

.ocv-status-row { display: flex; align-items: center; gap: 0.4rem; margin-left: auto; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-dot.online { background: #00ADB5; box-shadow: 0 0 8px rgba(0, 173, 181, 0.6); }
.status-dot.offline { background: #ff4757; box-shadow: 0 0 8px rgba(255,71,87,0.4); }
.status-dot.checking { background: #ffa502; animation: pulse 1s infinite; }
.status-text { font-size: 0.7rem; color: var(--miya-text-dim); font-family: 'JetBrains Mono', monospace; }

@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* ── 主体布局 ── */
.ocv-body {
  display: flex; flex: 1; overflow: hidden;
}

/* ── 左侧面板 ── */
.ocv-panel {
  width: 220px; flex-shrink: 0;
  padding: 0.8rem; display: flex; flex-direction: column; gap: 0.6rem;
  border-right: 1px solid color-mix(in srgb, var(--miya-accent) 8%, transparent);
  overflow-y: auto;
}

.ocv-card {
  background: var(--miya-surface);
  border: 1px solid color-mix(in srgb, var(--miya-accent) 10%, transparent);
  border-radius: 0.6rem; padding: 0.7rem;
}
.ocv-card-title { font-size: 0.72rem; font-weight: 600; color: var(--miya-text); margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: space-between; }
.ocv-card-badge { font-size: 0.58rem; color: var(--miya-accent); font-family: 'JetBrains Mono', monospace; }

.ocv-btn-row { display: flex; gap: 0.4rem; }

.miya-btn {
  flex: 1; padding: 0.4rem 0.6rem; border-radius: 0.4rem; border: none; cursor: pointer;
  font-size: 0.72rem; font-weight: 500; font-family: inherit;
  transition: all 0.2s; text-align: center;
}
.miya-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.miya-btn.primary { background: color-mix(in srgb, var(--miya-accent) 25%, transparent); color: var(--miya-accent); border: 1px solid color-mix(in srgb, var(--miya-accent) 30%, transparent); }
.miya-btn.primary:hover:not(:disabled) { background: color-mix(in srgb, var(--miya-accent) 40%, transparent); box-shadow: 0 0 12px var(--miya-glow); }
.miya-btn.danger { background: color-mix(in srgb, #ff4757 15%, transparent); color: #ff6b7a; border: 1px solid color-mix(in srgb, #ff4757 25%, transparent); }
.miya-btn.danger:hover:not(:disabled) { background: color-mix(in srgb, #ff4757 25%, transparent); }

.ocv-select, .ocv-input {
  width: 100%; padding: 0.35rem 0.5rem; margin-top: 0.4rem;
  background: color-mix(in srgb, var(--miya-bg) 90%, transparent);
  border: 1px solid color-mix(in srgb, var(--miya-accent) 12%, transparent);
  border-radius: 0.35rem; color: var(--miya-text); font-size: 0.68rem; font-family: inherit;
  outline: none; box-sizing: border-box;
}
.ocv-select:focus, .ocv-input:focus { border-color: var(--miya-accent); }

/* 迷你会话历史 */
.ocv-mini-history { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.mini-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 0.3rem; font-size: 0.6rem; }
.mini-item { padding: 0.2rem 0.3rem; border-radius: 0.2rem; }
.mini-item.user { background: color-mix(in srgb, #00ADB5 8%, transparent); }
.mini-item.assistant { background: color-mix(in srgb, #00ADB5 8%, transparent); }
.mini-role { font-weight: 600; margin-right: 0.3rem; color: var(--miya-accent); }
.mini-text { color: var(--miya-text-dim); }

/* ── 主区域 ── */
.ocv-main {
  flex: 1; display: flex; flex-direction: column; padding: 0.8rem; overflow: hidden;
}

.ocv-input-area {
  display: flex; flex-direction: column; gap: 0.5rem; flex-shrink: 0;
}

.ocv-textarea {
  width: 100%; padding: 0.7rem; resize: vertical;
  background: var(--miya-surface);
  border: 1px solid color-mix(in srgb, var(--miya-accent) 15%, transparent);
  border-radius: 0.5rem; color: var(--miya-text); font-size: 0.8rem; font-family: inherit;
  outline: none; box-sizing: border-box;
  clip-path: polygon(0 6px, 5px 0, 100% 0, 100% calc(100% - 5px), calc(100% - 5px) 100%, 0 100%);
}
.ocv-textarea:focus { border-color: var(--miya-accent); box-shadow: 0 0 15px rgba(167,139,250,0.1); }
.ocv-textarea::placeholder { color: var(--miya-text-dim); }
.ocv-textarea:disabled { opacity: 0.4; }

.send-btn {
  align-self: flex-end; flex: none !important; padding: 0.5rem 1.2rem;
  display: flex; align-items: center; gap: 0.5rem;
}
.key-hint { font-size: 0.55rem; color: var(--miya-text-dim); opacity: 0.6; }

/* ── 结果 ── */
.ocv-result {
  flex: 1; margin-top: 0.8rem; overflow-y: auto;
  background: var(--miya-surface);
  border: 1px solid color-mix(in srgb, var(--miya-accent) 10%, transparent);
  border-radius: 0.5rem; padding: 0.8rem;
  clip-path: polygon(0 6px, 5px 0, 100% 0, 100% calc(100% - 5px), calc(100% - 5px) 100%, 0 100%);
}
.ocv-result.success { border-color: color-mix(in srgb, #00ADB5 20%, transparent); }
.ocv-result.error { border-color: color-mix(in srgb, #ff4757 20%, transparent); }

.result-label {
  font-size: 0.65rem; font-weight: 600; margin-bottom: 0.5rem; letter-spacing: 0.05em;
}
.ocv-result.success .result-label { color: #00ADB5; }
.ocv-result.error .result-label { color: #ff6b7a; }

.result-content {
  font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.7rem;
  color: var(--miya-text); white-space: pre-wrap; word-break: break-all; line-height: 1.6; margin: 0;
}

/* ── 空状态 ── */
.ocv-empty {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.5rem;
  color: var(--miya-text-dim);
}
.empty-icon { font-size: 2.5rem; opacity: 0.25; }
.empty-text { font-size: 0.8rem; }
.empty-hint { font-size: 0.62rem; opacity: 0.45; text-align: center; line-height: 1.6; }
</style>
