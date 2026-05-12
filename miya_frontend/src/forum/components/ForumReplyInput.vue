<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  placeholder?: string
}>()

const emit = defineEmits<{
  submit: [payload: { content: string, wantToMeet: boolean }]
}>()

const content = ref('')
const wantToMeet = ref(false)
const submitting = ref(false)

async function handleSubmit() {
  if (!content.value.trim()) return
  submitting.value = true
  try {
    emit('submit', { content: content.value.trim(), wantToMeet: wantToMeet.value })
    content.value = ''
    wantToMeet.value = false
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="reply-input">
    <textarea
      v-model="content"
      :placeholder="placeholder || '写下你的回复...'"
      rows="2"
      class="reply-textarea"
      @keydown.ctrl.enter="handleSubmit"
    />
    <div class="reply-actions">
      <label class="meet-toggle" @click="wantToMeet = !wantToMeet">
        <span class="meet-dot" :class="{ active: wantToMeet }" />
        <span class="meet-label" :class="{ active: wantToMeet }">想要认识!</span>
      </label>
      <button class="send-btn" :disabled="!content.trim() || submitting" @click="handleSubmit">
        {{ submitting ? '...' : '发送' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.reply-input { display: flex; flex-direction: column; gap: 0.4rem; }

.reply-textarea {
  width: 100%; padding: 7px 10px; resize: none; outline: none;
  background: color-mix(in srgb, var(--miya-bg) 90%, transparent);
  border: 1px solid color-mix(in srgb, var(--miya-accent) 10%, transparent);
  border-radius: 5px; color: var(--miya-text); font-size: 0.7rem; line-height: 1.5;
  font-family: inherit; box-sizing: border-box;
}
.reply-textarea:focus { border-color: var(--miya-accent); }
.reply-textarea::placeholder { color: var(--miya-text-dim); }

.reply-actions { display: flex; align-items: center; justify-content: space-between; }

.meet-toggle { display: flex; align-items: center; gap: 0.4rem; cursor: pointer; user-select: none; }
.meet-dot { width: 0.7rem; height: 0.7rem; border-radius: 50%; border: 2px solid var(--miya-text-dim); transition: all 0.2s; }
.meet-dot.active { background: var(--miya-gold); border-color: var(--miya-gold); }
.meet-label { font-size: 0.65rem; color: var(--miya-text-dim); transition: color 0.2s; }
.meet-label.active { color: var(--miya-gold); }

.send-btn {
  padding: 4px 14px; border-radius: 4px; cursor: pointer; font-size: 0.68rem; font-family: inherit;
  background: color-mix(in srgb, var(--miya-accent) 20%, transparent);
  color: var(--miya-accent); border: 1px solid color-mix(in srgb, var(--miya-accent) 25%, transparent);
  transition: all 0.2s;
}
.send-btn:hover:not(:disabled) { background: color-mix(in srgb, var(--miya-accent) 35%, transparent); box-shadow: 0 0 8px var(--miya-glow); }
.send-btn:disabled { opacity: 0.35; cursor: not-allowed; }
</style>
