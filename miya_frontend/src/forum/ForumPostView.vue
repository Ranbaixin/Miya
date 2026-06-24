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
      <button class="fpv-back-btn" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
      </button>
      <span class="fpv-label">返回社区</span>
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
        <span class="action-item"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>{{ post.viewCount }}</span>
        <span class="action-item"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>{{ post.commentList?.length || 0 }}</span>
        <button class="action-item like-btn" :class="{ liked: post.liked }" @click="toggleLike">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" /></svg>{{ post.likesCount }}
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
.fpv-root {
  display: flex; flex-direction: column; height: 100%;
  padding: 1rem 1.2rem; gap: 0.8rem;
  perspective: 800px; -webkit-perspective: 800px;
  overflow: hidden;
  color: var(--miya-text, #E4ECF0);
  font-family: 'Noto Sans SC', sans-serif;
}

/* ── Header ── */
.fpv-header {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem 0.8rem; flex-shrink: 0;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(0, 173, 181, 0.06);
  box-shadow:
    3px 3px 8px rgba(0, 40, 50, 0.3),
    -2px -2px 6px rgba(0, 180, 200, 0.04);
  border-radius: 4px;
  transform: rotateY(2deg);
  transition: border-color 0.3s ease, transform 0.5s ease;
}
.fpv-header:hover { border-color: rgba(0, 255, 245, 0.15); transform: rotateY(1deg); }

.fpv-back-btn {
  width: 28px; height: 28px; border-radius: 5px;
  border: 1px solid rgba(0, 173, 181, 0.1);
  background: rgba(0, 173, 181, 0.04);
  color: rgba(0, 173, 181, 0.5); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.fpv-back-btn:hover {
  background: rgba(0, 173, 181, 0.1); border-color: rgba(0, 255, 245, 0.3);
  color: rgba(0, 255, 245, 0.8); transform: skewX(-4deg);
}
.fpv-back-btn svg { width: 14px; height: 14px; }
.fpv-label { font-size: 0.62rem; color: rgba(0, 173, 181, 0.3); font-family: 'JetBrains Mono', monospace; }

/* ── Body ── */
.fpv-body {
  flex: 1; overflow-y: auto;
  max-width: 720px; margin: 0 auto; width: 100%; box-sizing: border-box;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(0, 173, 181, 0.06);
  box-shadow:
    3px 3px 10px rgba(0, 40, 50, 0.35),
    -1px -1px 4px rgba(0, 180, 200, 0.04);
  border-radius: 4px; padding: 1.2rem 1.5rem;
  transform: rotateY(-2deg);
  transition: transform 0.5s ease, border-color 0.3s ease;
}
.fpv-body:hover { transform: rotateY(-1deg); border-color: rgba(0, 255, 245, 0.1); }
.fpv-body::-webkit-scrollbar { width: 3px; }
.fpv-body::-webkit-scrollbar-thumb { background: rgba(0, 173, 181, 0.1); border-radius: 2px; }

.fpv-loading { flex: 1; display: flex; align-items: center; justify-content: center; color: rgba(200, 200, 200, 0.3); font-size: 0.8rem; }

/* ── Author ── */
.author-row { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1rem; }
.avatar {
  width: 2.2rem; height: 2.2rem; border-radius: 6px; display: flex; align-items: center; justify-content: center;
  font-size: 0.8rem; font-family: 'Noto Serif SC', serif;
  background: rgba(0, 173, 181, 0.1); color: rgba(0, 255, 245, 0.7);
  border: 1px solid rgba(0, 173, 181, 0.15);
}
.author-name { font-size: 0.8rem; font-weight: 600; color: #ffffff; }
.author-lv { font-size: 0.58rem; color: rgba(0, 173, 181, 0.3); font-weight: 400; font-family: 'JetBrains Mono', monospace; }
.author-time { font-size: 0.58rem; color: rgba(200, 200, 200, 0.3); }

/* ── Post ── */
.post-title { font-size: 1.1rem; font-weight: 700; margin: 0 0 0.5rem; color: #ffffff; font-family: 'Noto Serif SC', serif; }

.board-row { display: flex; gap: 0.3rem; margin-bottom: 1rem; }
.board-tag {
  padding: 2px 8px; border-radius: 3px; font-size: 0.55rem;
  background: rgba(0, 173, 181, 0.06); color: rgba(0, 173, 181, 0.4);
  border: 1px solid rgba(0, 173, 181, 0.08);
}

.post-content { font-size: 0.8rem; line-height: 1.7; color: rgba(228, 236, 240, 0.85); margin-bottom: 1rem; }
.post-content :deep(h2) { color: #ffffff; font-size: 1rem; font-family: 'Noto Serif SC', serif; margin: 1.2em 0 0.6em; }
.post-content :deep(h3) { color: rgba(228, 236, 240, 0.9); font-size: 0.9rem; margin: 1em 0 0.5em; }
.post-content :deep(code) {
  background: rgba(0, 173, 181, 0.06); padding: 0.15em 0.4em; border-radius: 3px;
  font-size: 0.9em; font-family: 'JetBrains Mono', monospace;
}
.post-content :deep(table) { width: 100%; border-collapse: collapse; margin: 0.8em 0; font-size: 0.8rem; }
.post-content :deep(th), .post-content :deep(td) { padding: 6px 10px; border: 1px solid rgba(0, 173, 181, 0.06); text-align: left; }

.img-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.4rem; margin-bottom: 1rem; }
.img-item { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 4px; cursor: pointer; border: 1px solid rgba(0, 173, 181, 0.06); }
.img-item:hover { filter: brightness(1.15); border-color: rgba(0, 255, 245, 0.2); }

/* ── Actions ── */
.action-bar {
  display: flex; align-items: center; gap: 1.2rem;
  padding: 0.6rem 0;
  border-top: 1px solid rgba(0, 173, 181, 0.06);
  border-bottom: 1px solid rgba(0, 173, 181, 0.06);
}
.action-item { display: flex; align-items: center; gap: 0.3rem; font-size: 0.7rem; color: rgba(200, 200, 200, 0.4); }
.action-item svg { width: 0.85rem; height: 0.85rem; }
.like-btn { background: transparent; border: none; cursor: pointer; padding: 0; font-family: inherit; transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1); }
.like-btn:hover { color: rgba(255, 255, 255, 0.8); transform: scale(1.1); }
.like-btn.liked { color: rgba(0, 255, 245, 0.6); }
.like-btn.liked svg { fill: rgba(0, 255, 245, 0.4); }

/* ── Comments ── */
.comments-section { margin-top: 1rem; }
.comments-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.5rem 0; font-size: 0.7rem; font-weight: 600; color: rgba(228, 236, 240, 0.7); cursor: pointer;
}
.reply-toggle { font-size: 0.6rem; color: rgba(0, 173, 181, 0.4); font-weight: 400; font-family: 'JetBrains Mono', monospace; }
.reply-toggle:hover { color: rgba(0, 255, 245, 0.6); }
.no-comments { text-align: center; padding: 1rem; font-size: 0.65rem; color: rgba(200, 200, 200, 0.2); }

/* ── Deep overrides ── */
:deep(.border-gray-800) { border-color: rgba(0, 173, 181, 0.06) !important; }
:deep(.bg-gray-900) { background: rgba(0, 0, 0, 0.35) !important; }
:deep(.text-gray-400) { color: rgba(200, 200, 200, 0.4) !important; }
:deep(.text-gray-500) { color: rgba(200, 200, 200, 0.35) !important; }
</style>
