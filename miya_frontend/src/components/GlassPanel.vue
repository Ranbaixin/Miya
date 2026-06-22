<script setup lang="ts">
import { useRouter } from 'vue-router'

const props = withDefaults(defineProps<{
  title?: string
  subtitle?: string
  hideBack?: boolean
  size?: 'sm' | 'md' | 'lg' | 'full' | 'fluid'
}>(), {
  size: 'lg',
  hideBack: false,
})

const router = useRouter()
const sizeClass = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-2xl',
  full: 'max-w-full',
  fluid: '', // no max-width constraint at all
}[props.size]
</script>

<template>
  <div class="glass-panel-container" :class="sizeClass">
    <div class="glass-panel">
      <!-- 斜切角装饰线 -->
      <div class="panel-corner tl" />
      <div class="panel-corner tr" />
      <div class="panel-corner bl" />
      <div class="panel-corner br" />

      <!-- 顶部扫描线 -->
      <div class="panel-scanline" />

      <!-- 标题栏 -->
      <div v-if="title || !hideBack" class="panel-header">
        <button
          v-if="!hideBack"
          class="panel-back-btn"
          title="返回"
          @click="router.back()"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div v-if="title" class="panel-title-group">
          <span class="panel-title">{{ title }}</span>
          <span v-if="subtitle" class="panel-subtitle">{{ subtitle }}</span>
        </div>
        <slot name="header-actions" />
      </div>

      <!-- 内容区 -->
      <div class="panel-content">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.glass-panel-container {
  width: 100%;
  margin: 0 auto;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  animation: panel-enter 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes panel-enter {
  from { opacity: 0; transform: translateY(12px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.glass-panel {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: linear-gradient(
    135deg,
    rgba(34, 40, 49, 0.85) 0%,
    rgba(57, 62, 70, 0.75) 50%,
    rgba(34, 40, 49, 0.85) 100%
  );
  backdrop-filter: blur(20px) saturate(120%);
  -webkit-backdrop-filter: blur(20px) saturate(120%);
  border: 1px solid rgba(0, 173, 181, 0.15);
  clip-path: polygon(
    0 10px, 8px 0, 100% 0,
    100% calc(100% - 8px), calc(100% - 8px) 100%,
    0 100%
  );
  overflow: hidden;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(0, 173, 181, 0.08),
    inset 0 1px 0 rgba(0, 255, 245, 0.04);
  transition: border-color 0.4s ease, box-shadow 0.4s ease;
}

.glass-panel:hover {
  border-color: rgba(0, 173, 181, 0.25);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.4),
    0 0 20px rgba(0, 173, 181, 0.08),
    0 0 0 1px rgba(0, 173, 181, 0.12),
    inset 0 1px 0 rgba(0, 255, 245, 0.06);
}

/* 斜切角 */
.panel-corner {
  position: absolute;
  pointer-events: none;
  z-index: 2;
}
.panel-corner.tl {
  top: 0; left: 0;
  width: 18px; height: 18px;
  border-top: 2px solid rgba(0, 255, 245, 0.4);
  border-left: 2px solid rgba(0, 255, 245, 0.4);
  clip-path: polygon(0 0, 100% 0, 0 100%);
}
.panel-corner.tr {
  top: 0; right: 0;
  width: 18px; height: 18px;
  border-top: 1px solid rgba(0, 173, 181, 0.25);
  border-right: 1px solid rgba(0, 173, 181, 0.25);
  clip-path: polygon(100% 0, 100% 100%, 0 0);
}
.panel-corner.bl {
  bottom: 0; left: 0;
  width: 18px; height: 18px;
  border-bottom: 1px solid rgba(0, 173, 181, 0.2);
  border-left: 1px solid rgba(0, 173, 181, 0.2);
  clip-path: polygon(0 0, 0 100%, 100% 100%);
}
.panel-corner.br {
  bottom: 0; right: 0;
  width: 22px; height: 22px;
  border-bottom: 2px solid rgba(0, 255, 245, 0.35);
  border-right: 2px solid rgba(0, 255, 245, 0.35);
  clip-path: polygon(100% 0, 0 100%, 100% 100%);
}

/* 扫描线 */
.panel-scanline {
  position: absolute;
  top: 18px;
  left: 10%;
  right: 10%;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(0, 255, 245, 0.15) 20%,
    rgba(0, 255, 245, 0.04) 50%,
    rgba(0, 255, 245, 0.15) 80%,
    transparent
  );
  opacity: 0.5;
  pointer-events: none;
  z-index: 1;
}

/* 标题栏 */
.panel-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.8rem 1rem 0.5rem;
  border-bottom: 1px solid rgba(0, 173, 181, 0.06);
  position: relative;
  z-index: 2;
}

.panel-back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid rgba(0, 173, 181, 0.2);
  background: rgba(0, 173, 181, 0.06);
  color: rgba(0, 173, 181, 0.7);
  cursor: pointer;
  clip-path: polygon(0 4px, 4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%);
  transition: all 0.25s ease;
  flex-shrink: 0;
}

.panel-back-btn:hover {
  background: rgba(0, 173, 181, 0.14);
  border-color: rgba(0, 173, 181, 0.45);
  color: rgba(0, 255, 245, 0.95);
  box-shadow: 0 0 14px rgba(0, 173, 181, 0.2);
}

.panel-title-group {
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
  min-width: 0;
}

.panel-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--miya-text, #E4ECF0);
  letter-spacing: 0.08em;
}

.panel-subtitle {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
  color: var(--miya-text-dim);
  letter-spacing: 0.12em;
}

/* 内容 */
.panel-content {
  position: relative;
  z-index: 2;
  flex: 1;
  min-height: 0;
  padding: 0.8rem 1rem;
  overflow-y: auto;
}

.panel-content::-webkit-scrollbar {
  width: 4px;
}
.panel-content::-webkit-scrollbar-track {
  background: transparent;
}
.panel-content::-webkit-scrollbar-thumb {
  background: rgba(0, 173, 181, 0.12);
  border-radius: 2px;
}
.panel-content::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 173, 181, 0.25);
}
</style>
