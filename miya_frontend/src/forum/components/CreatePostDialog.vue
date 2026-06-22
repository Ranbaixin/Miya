<script setup lang="ts">
import { ref, watch } from 'vue'
import { createPost } from '../api'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: []; created: [] }>()

const title = ref('')
const content = ref('')
const tags = ref('')
const loading = ref(false)
const error = ref('')

watch(() => props.visible, (v) => {
  if (v) {
    title.value = ''
    content.value = ''
    tags.value = ''
    error.value = ''
  }
})

function parseResult(resp: any): any {
  let r = resp?.result
  if (typeof r === 'string') {
    try { r = JSON.parse(r) } catch { return r }
  }
  return r
}

async function handleCreate() {
  error.value = ''
  if (!title.value.trim() || !content.value.trim()) {
    error.value = '请填写标题和内容'
    return
  }
  loading.value = true
  try {
    const resp = await createPost({
      title: title.value.trim(),
      content: content.value.trim(),
      tags: tags.value.trim()
        ? tags.value.split(',').map(t => t.trim()).filter(Boolean)
        : [],
    })
    const r = parseResult(resp)
    if (r?.success || r?.data?.success) {
      emit('created')
      emit('close')
    } else {
      const err = r?.error || r?.data?.error || r || {}
      error.value = typeof err === 'string' ? err : (err.message || err.detail || '发布失败')
    }
  } catch (e: any) {
    error.value = e?.message || '网络错误'
  } finally {
    loading.value = false
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && e.ctrlKey) handleCreate()
  if (e.key === 'Escape') emit('close')
}
</script>

<template>
  <Transition name="cp-fade">
    <div v-if="visible" class="cp-overlay" @click.self="emit('close')">
      <div class="cp-card">
        <button class="cp-close" @click="emit('close')">&times;</button>
        <div class="cp-header">
          <h3>发布新帖</h3>
          <p class="cp-desc">在娜迦社区分享你的想法</p>
        </div>
        <div class="cp-form" @keydown="handleKeydown">
          <div class="field">
            <label>标题</label>
            <input v-model="title" type="text" placeholder="给你的帖子起个标题" :disabled="loading" maxlength="200" autofocus />
          </div>
          <div class="field">
            <label>内容</label>
            <textarea v-model="content" placeholder="写下你想分享的内容..." :disabled="loading" rows="8" maxlength="10000" />
          </div>
          <div class="field">
            <label>标签（选填，逗号分隔）</label>
            <input v-model="tags" type="text" placeholder="例如：日常, 技术, 闲聊" :disabled="loading" />
          </div>
          <div v-if="error" class="cp-error">{{ error }}</div>
          <div class="cp-actions">
            <button class="cp-cancel" @click="emit('close')">取消</button>
            <button class="cp-submit" :disabled="loading" @click="handleCreate">
              <span v-if="loading" class="cp-spinner"></span>
              <span v-else>发布</span>
            </button>
          </div>
          <p class="cp-hint">Ctrl + Enter 快速发布</p>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.cp-overlay {
  position: fixed; inset: 0; z-index: 80;
  display: flex; align-items: center; justify-content: center;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(4px);
}
.cp-card {
  position: relative; width: 520px;
  border: 1px solid color-mix(in srgb, var(--miya-accent, #00FFF5) 25%, transparent);
  border-radius: 12px;
  background: rgba(20,14,6,0.94);
  box-shadow: 0 0 60px rgba(212,175,55,0.06);
  padding: 1.5rem 2rem 1.8rem;
}
.cp-close {
  position: absolute; top: 0.75rem; right: 0.9rem;
  background: transparent; border: none; color: var(--miya-text-dim);
  font-size: 1.3rem; cursor: pointer; line-height: 1; padding: 0.2rem;
}
.cp-close:hover { color: var(--miya-primary); }

.cp-header { margin-bottom: 1.2rem; }
.cp-header h3 { margin: 0; font-size: 0.95rem; font-weight: 600; color: var(--miya-text); }
.cp-desc { margin: 0.2rem 0 0; font-size: 0.62rem; color: var(--miya-text-dim); }

.cp-form { display: flex; flex-direction: column; gap: 0.7rem; }

.field { display: flex; flex-direction: column; gap: 0.2rem; }
.field label { font-size: 0.62rem; color: var(--miya-text-dim); letter-spacing: 0.05em; }
.field input, .field textarea {
  padding: 0.5rem 0.7rem; border-radius: 6px;
  background: rgba(255,255,255,0.04);
  border: 1px solid color-mix(in srgb, var(--miya-accent, #00FFF5) 15%, transparent);
  color: var(--miya-text); font-size: 0.78rem; font-family: inherit; outline: none;
  transition: border-color 0.2s; resize: vertical;
}
.field input:focus, .field textarea:focus { border-color: var(--miya-accent, #00FFF5); }
.field input::placeholder, .field textarea::placeholder { color: rgba(255,255,255,0.18); }

.cp-error {
  padding: 0.45rem 0.65rem; border-radius: 6px;
  background: rgba(255,75,85,0.08); border: 1px solid rgba(255,75,85,0.2);
  color: #ff6b7a; font-size: 0.68rem;
}

.cp-actions { display: flex; gap: 0.6rem; justify-content: flex-end; margin-top: 0.3rem; }
.cp-cancel, .cp-submit {
  padding: 0.4rem 1rem; border-radius: 5px; font-size: 0.72rem; font-family: inherit; cursor: pointer;
  transition: all 0.2s;
}
.cp-cancel {
  background: transparent; color: var(--miya-text-dim);
  border: 1px solid color-mix(in srgb, var(--miya-text-dim) 20%, transparent);
}
.cp-cancel:hover { border-color: var(--miya-text); color: var(--miya-text); }
.cp-submit {
  background: color-mix(in srgb, var(--miya-accent, #00FFF5) 18%, transparent);
  border: 1px solid color-mix(in srgb, var(--miya-accent, #00FFF5) 25%, transparent);
  color: var(--miya-accent, #00FFF5); display: flex; align-items: center; gap: 0.4rem;
}
.cp-submit:hover:not(:disabled) { background: color-mix(in srgb, var(--miya-accent, #00FFF5) 32%, transparent); }
.cp-submit:disabled { opacity: 0.5; cursor: not-allowed; }

.cp-spinner {
  width: 0.75rem; height: 0.75rem;
  border: 2px solid transparent; border-top-color: var(--miya-accent, #00FFF5);
  border-radius: 50%; animation: cp-spin 0.6s linear infinite;
}
@keyframes cp-spin { to { transform: rotate(360deg); } }

.cp-hint { margin: 0; text-align: center; font-size: 0.58rem; color: rgba(255,255,255,0.15); }

.cp-fade-enter-active, .cp-fade-leave-active { transition: opacity 0.25s ease; }
.cp-fade-enter-from, .cp-fade-leave-to { opacity: 0; }
</style>
