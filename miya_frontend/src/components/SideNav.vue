<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

interface NavItem {
  id: string
  label: string
  icon: string
  path?: string
  action?: () => void
}

const router = useRouter()
const route = useRoute()
const showMore = ref(false)

const mainItems: NavItem[] = [
  { id: 'chat', label: '弥娅对话', icon: '◆', path: '/chat' },
  { id: 'mind', label: '记忆星河', icon: '◇', path: '/mind' },
  { id: 'artboard', label: '弥娅画板', icon: '⬗', path: '/artboard' },
  { id: 'terminal', label: '终端引擎', icon: '⬡', path: '/terminal' },
]

const moreItems: NavItem[] = [
  { id: 'config', label: '灵魂调谐', icon: '❖', path: '/config' },
  { id: 'community', label: '娜迦社区', icon: '✧', path: '/community' },
  { id: 'security', label: '安全中心', icon: '⬢', path: '/security' },
  { id: 'hub', label: '弥娅中枢', icon: '⬡', path: '/hub' },
  { id: 'screen', label: '屏幕视觉', icon: '⊙', path: '/screen' },
]

function isActive(item: NavItem) {
  if (item.path === '/chat' && (route.path === '/chat' || route.path === '/'))
    return true
  return route.path.startsWith(item.path || '')
}

const homeActive = computed(() => route.path === '/' || route.path === '')

function navigateTo(item: NavItem) {
  if (item.action) {
    item.action()
    return
  }
  if (item.path)
    router.push(item.path)
}
</script>

<template>
  <nav class="side-nav">
    <!-- Logo / Home -->
    <button
      class="nav-logo"
      :class="{ active: homeActive }"
      title="弥娅 · 首页"
      @click="router.push('/')"
    >
      <span class="nav-logo-icon">弥</span>
      <span class="nav-logo-label">MIYA</span>
    </button>

    <div class="nav-divider" />

    <!-- 主菜单 -->
    <button
      v-for="item in mainItems"
      :key="item.id"
      class="nav-item"
      :class="{ active: isActive(item) }"
      :title="item.label"
      @click="navigateTo(item)"
    >
      <span class="nav-icon">{{ item.icon }}</span>
      <span class="nav-label">{{ item.label }}</span>
      <div class="nav-active-bar" />
    </button>

    <!-- 更多按钮 -->
    <button
      class="nav-item nav-more-btn"
      :class="{ active: showMore }"
      title="更多功能"
      @click="showMore = !showMore"
    >
      <span class="nav-icon">{{ showMore ? '▼' : '▶' }}</span>
      <span class="nav-label">更多</span>
    </button>

    <!-- 展开更多项 -->
    <Transition name="more-slide">
      <div v-if="showMore" class="nav-more-section">
        <button
          v-for="item in moreItems"
          :key="item.id"
          class="nav-item nav-item-sm"
          :class="{ active: isActive(item) }"
          :title="item.label"
          @click="navigateTo(item)"
        >
          <span class="nav-icon-sm">{{ item.icon }}</span>
          <span class="nav-label-sm">{{ item.label }}</span>
        </button>
      </div>
    </Transition>

    <!-- 底部 -->
    <div class="nav-spacer" />
    <div class="nav-divider" />
    <button
      class="nav-item"
      title="回到首页"
      @click="router.push('/')"
    >
      <span class="nav-icon">⌂</span>
      <span class="nav-label">首页</span>
    </button>
  </nav>
</template>

<style scoped>
.side-nav {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 64px;
  min-width: 64px;
  height: 100%;
  padding: 0.5rem 0;
  background: rgba(0, 0, 0, 0.45);
  border-right: 1px solid rgba(0, 173, 181, 0.06);
  box-shadow:
    3px 0 10px rgba(0, 60, 70, 0.35),
    -1px 0 0 rgba(0, 200, 210, 0.06);
  perspective: 400px;
  -webkit-perspective: 400px;
  z-index: 50;
  user-select: none;
}

