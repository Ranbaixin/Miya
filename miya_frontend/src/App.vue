<script setup lang="ts">
import type { FloatingState } from '@/electron.d'
import { useStorage, useWindowSize } from '@vueuse/core'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import TitleBar from '@/components/TitleBar.vue'
import TopStatusBar from '@/components/TopStatusBar.vue'
import SideNav from '@/components/SideNav.vue'
import BottomBar from '@/components/BottomBar.vue'
import { playBgm } from '@/composables/useAudio'
import { useElectron } from '@/composables/useElectron'
import { useMIYARealtime } from '@/composables/useMIYARealtime'
import SciFiOverlay from '@/components/SciFiOverlay.vue'
import Live2dModel from '@/components/Live2dModel.vue'
import FloatingView from '@/views/FloatingView.vue'
import { CONFIG } from '@/utils/config'
import { mascotCfg } from '@/utils/live2dMascotConfig'

const route = useRoute()
const isElectron = !!window.electronAPI
const { connect: connectWS, disconnect: disconnectWS } = useMIYARealtime()
const { isMaximized } = useElectron()
const isMac = window.electronAPI?.platform === 'darwin'

const floatingState = ref<FloatingState>('classic')
const isFloatingMode = computed(() => floatingState.value !== 'classic')
const isHome = computed(() => route.path === '/')

const customBg = useStorage('miya-bg-image', '')
const customBgOpacity = useStorage('miya-bg-opacity', 0.35)

const frameStyle = computed(() => {
  const overlay = `rgba(34, 40, 49, ${1 - customBgOpacity.value})`
  const img = customBg.value || `url('/assets/aims.jpg') center/cover no-repeat`
  const bg = img.startsWith('url(') ? img : `url(${img}) center/cover no-repeat`
  return `background:linear-gradient(${overlay},${overlay}),${bg}`
})

onMounted(() => {
  playBgm('9.快乐的小曲.mp3')
  connectWS()
  if (isElectron) {
    window.electronAPI?.floating.getState().then((s: FloatingState) => {
      floatingState.value = s
    })
    window.electronAPI?.floating.onStateChange((s: FloatingState) => {
      floatingState.value = s
    })
  }
})

onUnmounted(() => { disconnectWS() })

// ── 嵌入式 Live2D 看板娘 ──
const { width: winW, height: winH } = useWindowSize()
const live2dW = computed(() => Math.max(280, Math.min(winW.value * 0.32, 420)))
const live2dH = computed(() => Math.max(400, Math.min(winH.value * 0.72, 640)))
const showEmbeddedLive2d = computed(() => !isFloatingMode.value && isHome.value && mascotCfg.value.enabled)

// Live2D 窗口位置跟随
let resizeDebounce: ReturnType<typeof setTimeout> | undefined
function syncLive2dPosition() {
  clearTimeout(resizeDebounce)
  resizeDebounce = setTimeout(async () => {
    if (!isHome.value || !isElectron) return
    if (!window.live2dAPI?.positionRelative) return
    try {
      const bounds = await window.electronAPI!.getBounds()
      console.log('[App] syncLive2d bounds:', bounds)
      window.live2dAPI.positionRelative(bounds)
    } catch (e) {
      console.error('[App] syncLive2d failed:', e)
    }
  }, 300)
}
watch(isHome, (home) => {
  if (!isElectron) return
  if (home) syncLive2dPosition()
  else window.live2dAPI?.resetPosition()
}, { immediate: true })
onMounted(() => window.addEventListener('resize', syncLive2dPosition))
onUnmounted(() => {
  window.removeEventListener('resize', syncLive2dPosition)
  clearTimeout(resizeDebounce)
})

const layoutPadTop = computed(() => isElectron ? (isMac ? '28px' : '32px') : '0px')
</script>

<template>
  <template v-if="isFloatingMode">
    <FloatingView />
  </template>
  <template v-else>
    <SciFiOverlay />
    <TitleBar />
    <TopStatusBar :style="{ paddingTop: layoutPadTop }" />

    <div class="miya-body" :style="frameStyle">
      <div v-if="showEmbeddedLive2d" class="live2d-container" :style="{ width: `${live2dW}px`, height: `${live2dH}px` }">
        <Live2dModel
          :source="CONFIG.web_live2d.model.source"
          :width="live2dW"
          :height="live2dH"
          :x="0.5"
          :y="0.55"
          :fill-ratio="0.75"
          :ssaa="CONFIG.web_live2d.ssaa"
        />
      </div>
      <SideNav />
      <main class="content-main" :class="{ 'content-home': isHome }">
        <RouterView v-slot="{ Component, route: r }">
          <Transition :name="r.path === '/' ? 'page-fade' : 'page-slide'" mode="out-in">
            <component :is="Component" :key="r.fullPath" />
          </Transition>
        </RouterView>
      </main>
    </div>

    <BottomBar />
  </template>
</template>

<style scoped>
.miya-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.content-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 0.6rem 1rem;
  overflow: hidden;
}

.content-home {
  padding: 0;
}

.page-slide-enter-active,
.page-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.page-slide-enter-from { opacity: 0; transform: translateX(24px); }
.page-slide-leave-to { opacity: 0; transform: translateX(-24px); }

.page-fade-enter-active,
.page-fade-leave-active {
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.page-fade-enter-from,
.page-fade-leave-to { opacity: 0; }

.live2d-container {
  position: absolute;
  left: 50%;
  bottom: 0;
  transform: translateX(-50%);
  overflow: hidden;
  z-index: 0;
  pointer-events: none;
  opacity: 0.85;
}
</style>
