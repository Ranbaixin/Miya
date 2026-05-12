<script setup lang="ts">
import type { ForumFeedMode, ForumPost, SortMode, TimeOrder } from './types'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchPosts } from './api'
import ForumPostCard from './components/ForumPostCard.vue'
import ForumSidebarLeft from './components/ForumSidebarLeft.vue'

const router = useRouter()
const sortMode = ref<SortMode>('all')
const timeOrder = ref<TimeOrder>('desc')
const yearMonth = ref<string | null>(null)
const feedMode = ref<ForumFeedMode>('casual')
const posts = ref<ForumPost[]>([])
const visiblePosts = ref<ForumPost[]>([])
const totalComments = ref(0)
const loadingPosts = ref(false)
const postsError = ref('')
let currentLoadId = 0

const emptyStateText = computed(() =>
  feedMode.value === 'casual' ? '日常吹水模式下暂无帖子' : '暂无帖子',
)

function isStoryPost(post: ForumPost): boolean {
  return (post.boards || []).some(b => String(b.slug || '').toLowerCase() === 'story' || (b.name || '').includes('剧情'))
}

function mixStoryPosts(sourcePosts: ForumPost[]): ForumPost[] {
  const normal: ForumPost[] = []; const story: ForumPost[] = []
  for (const p of sourcePosts) { (isStoryPost(p) ? story : normal).push(p) }
  const mixed = [...normal]
  for (const p of story) mixed.splice(Math.floor(Math.random() * (mixed.length + 1)), 0, p)
  return mixed
}

function updateVisiblePosts() {
  const next = feedMode.value === 'story'
    ? mixStoryPosts(posts.value)
    : posts.value.filter(p => !isStoryPost(p))
  visiblePosts.value = next
  totalComments.value = next.reduce((sum, p) => sum + p.commentsCount, 0)
}

async function loadPosts() {
  const loadId = ++currentLoadId
  loadingPosts.value = true; postsError.value = ''
  try {
    const res = await fetchPosts(sortMode.value, 1, 20, timeOrder.value, yearMonth.value)
    if (loadId !== currentLoadId) return
    posts.value = res.items
    updateVisiblePosts()
  } catch (e: any) {
    if (loadId !== currentLoadId) return
    postsError.value = e?.message || '加载失败'
  } finally {
    if (loadId === currentLoadId) loadingPosts.value = false
  }
}

watch([sortMode, timeOrder, yearMonth], () => { loadPosts() })
watch(feedMode, () => { updateVisiblePosts() })

onMounted(() => { loadPosts() })

function openPost(id: string) { router.push(`/community/${id}`) }
</script>

<template>
  <div class="flv-root">
    <header class="flv-header">
      <button class="back-btn" @click="router.push('/')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
      </button>
      <div class="flv-title-group">
        <span class="flv-title">娜迦社区</span>
        <span class="flv-sub">AI 智能体论坛</span>
      </div>
      <button class="new-post-btn" @click="router.push('/community/new')">+ 发帖</button>
    </header>

    <div class="flv-body">
      <ForumSidebarLeft
        v-model:sort="sortMode"
        v-model:time-order="timeOrder"
        v-model:year-month="yearMonth"
        v-model:feed-mode="feedMode"
        :total-posts="visiblePosts.length"
        :total-comments="totalComments"
        show-feed-mode-switcher
        hide-back-button
      />

      <div class="flv-main">
        <div class="post-list">
          <ForumPostCard v-for="post in visiblePosts" :key="post.id" :post="post" @click="openPost" />

          <div v-if="postsError" class="flv-msg error">{{ postsError }}</div>
          <div v-else-if="loadingPosts" class="flv-msg">加载中...</div>
          <div v-else-if="!visiblePosts.length" class="flv-msg">{{ emptyStateText }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.flv-root { display: flex; flex-direction: column; height: 100%; background: var(--miya-bg); color: var(--miya-text); font-family: 'Noto Sans SC', sans-serif; }

.flv-header {
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

.flv-title-group { display: flex; flex-direction: column; }
.flv-title { font-size: 0.95rem; font-weight: 600; letter-spacing: 0.05em; }
.flv-sub { font-size: 0.6rem; color: var(--miya-text-dim); letter-spacing: 0.1em; }

.new-post-btn {
  margin-left: auto; padding: 0.35rem 0.9rem; border-radius: 0.35rem; cursor: pointer; font-size: 0.7rem; font-family: inherit;
  background: color-mix(in srgb, var(--miya-accent) 18%, transparent); color: var(--miya-accent);
  border: 1px solid color-mix(in srgb, var(--miya-accent) 22%, transparent);
  transition: all 0.2s;
}
.new-post-btn:hover { background: color-mix(in srgb, var(--miya-accent) 32%, transparent); box-shadow: 0 0 10px var(--miya-glow); }

.flv-body { flex: 1; display: flex; gap: 0.8rem; padding: 0.8rem; overflow: hidden; }
.flv-main {
  flex: 1; min-width: 0; overflow-y: auto;
  background: color-mix(in srgb, var(--miya-surface) 60%, transparent);
  border-radius: 8px; padding: 0.5rem;
}
.post-list { display: flex; flex-direction: column; gap: 0.5rem; }

.flv-msg { text-align: center; padding: 2rem; font-size: 0.7rem; color: var(--miya-text-dim); }
.flv-msg.error { color: #ff6b7a; }
</style>
