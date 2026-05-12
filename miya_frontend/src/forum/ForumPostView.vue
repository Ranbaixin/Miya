<script setup lang="ts">
import type { ForumPostDetail } from './types'
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Markdown from '@/components/Markdown.vue'
import { fetchPost, likePost, createComment } from './api'
import ForumCommentItem from './components/ForumCommentItem.vue'
import ForumReplyInput from './components/ForumReplyInput.vue'

const route = useRoute()
const router = useRouter()

const post = ref<ForumPostDetail | null>(null)
const showReply = ref(false)

onMounted(async () => {
  const id = route.params.id as string
  post.value = await fetchPost(id)
})

function goBack() { router.push('/community') }

async function toggleLike() {
  if (!post.value) return
  const res = await likePost(post.value.id)
  post.value.likesCount = res.likes
  post.value.liked = res.liked
}

async function onComment(payload: { content: string, wantToMeet: boolean }) {
  if (!post.value) return
  await createComment({ postId: post.value.id, content: payload.content, wantToMeet: payload.wantToMeet })
  // 刷新评论
  post.value = await fetchPost(post.value.id)
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<template>
  <div class="fpv-root">
    <header class="fpv-header">
      <button class="back-btn" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
      </button>
      <span class="fpv-label">返回列表</span>
    </header>

    <div v-if="post" class="fpv-body">
      <!-- 作者 -->
      <div class="author-row">
        <div class="avatar">{{ post.author.name.charAt(0) }}</div>
        <div>
          <div class="author-name">{{ post.author.name }} <span class="author-lv">Lv.{{ post.author.level }}</span></div>
          <div class="author-time">{{ formatTime(post.createdAt) }}</div>
        </div>
      </div>

      <!-- 标题 + 标签 -->
      <h2 class="post-title">{{ post.title }}</h2>
      <div v-if="post.boards?.length" class="board-row">
        <span v-for="b in post.boards" :key="b.id" class="board-tag">{{ b.name }}</span>
      </div>

      <!-- Markdown -->
      <div class="post-content">
        <Markdown :source="post.content" />
      </div>

      <!-- 图片 -->
      <div v-if="post.images?.length" class="img-grid">
        <img v-for="(src, i) in post.images" :key="i" :src="src" class="img-item">
      </div>

      <!-- 互动栏 -->
      <div class="action-bar">
        <span class="action-item"><svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>{{ post.viewCount }}</span>
        <span class="action-item"><svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>{{ post.commentList?.length || 0 }}</span>
        <button class="action-item like-btn" :class="{ liked: post.liked }" @click="toggleLike">
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" /></svg>{{ post.likesCount }}
        </button>
      </div>

      <!-- 评论 -->
      <div class="comments-section">
        <div class="comments-head" @click="showReply = !showReply">
          <span>评论 ({{ post.commentList?.length || 0 }})</span>
          <span class="reply-toggle">{{ showReply ? '收起' : '回复' }}</span>
        </div>
        <ForumReplyInput v-if="showReply" @submit="onComment" />

        <div class="comments-list">
          <ForumCommentItem v-for="c in post.commentList" :key="c.id" :comment="c" />
          <div v-if="!post.commentList?.length" class="no-comments">暂无评论</div>
        </div>
      </div>
    </div>

    <div v-else class="fpv-loading">加载中...</div>
  </div>
</template>

<style scoped>
.fpv-root { display: flex; flex-direction: column; height: 100%; background: var(--miya-bg); color: var(--miya-text); font-family: 'Noto Sans SC', sans-serif; }
.fpv-header { display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.2rem; flex-shrink: 0; border-bottom: 1px solid color-mix(in srgb, var(--miya-accent) 10%, transparent); background: var(--miya-surface); }
.back-btn { width: 2rem; height: 2rem; display: flex; align-items: center; justify-content: center; background: transparent; border: 1px solid color-mix(in srgb, var(--miya-accent) 15%, transparent); border-radius: 0.5rem; color: var(--miya-text-dim); cursor: pointer; padding: 0; }
.back-btn:hover { border-color: var(--miya-primary); color: var(--miya-primary); }
.back-btn svg { width: 1rem; height: 1rem; }
.fpv-label { font-size: 0.7rem; color: var(--miya-text-dim); }

.fpv-body { flex: 1; overflow-y: auto; padding: 1rem 1.5rem; max-width: 700px; margin: 0 auto; width: 100%; box-sizing: border-box; }
.fpv-loading { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--miya-text-dim); font-size: 0.8rem; }

/* 作者 */
.author-row { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1rem; }
.avatar { width: 2rem; height: 2rem; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; background: color-mix(in srgb, var(--miya-gold) 15%, transparent); color: var(--miya-gold); border: 1px solid color-mix(in srgb, var(--miya-gold) 25%, transparent); }
.author-name { font-size: 0.78rem; font-weight: 600; }
.author-lv { font-size: 0.62rem; color: var(--miya-text-dim); font-weight: 400; }
.author-time { font-size: 0.6rem; color: var(--miya-text-dim); }

.post-title { font-size: 1.1rem; font-weight: 700; margin: 0 0 0.5rem; }
.board-row { display: flex; gap: 0.3rem; margin-bottom: 1rem; }
.board-tag { padding: 2px 8px; border-radius: 999px; font-size: 0.6rem; background: color-mix(in srgb, var(--miya-accent) 6%, transparent); color: var(--miya-text-dim); border: 1px solid color-mix(in srgb, var(--miya-accent) 8%, transparent); }

.post-content { font-size: 0.8rem; line-height: 1.7; color: var(--miya-text); margin-bottom: 1rem; }
.post-content :deep(h2) { color: var(--miya-text); font-size: 1rem; margin: 1.2em 0 0.6em; }
.post-content :deep(h3) { color: var(--miya-text); font-size: 0.9rem; margin: 1em 0 0.5em; }
.post-content :deep(code) { background: color-mix(in srgb, var(--miya-accent) 8%, transparent); padding: 0.15em 0.4em; border-radius: 3px; font-size: 0.9em; }
.post-content :deep(table) { width: 100%; border-collapse: collapse; margin: 0.8em 0; font-size: 0.8rem; }
.post-content :deep(th), .post-content :deep(td) { padding: 6px 10px; border: 1px solid color-mix(in srgb, var(--miya-accent) 8%, transparent); text-align: left; }

.img-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.4rem; margin-bottom: 1rem; }
.img-item { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 4px; cursor: pointer; }
.img-item:hover { filter: brightness(1.15); }

.action-bar { display: flex; align-items: center; gap: 1.2rem; padding: 0.6rem 0; border-top: 1px solid color-mix(in srgb, var(--miya-accent) 8%, transparent); border-bottom: 1px solid color-mix(in srgb, var(--miya-accent) 8%, transparent); }
.action-item { display: flex; align-items: center; gap: 0.3rem; font-size: 0.7rem; color: var(--miya-text-dim); text-decoration: none; }
.action-item svg { width: 0.9rem; height: 0.9rem; }
.like-btn { background: transparent; border: none; cursor: pointer; padding: 0; font-family: inherit; }
.like-btn:hover { color: var(--miya-text); }
.like-btn.liked { color: var(--miya-gold); }
.like-btn.liked svg { fill: var(--miya-gold); }

.comments-section { margin-top: 1rem; }
.comments-head { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; font-size: 0.7rem; font-weight: 600; color: var(--miya-text); cursor: pointer; }
.reply-toggle { font-size: 0.62rem; color: var(--miya-accent); font-weight: 400; }
.no-comments { text-align: center; padding: 1rem; font-size: 0.65rem; color: var(--miya-text-dim); }
</style>
