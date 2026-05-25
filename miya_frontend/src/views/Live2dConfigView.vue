<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { Slider, ToggleSwitch } from 'primevue'
import { useRouter } from 'vue-router'

const router = useRouter()

const live2dCfg = useStorage('miya-live2d-window-config', {
  bgColor: '#111122',
  bgAlpha: 0.1,
  windowScale: 100,
  alwaysOnTop: true,
  visible: true,
})

function setLive2dBg(e?: Event) {
  if (e) live2dCfg.value.bgColor = (e.target as HTMLInputElement).value
  const api = window.live2dAPI
  if (!api) return
  const hex = live2dCfg.value.bgColor.replace('#', '')
  api.setBackground?.(`0x${hex}`, live2dCfg.value.bgAlpha)
}

function setLive2dScale() {
  const api = window.live2dAPI
  if (api) api.setWindowScale?.(live2dCfg.value.windowScale)
}

function setLive2dAlwaysOnTop() {
  const api = window.live2dAPI
  if (api) api.setAlwaysOnTop(live2dCfg.value.alwaysOnTop)
}

function setLive2dVisibility() {
  const api = window.live2dAPI
  if (api) api.toggleVisibility()
}

function resetLive2dPos() {
  const api = window.live2dAPI
  if (api) api.resetPosition()
}

function resetLive2dSize() {
  live2dCfg.value.windowScale = 100
  setLive2dScale()
}
</script>

<template>
  <div class="live2d-page">
    <div class="page-header">
      <button class="back-btn" @click="router.push('/')">←</button>
      <h1 class="page-title">Live2D 独立窗口</h1>
    </div>
    <p class="page-hint">控制独立弥娅渲染窗口的显示效果</p>

    <div class="config-card">
      <h3>窗口背景</h3>
      <div class="color-row">
        <input
          type="color"
          :value="live2dCfg.bgColor"
          class="big-color-picker"
          @input="setLive2dBg($event)"
        >
        <span class="color-hex">{{ live2dCfg.bgColor }}</span>
      </div>
    </div>

    <div class="config-card">
      <h3>背景透明度</h3>
      <div class="slider-row">
        <Slider v-model="live2dCfg.bgAlpha" :min="0" :max="1" :step="0.05" style="flex:1" @update:model-value="setLive2dBg()" />
        <span class="slider-val">{{ Math.round(live2dCfg.bgAlpha * 100) }}%</span>
      </div>
    </div>

    <div class="config-card">
      <h3>窗口缩放</h3>
      <div class="slider-row">
        <Slider v-model="live2dCfg.windowScale" :min="50" :max="200" :step="5" style="flex:1" @update:model-value="setLive2dScale()" />
        <span class="slider-val">{{ live2dCfg.windowScale }}%</span>
      </div>
    </div>

    <div class="config-card">
      <h3>显示选项</h3>
      <div class="toggle-row">
        <span>窗口置顶</span>
        <ToggleSwitch v-model="live2dCfg.alwaysOnTop" @change="setLive2dAlwaysOnTop()" />
      </div>
      <div class="toggle-row">
        <span>显示 Live2D 窗口</span>
        <ToggleSwitch v-model="live2dCfg.visible" @change="setLive2dVisibility()" />
      </div>
    </div>

    <div class="config-card">
      <h3>窗口位置</h3>
      <div class="btn-row">
        <button class="action-btn" @click="resetLive2dPos()">重置位置</button>
        <button class="action-btn" @click="resetLive2dSize()">重置大小</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.live2d-page {
  padding: 1.5rem 2rem;
  color: var(--miya-text);
  height: 100%;
  overflow-y: auto;
  font-size: 0.85rem;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}
.back-btn {
  background: transparent;
  border: 1px solid rgba(0,229,255,0.2);
  color: var(--miya-accent);
  padding: 0.3rem 0.6rem;
  border-radius: 0.3rem;
  cursor: pointer;
  font-size: 0.9rem;
}
.back-btn:hover { background: rgba(0,229,255,0.08); }
.page-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 1.2rem;
  color: var(--miya-accent);
  margin: 0;
}
.page-hint {
  color: var(--miya-text-dim);
  font-size: 0.78rem;
  margin: 0 0 1.5rem;
}
.config-card {
  background: rgba(10,8,21,0.6);
  border: 1px solid rgba(0,229,255,0.08);
  border-radius: 0.5rem;
  padding: 1rem 1.2rem;
  margin-bottom: 0.8rem;
}
.config-card h3 {
  font-size: 0.85rem;
  color: var(--miya-accent);
  margin: 0 0 0.6rem;
}
.color-row {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.big-color-picker {
  width: 52px;
  height: 40px;
  border-radius: 6px;
  border: 1px solid rgba(0,229,255,0.2);
  background: transparent;
  cursor: pointer;
  padding: 2px;
}
.color-hex {
  font-size: 0.85rem;
  color: var(--miya-text-dim);
  font-family: 'JetBrains Mono', monospace;
}
.slider-row {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.slider-row .p-slider { flex: 1; }
.slider-val {
  font-size: 0.8rem;
  color: var(--miya-accent);
  min-width: 3rem;
  text-align: right;
}
.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.3rem 0;
}
.btn-row {
  display: flex;
  gap: 0.5rem;
}
.action-btn {
  padding: 0.3rem 0.8rem;
  font-size: 0.72rem;
  border: 1px dashed rgba(0,229,255,0.15);
  border-radius: 0.3rem;
  background: transparent;
  color: rgba(0,229,255,0.4);
  cursor: pointer;
  transition: all 0.2s;
}
.action-btn:hover {
  border-color: rgba(0,229,255,0.4);
  color: rgba(0,229,255,0.7);
}
</style>