/* Logo */
.nav-logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
  padding: 0.4rem 0;
  width: 48px;
  margin: 0.3rem 0;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 173, 181, 0.1);
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow:
    2px 2px 6px rgba(0, 60, 70, 0.3),
    -1px -1px 4px rgba(0, 200, 210, 0.06);
}

.nav-logo:hover,
.nav-logo.active {
  border-color: rgba(0, 255, 245, 0.4);
  box-shadow:
    3px 3px 10px rgba(0, 60, 70, 0.4),
    -2px -2px 6px rgba(0, 200, 210, 0.1),
    0 0 20px rgba(0, 173, 181, 0.2);
}

.nav-logo.active {
  background: rgba(0, 173, 181, 0.12);
}

.nav-logo-icon {
  font-family: 'Noto Serif SC', serif;
  font-size: 1.1rem;
  font-weight: 700;
  color: rgba(0, 255, 245, 0.85);
  line-height: 1;
  transition: all 0.3s ease;
}

.nav-logo:hover .nav-logo-icon {
  text-shadow: 0 0 12px rgba(0, 255, 245, 0.3);
}

.nav-logo-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.4rem;
  color: rgba(0, 173, 181, 0.5);
  letter-spacing: 0.2em;
}

/* Divider */
.nav-divider {
  width: 28px;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(0, 173, 181, 0.15),
    transparent
  );
  margin: 0.25rem 0;
}

/* Nav items */
.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  width: 48px;
  padding: 0.45rem 0;
  margin: 0.15rem 0;
  background: none;
  border: none;
  cursor: pointer;
  position: relative;
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  color: rgba(200, 200, 200, 0.5);
}

.nav-item:hover {
  color: rgba(255, 255, 255, 0.9);
  transform: skewX(-6deg);
  background: rgba(0, 173, 181, 0.15);
  box-shadow: 2px 2px 8px rgba(0, 60, 70, 0.3);
}

.nav-item.active {
  color: #ffffff;
  background: rgba(0, 173, 181, 0.12);
  font-weight: 600;
}

.nav-icon {
  font-size: 1.1rem;
  line-height: 1;
  transition: transform 0.3s ease, filter 0.3s ease;
}

.nav-item:hover .nav-icon {
  transform: scale(1.15);
}

.nav-item.active .nav-icon {
  filter: drop-shadow(0 0 8px rgba(0, 255, 245, 0.5));
}

.nav-label {
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 0.48rem;
  letter-spacing: 0.06em;
  line-height: 1;
  white-space: nowrap;
}

/* Active bar */
.nav-active-bar {
  position: absolute;
  left: 0;
  top: 15%;
  height: 70%;
  width: 2px;
  background: linear-gradient(
    180deg,
    transparent,
    rgba(0, 255, 245, 0.7),
    transparent
  );
  opacity: 0;
  transition: opacity 0.3s ease;
  box-shadow: 0 0 4px rgba(0, 255, 245, 0.3);
}

.nav-item.active .nav-active-bar {
  opacity: 1;
}

/* More button */
.nav-more-btn {
  margin-top: 0.2rem;
}

.nav-more-btn .nav-icon {
  font-size: 0.6rem;
  transition: transform 0.3s ease;
}

/* More section */
.nav-more-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: hidden;
}

.nav-item-sm {
  padding: 0.35rem 0;
  width: 44px;
  margin: 0.08rem 0;
}

.nav-icon-sm {
  font-size: 0.9rem;
}

.nav-label-sm {
  font-size: 0.42rem;
}

/* Transitions */
.more-slide-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.more-slide-leave-active {
  transition: all 0.2s ease-in;
}
.more-slide-enter-from,
.more-slide-leave-to {
  opacity: 0;
  max-height: 0;
}

/* Spacer */
.nav-spacer {
  flex: 1;
}
</style>
