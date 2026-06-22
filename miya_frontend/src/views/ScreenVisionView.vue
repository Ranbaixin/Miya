<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import API from '@/api/core'
import { MESSAGES } from '@/utils/session'

const router = useRouter()
const query = ref('')
const loading = ref(false)
const result = ref('')
const screenshotPreview = ref('')
const status = ref<'idle' | 'success' | 'error' | 'partial'>('idle')
const screenshots = ref<string[]>([])

function pushToConversation(text: string) {
  MESSAGES.value.push({
    role: 'user',
    content: query.value
      ? `【截屏问题】${query.value}\n\n【AI分析结果】${text}`
      : `【屏幕分析】${text}`,
    sender: '屏幕视觉',
  })
}

async function doLook() {
  if (loading.value) return
  loading.value = true
  result.value = '正在截图并分析...'
  status.value = 'idle'

  // 自动缩窗避免截到自己
  let wasMinimized = false
  try {
    if (window.electronAPI?.minimize) {
      window.electronAPI.minimize()
      wasMinimized = true
      await new Promise(r => setTimeout(r, 800))
    }
  } catch {}

  try {
    const resp = await API.mcpCall('screen_vision', 'look_screen', {
      query: query.value || undefined,
    })
    const r = resp?.result
    const data = typeof r === 'string' ? JSON.parse(r) : r

    if (data?.status === 'success') {
      result.value = data.message
      status.value = 'success'
      pushToConversation(data.message)
      router.push('/chat')
    } else if (data?.status === 'partial') {
      result.value = data.message
      status.value = 'partial'
      pushToConversation(data.message)
      router.push('/chat')
    } else {
      result.value = data?.message || '分析失败'
      status.value = 'error'
    }
  } catch (e: any) {
    result.value = e?.message || '请求失败'
    status.value = 'error'
  }

  // 恢复窗口（路由跳转后 Electron 会自动 focus）
  loading.value = false
}

async function doScreenshot() {
  if (loading.value) return
  loading.value = true

  try {
    const resp = await API.mcpCall('screen_vision', 'screenshot', {})
    const r = resp?.result
    const data = typeof r === 'string' ? JSON.parse(r) : r
    if (data?.status === 'success') {
      screenshots.value.unshift(data.message)
      if (screenshots.value.length > 10) screenshots.value.pop()
      pushToConversation(data.message || '截图完成')
      router.push('/chat')
    }
  } catch (_e) {
    /* stay on page to show error */
  }
  loading.value = false
}
</script>

<template>
  <div class="sv-root">
    <header class="sv-header">
      <button class="back-btn" @click="router.push('/')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
      </button>
      <div class="sv-title-group">
        <span class="sv-title">屏幕视觉</span>
        <span class="sv-sub">截图 · AI 分析</span>
      </div>
    </header>

    <div class="sv-body">
      <div class="sv-controls">
        <textarea
          v-model="query"
          class="sv-textarea"
          placeholder="想问弥娅关于屏幕的问题？（留空则自动描述所有内容）"
          rows="2"
          :disabled="loading"
        />
        <div class="btn-row">
          <button class="miya-btn primary" :disabled="loading" @click="doLook">
            {{ loading ? '分析中...' : '分析屏幕' }}
          </button>
          <button class="miya-btn" :disabled="loading" @click="doScreenshot">只截图</button>
        </div>
      </div>

      <div v-if="result" class="sv-result" :class="status">
        <div class="result-label">
          {{ status === 'success' ? '✓ 分析结果' : status === 'error' ? '✗ 错误' : status === 'partial' ? '⚠ 部分成功' : '⟳ 处理中' }}
        </div>
        <div class="result-content">{{ result }}</div>
      </div>

      <div v-if="!result" class="sv-empty">
        <span class="empty-icon">📷</span>
        <span class="empty-text">点击「分析屏幕」让弥娅帮你看看屏幕上的内容</span>
        <span class="empty-hint">适用于：游戏界面分析 · 错误排查 · 操作指引 · 内容识别</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sv-root { display: flex; flex-direction: column; height: 100%; background: var(--miya-bg); color: var(--miya-text); font-family: 'Noto Sans SC', sans-serif; }

