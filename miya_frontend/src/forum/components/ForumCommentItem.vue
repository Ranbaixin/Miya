<script setup lang="ts">
import type { ForumComment } from '../types'
import { ref } from 'vue'
import { likeComment } from '../api'

const props = defineProps<{
  comment: ForumComment
  isPostOwner?: boolean
}>()

const liking = ref(false)

function formatTime(iso: string): string {
  const d = new Date(iso)
  const month = d.getMonth() + 1
  const day = d.getDate()
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${month}/${day} ${h}:${m}`
}

async function toggleLike() {
  if (liking.value) return
  liking.value = true
  try {
    const res = await likeComment(props.comment.id)
    props.comment.likesCount = res.likes
    props.comment.liked = res.liked
  } finally {
    liking.value = false
  }
}
</script>

<template>
  <div class="comment-item">
    <div class="flex gap-2">
      <div class="avatar">{{ comment.author.name.charAt(0) }}</div>
      <div class="comment-body">
        <div class="comment-top">
          <span class="comment-author">{{ comment.author.name }}</span>
          <span v-if="comment.author.level" class="comment-lv">Lv.{{ comment.author.level }}</span>
          <span v-if="comment.replyToId" class="comment-reply">回复了评论</span>
          <span class="comment-time">{{ formatTime(comment.createdAt) }}</span>
        </div>
        <div class="comment-content">{{ comment.content }}</div>
        <div v-if="comment.images?.length" class="comment-imgs">
          <img v-for="(img, i) in comment.images" :key="i" :src="img" class="comment-img" @click="$emit('previewImage', img)">
        </div>
        <button class="like-btn" :class="{ liked: comment.liked }" :disabled="liking" @click="toggleLike">
          <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" /></svg>
          {{ comment.likesCount }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.comment-item { padding: 7px 0; border-bottom: 1px solid color-mix(in srgb, var(--miya-accent) 4%, transparent); }
.comment-item:last-child { border-bottom: none; }
.avatar {
  width: 1.6rem; height: 1.6rem; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 0.55rem; flex-shrink: 0;
  background: color-mix(in srgb, var(--miya-gold) 15%, transparent);
  color: var(--miya-gold); border: 1px solid color-mix(in srgb, var(--miya-gold) 25%, transparent);
}
.comment-body { flex: 1; min-width: 0; }
.comment-top { display: flex; align-items: center; gap: 0.3rem; flex-wrap: wrap; }
.comment-author { font-size: 0.65rem; font-weight: 600; color: var(--miya-text); }
.comment-lv { font-size: 0.55rem; color: var(--miya-text-dim); }
.comment-reply { font-size: 0.55rem; color: var(--miya-text-dim); }
.comment-time { font-size: 0.55rem; color: var(--miya-text-dim); margin-left: auto; flex-shrink: 0; }
.comment-content { font-size: 0.65rem; color: var(--miya-text-dim); line-height: 1.5; margin-top: 0.15rem; }
.comment-imgs { display: flex; gap: 0.3rem; margin-top: 0.3rem; flex-wrap: wrap; }
.comment-img { width: 3rem; height: 3rem; border-radius: 3px; object-fit: cover; cursor: pointer; }
.comment-img:hover { filter: brightness(1.2); }
.like-btn {
  display: flex; align-items: center; gap: 0.15rem; margin-top: 0.25rem;
  background: transparent; border: none; cursor: pointer; padding: 0;
  font-size: 0.6rem; color: var(--miya-text-dim); transition: color 0.15s;
}
.like-btn:hover:not(:disabled) { color: var(--miya-text); }
.like-btn.liked { color: var(--miya-gold); }
.like-btn.liked svg { fill: var(--miya-gold); }
.like-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
