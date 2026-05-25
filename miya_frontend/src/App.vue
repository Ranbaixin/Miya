<script setup lang="ts">
import type { FloatingState } from '@/electron.d'
import { useStorage, useWindowSize } from '@vueuse/core'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import Live2dModel from '@/components/Live2dModel.vue'
import TitleBar from '@/components/TitleBar.vue'
import WindowResizeHandles from '@/components/WindowResizeHandles.vue'
import { playBgm, stopBgm } from '@/composables/useAudio'
import { useElectron } from '@/composables/useElectron'
import { CONFIG } from '@/utils/config'
import { useMIYARealtime } from '@/composables/useMIYARealtime'
import SciFiOverlay from '@/components/SciFiOverlay.vue'
import FloatingView from '@/views/FloatingView.vue'
import { isIndependentMode } from '@/utils/live2dProxy'

const isElectron = !!window.electronAPI
const { connect: connectWS, disconnect: disconnectWS } = useMIYARealtime()
const { isMaximized } = useElectron()
const isMac = window.electronAPI?.platform === 'darwin'

const floatingState = ref<FloatingState>('classic')
const isFloatingMode = computed(() => floatingState.value !== 'classic')

const { width, height } = useWindowSize()
const scale = computed(() => height.value / (10000 - CONFIG.value.web_live2d.model.size))

const STARTUP_LIVE2D = isElectron
  ? 'miya-char://弥娅/Miya/01.model3.json'
  : './models/弥娅/Miya/01.model3.json'
const live2dSource = ref(STARTUP_LIVE2D)

// Live2D 开关 - 独立窗口模式下隐藏内嵌模型
const live2dStore = useStorage('miya-live2d-enabled', true)
const live2dEnabled = computed(() => live2dStore.value && !isIndependentMode())

// 自定义背景
const customBg = useStorage('miya-bg-image', '')
const customBgOpacity = useStorage('miya-bg-opacity', 0.35)

const frameStyle = computed(() => {
  const pad = isElectron ? (isMac ? '28px' : '32px') : '0px'
  const overlay = `rgba(10, 8, 21, ${1 - customBgOpacity.value})`
  const img = customBg.value || `url('/assets/aims.jpg') center/cover no-repeat`
  const bg = img.startsWith('url(') ? img : `url(${img}) center/cover no-repeat`
  return `padding-top:${pad};background:linear-gradient(${overlay},${overlay}),${bg}`
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

const showResizeHandles = computed(() => isElectron && !isFloatingMode.value && !isMaximized.value)
</script>

<template>
  <SciFiOverlay v-if="!isFloatingMode" />
  <FloatingView v-if="isFloatingMode" />
  <template v-else>
    <TitleBar />
    <WindowResizeHandles :visible="showResizeHandles" :title-bar-height="isMac ? 28 : 32" />
      <div class="h-full miya-frame" :style="frameStyle">
      <div class="absolute top-0 left-0 size-full z-0 pointer-events-none">
        <Live2dModel v-if="live2dEnabled" :source="live2dSource" :x="CONFIG.web_live2d.model.x" :y="CONFIG.web_live2d.model.y" :width="width" :height="height" :scale="scale" :ssaa="CONFIG.web_live2d.ssaa" />
      </div>
      <div class="h-full px-1/8 py-1/12" style="display:grid;grid-template-columns:1fr;grid-template-rows:1fr">
        <RouterView v-slot="{ Component, route }">
          <Transition :name="route.path === '/' ? 'slide-out' : 'slide-in'">
            <component :is="Component" :key="route.fullPath" style="grid-column:1;grid-row:1;min-height:0;pointer-events:auto" />
          </Transition>
        </RouterView>
      </div>
    </div>
  </template>
</template>

<style scoped>
.miya-frame {}
.miya-custom-bg { display: none; }
.slide-in-enter-active, .slide-in-leave-active, .slide-out-enter-active, .slide-out-leave-active { transition: all 1s ease; }
.slide-in-enter-from { transform: translateX(-100%); }
.slide-in-leave-to { opacity: 0; transform: translate(-3%, -5%); }
.slide-out-enter-from { opacity: 0; transform: translate(-3%, -5%); }
.slide-out-leave-to { opacity: 0; transform: translateX(-100%); }
</style>
