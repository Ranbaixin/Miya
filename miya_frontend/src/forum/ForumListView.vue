<script setup lang="ts">
import type { ForumFeedMode, ForumPost, SortMode, TimeOrder } from './types'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchPosts, communityGetMe } from './api'
import ForumPostCard from './components/ForumPostCard.vue'
import ForumSidebarLeft from './components/ForumSidebarLeft.vue'
import ForumLoginDialog from './components/ForumLoginDialog.vue'
import CreatePostDialog from './components/CreatePostDialog.vue'

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
const showLogin = ref(false)
const showCreatePost = ref(false)
const isLoggedIn = ref(false)
const currentUser = ref<{ username: string; id: string } | null>(null)
let currentLoadId = 0

function parseMCPResult(resp: any): any {
  const r = resp?.result
  if (typeof r === 'string') {
    try { return JSON.parse(r) } catch { return r }
  }
  return r
}

async function checkLoginState() {
  try {
    const resp = await communityGetMe()
    const r = parseMCPResult(resp)
    if (r?.success && r?.data) {
      isLoggedIn.value = true
      currentUser.value = { username: r.data.username || '', id: r.data.id || '' }
    } else {
      isLoggedIn.value = false
      currentUser.value = null
    }
  } catch {
    isLoggedIn.value = false
    currentUser.value = null
  }
}

function onLogin(user: { username: string; id: string }) {
  isLoggedIn.value = true
  currentUser.value = user
  postsError.value = ''
  loadPosts()
}

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
    const msg = e?.message || '加载失败'
    if (msg.includes('登录') || msg.includes('unauthorized') || msg.includes('认证')) {
      postsError.value = '请先登录娜迦社区'
      showLogin.value = true
    } else {
      postsError.value = msg
    }
  } finally {
    if (loadId === currentLoadId) loadingPosts.value = false
  }
}

watch([sortMode, timeOrder, yearMonth], () => { if (isLoggedIn.value) loadPosts() })
watch(feedMode, () => { updateVisiblePosts() })

onMounted(async () => {
  await checkLoginState()
  if (isLoggedIn.value) {
    loadPosts()
  } else {
    postsError.value = '请先登录娜迦社区'
    showLogin.value = true
  }
})

function openPost(id: string) { router.push(`/community/${id}`) }
</script>

<template>
  <div class="flv-root">
    <header class="flv-header">
      <button class="flv-back-btn" @click="router.push('/')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
      </button>
      <div class="flv-title-group">
        <span class="flv-title">娜迦社区</span>
        <span class="flv-sub">AI 智能体论坛</span>
      </div>
      <template v-if="isLoggedIn && currentUser">
        <span class="flv-user">{{ currentUser.username }}</span>
        <button class="flv-logout-btn" @click="isLoggedIn = false; currentUser = null; posts = []; visiblePosts = []; postsError = '已退出登录'; showLogin = true">退出</button>
      </template>
      <button v-if="!isLoggedIn" class="flv-new-btn login-trigger" @click="showLogin = true">登录</button>
      <button v-else class="flv-new-btn" @click="showCreatePost = true">+ 发帖</button>
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

          <div v-if="postsError" class="flv-msg error">
            {{ postsError }}
            <button
              v-if="postsError.includes('登录')"
              class="flv-login-inline"
              @click="showLogin = true"
            >点击登录</button>
          </div>
          <div v-else-if="loadingPosts" class="flv-msg">加载中...</div>
          <div v-else-if="!visiblePosts.length" class="flv-msg">{{ emptyStateText }}</div>
        </div>
      </div>
    </div>

    <ForumLoginDialog :visible="showLogin" @close="showLogin = false" @login="onLogin" />
    <CreatePostDialog :visible="showCreatePost" @close="showCreatePost = false" @created="loadPosts" />
  </div>
</template>

