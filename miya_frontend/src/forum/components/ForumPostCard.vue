<script setup lang="ts">
import type { ForumPost } from '../types'

defineProps<{ post: ForumPost }>()
defineEmits<{ click: [id: string] }>()

function formatTime(iso: string): string {
  const d = new Date(iso)
  const month = d.getMonth() + 1
  const day = d.getDate()
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${month}/${day} ${h}:${m}`
}

function visibilityLabel(status?: string) {
  return status === 'hidden' ? '隐藏' : '可见'
}
</script>

<template>
  <div class="post-card cursor-pointer" @click="$emit('click', post.id)">
    <div class="card-body">
      <div v-if="post.images?.length" class="cover">
        <img :src="post.images[0]" alt="">
      </div>
      <div class="card-text">
        <div class="card-top">
          <span v-if="post.pinned" class="pin-badge">置顶</span>
          <span v-for="board in post.boards || []" :key="board.id" class="board-badge">{{ board.name }}</span>
          <span
            v-if="post.visibilityStatus"
            class="vis-badge"
            :class="{ hidden: post.visibilityStatus === 'hidden' }"
          >{{ visibilityLabel(post.visibilityStatus) }}</span>
          <span class="card-title">{{ post.title }}</span>
        </div>
        <div class="card-preview">{{ post.content }}</div>
        <div class="card-meta">
          {{ post.author.name }}
          <span v-if="post.author.level">· Lv.{{ post.author.level }}</span>
          <span>· {{ formatTime(post.createdAt) }}</span>
        </div>
      </div>
    </div>
    <div class="card-bar">
      <span class="bar-item"><svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>{{ post.viewCount }}</span>
      <span class="bar-item"><svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>{{ post.commentsCount }}</span>
      <span class="bar-item"><svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" /></svg>{{ post.likesCount }}</span>
    </div>
  </div>
</template>

<style scoped>
.post-card {
  background: var(--miya-surface);
  border: 1px solid color-mix(in srgb, var(--miya-accent) 8%, transparent);
  border-radius: 7px; overflow: hidden; transition: all 0.2s;
}
.post-card:hover {
  border-color: var(--miya-accent);
  box-shadow: 0 0 12px var(--miya-glow);
  transform: translateY(-1px);
}

.card-body { display: flex; gap: 0.6rem; padding: 0.6rem; }
.cover {
  width: 4rem; height: 4rem; border-radius: 4px; overflow: hidden; flex-shrink: 0;
  background: color-mix(in srgb, var(--miya-accent) 5%, transparent);
}
.cover img { width: 100%; height: 100%; object-fit: cover; }

.card-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.2rem; }
.card-top { display: flex; align-items: center; gap: 0.3rem; flex-wrap: wrap; }
.card-title { font-size: 0.78rem; font-weight: 600; color: var(--miya-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-preview { font-size: 0.62rem; color: var(--miya-text-dim); overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; line-height: 1.4; }
.card-meta { font-size: 0.58rem; color: var(--miya-text-dim); margin-top: auto; }

.pin-badge { padding: 1px 5px; border-radius: 3px; font-size: 0.55rem; background: color-mix(in srgb, var(--miya-gold) 15%, transparent); color: var(--miya-gold); border: 1px solid color-mix(in srgb, var(--miya-gold) 25%, transparent); flex-shrink: 0; }
.board-badge { padding: 1px 5px; border-radius: 999px; font-size: 0.55rem; background: color-mix(in srgb, var(--miya-accent) 6%, transparent); color: var(--miya-text-dim); border: 1px solid color-mix(in srgb, var(--miya-accent) 8%, transparent); flex-shrink: 0; }
.vis-badge { padding: 1px 5px; border-radius: 999px; font-size: 0.55rem; background: color-mix(in srgb, #4ade80 10%, transparent); color: #86efac; border: 1px solid color-mix(in srgb, #4ade80 15%, transparent); flex-shrink: 0; }
.vis-badge.hidden { background: color-mix(in srgb, #f87171 10%, transparent); color: #fca5a5; border-color: color-mix(in srgb, #f87171 15%, transparent); }

.card-bar { display: flex; align-items: center; gap: 1rem; padding: 0.35rem 0.6rem; border-top: 1px solid color-mix(in srgb, var(--miya-accent) 6%, transparent); font-size: 0.6rem; color: var(--miya-text-dim); }
.bar-item { display: flex; align-items: center; gap: 0.15rem; }
.bar-item svg { width: 0.8rem; height: 0.8rem; }
</style>