.sv-header {
  display: flex; align-items: center; gap: 1rem; padding: 0.6rem 1.2rem; flex-shrink: 0;
  border-bottom: 1px solid color-mix(in srgb, var(--miya-accent) 10%, transparent);
  background: var(--miya-surface);
}
.back-btn {
  width: 2rem; height: 2rem; display: flex; align-items: center; justify-content: center;
  background: transparent; border: 1px solid color-mix(in srgb, var(--miya-accent) 15%, transparent);
  border-radius: 0.5rem; color: var(--miya-text-dim); cursor: pointer; padding: 0;
}
.back-btn:hover { border-color: var(--miya-primary); color: var(--miya-primary); }
.back-btn svg { width: 1rem; height: 1rem; }
.sv-title-group { display: flex; flex-direction: column; }
.sv-title { font-size: 0.95rem; font-weight: 600; }
.sv-sub { font-size: 0.6rem; color: var(--miya-text-dim); }

.sv-body { flex: 1; padding: 1rem 1.5rem; max-width: 600px; margin: 0 auto; width: 100%; box-sizing: border-box; display: flex; flex-direction: column; gap: 1rem; overflow-y: auto; }

.sv-textarea {
  width: 100%; padding: 0.7rem; resize: vertical; box-sizing: border-box;
  background: var(--miya-surface);
  border: 1px solid color-mix(in srgb, var(--miya-accent) 12%, transparent);
  border-radius: 0.4rem; color: var(--miya-text); font-size: 0.8rem; font-family: inherit; outline: none;
}
.sv-textarea:focus { border-color: var(--miya-accent); }
.sv-textarea::placeholder { color: var(--miya-text-dim); }
.sv-textarea:disabled { opacity: 0.4; }

.btn-row { display: flex; gap: 0.5rem; margin-top: 0.5rem; }

.miya-btn {
  padding: 0.45rem 1rem; border-radius: 0.35rem; cursor: pointer; font-size: 0.72rem; font-family: inherit;
  background: color-mix(in srgb, var(--miya-accent) 10%, transparent);
  color: var(--miya-text-dim); border: 1px solid color-mix(in srgb, var(--miya-accent) 12%, transparent);
  transition: all 0.2s;
}
.miya-btn:hover:not(:disabled) { color: var(--miya-accent); background: color-mix(in srgb, var(--miya-accent) 20%, transparent); }
.miya-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.miya-btn.primary {
  background: color-mix(in srgb, var(--miya-accent) 22%, transparent);
  color: var(--miya-accent); border: 1px solid color-mix(in srgb, var(--miya-accent) 28%, transparent);
}
.miya-btn.primary:hover:not(:disabled) { background: color-mix(in srgb, var(--miya-accent) 38%, transparent); box-shadow: 0 0 10px var(--miya-glow); }

.sv-result {
  background: var(--miya-surface); border-radius: 0.5rem; padding: 1rem;
  border: 1px solid color-mix(in srgb, var(--miya-accent) 10%, transparent);
}
.sv-result.success { border-color: color-mix(in srgb, #00ADB5 15%, transparent); }
.sv-result.error { border-color: color-mix(in srgb, #ff4757 15%, transparent); }
.sv-result.partial { border-color: color-mix(in srgb, #ffa502 15%, transparent); }
.result-label { font-size: 0.65rem; font-weight: 600; margin-bottom: 0.5rem; }
.sv-result.success .result-label { color: #00ADB5; }
.sv-result.error .result-label { color: #ff6b7a; }
.sv-result.partial .result-label { color: #ffa502; }
.result-content { font-size: 0.75rem; line-height: 1.7; color: var(--miya-text); white-space: pre-wrap; }

.sv-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.5rem; color: var(--miya-text-dim); }
.empty-icon { font-size: 2.5rem; opacity: 0.25; }
.empty-text { font-size: 0.8rem; }
.empty-hint { font-size: 0.62rem; opacity: 0.45; }
</style>