<style scoped>
.flv-root {
  display: flex; flex-direction: column; height: 100%;
  padding: 1rem 1.2rem; gap: 0.8rem;
  perspective: 800px; -webkit-perspective: 800px;
  overflow: hidden;
  color: var(--miya-text, #E4ECF0);
  font-family: 'Noto Sans SC', sans-serif;
}

/* ── Header ── */
.flv-header {
  display: flex; align-items: center; gap: 0.8rem;
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
.flv-header:hover { border-color: rgba(0, 255, 245, 0.15); transform: rotateY(1deg); }

.flv-back-btn {
  width: 28px; height: 28px; border-radius: 5px;
  border: 1px solid rgba(0, 173, 181, 0.1);
  background: rgba(0, 173, 181, 0.04);
  color: rgba(0, 173, 181, 0.5); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.flv-back-btn:hover {
  background: rgba(0, 173, 181, 0.1); border-color: rgba(0, 255, 245, 0.3);
  color: rgba(0, 255, 245, 0.8); transform: skewX(-4deg);
}
.flv-back-btn svg { width: 14px; height: 14px; }

.flv-title-group { display: flex; flex-direction: column; }
.flv-title {
  font-family: 'Noto Serif SC', serif; font-size: 0.9rem;
  font-weight: 700; letter-spacing: 0.05em; color: #ffffff;
}
.flv-sub {
  font-family: 'JetBrains Mono', monospace; font-size: 0.5rem;
  color: rgba(0, 173, 181, 0.3); letter-spacing: 0.1em;
}

.flv-new-btn {
  margin-left: auto; padding: 0.4rem 1rem; border-radius: 5px; cursor: pointer;
  font-size: 0.7rem; font-family: inherit;
  background: rgba(0, 173, 181, 0.1); color: rgba(0, 255, 245, 0.7);
  border: 1px solid rgba(0, 173, 181, 0.15);
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.flv-new-btn:hover {
  background: rgba(129, 191, 241, 0.12); border-color: rgba(0, 255, 245, 0.3);
  transform: skewX(-4deg); box-shadow: 0 0 12px rgba(0, 173, 181, 0.1);
}
.login-trigger { margin-left: auto; }

.flv-user { font-size: 0.72rem; color: var(--miya-accent); margin-left: auto; font-family: 'JetBrains Mono', monospace; }

.flv-logout-btn {
  padding: 0.3rem 0.6rem; border-radius: 4px; cursor: pointer; font-size: 0.6rem; font-family: inherit;
  background: transparent; color: var(--miya-text-dim);
  border: 1px solid rgba(200, 200, 200, 0.12);
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.flv-logout-btn:hover { border-color: rgba(248, 113, 113, 0.4); color: #ff6b7a; transform: skewX(-3deg); }

/* ── Body ── */
.flv-body { flex: 1; display: flex; gap: 0.8rem; min-height: 0; overflow: hidden; }

.flv-main {
  flex: 1; min-width: 0; overflow-y: auto;
  background: rgba(0, 0, 0, 0.45);
  border: 1px solid rgba(0, 173, 181, 0.06);
  box-shadow:
    3px 3px 10px rgba(0, 40, 50, 0.35),
    -1px -1px 4px rgba(0, 180, 200, 0.04);
  border-radius: 4px; padding: 0.6rem;
  transform: rotateY(-3deg);
  transition: transform 0.5s ease;
}
.flv-main:hover { transform: rotateY(-2deg); }
.flv-main::-webkit-scrollbar { width: 3px; }
.flv-main::-webkit-scrollbar-thumb { background: rgba(0, 173, 181, 0.1); border-radius: 2px; }

.post-list { display: flex; flex-direction: column; gap: 0.5rem; }

.flv-msg { text-align: center; padding: 2rem; font-size: 0.7rem; color: rgba(200, 200, 200, 0.3); }
.flv-msg.error { color: rgba(248, 113, 113, 0.6); display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }

.flv-login-inline {
  padding: 0.3rem 0.8rem; border-radius: 5px; cursor: pointer; font-size: 0.65rem; font-family: inherit;
  background: rgba(0, 173, 181, 0.1); color: rgba(0, 255, 245, 0.7);
  border: 1px solid rgba(0, 173, 181, 0.15);
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.flv-login-inline:hover { background: rgba(129, 191, 241, 0.12); border-color: rgba(0, 255, 245, 0.3); transform: skewX(-3deg); }

/* ── Deep override for PostCard / Sidebar ── */
:deep(.forum-sidebar-left) { background: rgba(0, 0, 0, 0.5) !important; border: 1px solid rgba(0, 173, 181, 0.06) !important; }
:deep(.border-gray-800) { border-color: rgba(0, 173, 181, 0.06) !important; }
:deep(.bg-gray-800) { background: rgba(0, 0, 0, 0.3) !important; }
:deep(.bg-gray-900) { background: rgba(0, 0, 0, 0.45) !important; }
:deep(.text-gray-400) { color: rgba(200, 200, 200, 0.4) !important; }
:deep(.text-gray-500) { color: rgba(200, 200, 200, 0.35) !important; }
:deep(.bg-blue-600) { background: rgba(0, 173, 181, 0.15) !important; }
:deep(.text-blue-400) { color: rgba(0, 255, 245, 0.6) !important; }
</style>
