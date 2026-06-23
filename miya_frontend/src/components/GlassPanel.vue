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
  fluid: '',
}[props.size]
</script>

<template>
  <div class="glass-panel-container" :class="sizeClass">
    <div class="glass-panel">
      <!-- 四角 bracket -->
      <div class="panel-corner tl" />
      <div class="panel-corner tr" />
      <div class="panel-corner bl" />
      <div class="panel-corner br" />

      <!-- 顶部扫描线 -->
      <div class="panel-scanline" />

      <!-- 侧边装饰竖线 -->
      <div class="panel-edge left" />
      <div class="panel-edge right" />

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
    rgba(0, 0, 0, 0.55) 0%,
    rgba(34, 40, 49, 0.52) 50%,
    rgba(0, 0, 0, 0.5) 100%
  );
  backdrop-filter: blur(24px) saturate(120%);
  -webkit-backdrop-filter: blur(24px) saturate(120%);
  border: 1px solid rgba(0, 173, 181, 0.08);
  clip-path: polygon(
    0 12px, 8px 0, calc(100% - 8px) 0, 100% 6px,
    100% calc(100% - 6px), calc(100% - 8px) 100%,
    8px 100%, 0 calc(100% - 8px)
  );
  overflow: hidden;
  box-shadow:
    4px 4px 18px rgba(0, 50, 60, 0.45),
    -2px -2px 12px rgba(0, 180, 200, 0.07),
    0 1px 0 rgba(0, 173, 181, 0.04),
    inset 0 1px 0 rgba(0, 255, 245, 0.04);
  transition: border-color 0.4s ease, box-shadow 0.4s ease;
}

.glass-panel:hover {
  border-color: rgba(0, 173, 181, 0.2);
  box-shadow:
    4px 6px 22px rgba(0, 50, 60, 0.5),
    -2px -2px 14px rgba(0, 180, 200, 0.1),
    0 0 28px rgba(0, 173, 181, 0.1),
    inset 0 1px 0 rgba(0, 255, 245, 0.06);
}

/* ═══ 四角 bracket — PGR 风格 ═══ */
.panel-corner {
  position: absolute;
  pointer-events: none;
  z-index: 2;
  transition: all 0.35s ease;
}

.panel-corner.tl {
  top: 0; left: 0;
  width: 20px; height: 20px;
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

.glass-panel:hover .panel-corner.tl {
  border-color: rgba(0, 255, 245, 0.6) rgba(0, 255, 245, 0.6) transparent transparent;
}

.glass-panel:hover .panel-corner.br {
  border-color: transparent transparent rgba(0, 255, 245, 0.55) rgba(0, 255, 245, 0.55);
}

/* ═══ 侧边装饰竖线 ═══ */
.panel-edge {
  position: absolute;
  top: 14%;
  bottom: 14%;
  width: 1px;
  background: linear-gradient(
    180deg,
    transparent,
    rgba(0, 173, 181, 0.08) 30%,
    rgba(0, 255, 245, 0.04) 50%,
    rgba(0, 173, 181, 0.08) 70%,
    transparent
  );
  pointer-events: none;
  z-index: 1;
  opacity: 0;
  transition: opacity 0.4s ease;
}

.panel-edge.left {
  left: 12px;
}

.panel-edge.right {
  right: 12px;
}

.glass-panel:hover .panel-edge {
  opacity: 1;
}

/* ═══ 扫描线 ═══ */
.panel-scanline {
  position: absolute;
  top: 20px;
  left: 8%;
  right: 8%;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(0, 255, 245, 0.2) 15%,
    rgba(0, 255, 245, 0.05) 50%,
    rgba(0, 255, 245, 0.2) 85%,
    transparent
  );
  opacity: 0.45;
  pointer-events: none;
  z-index: 1;
}

/* ═══ 标题栏 ═══ */
.panel-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.8rem 1rem 0.5rem;
  border-bottom: 1px solid rgba(0, 173, 181, 0.05);
  position: relative;
  z-index: 2;
}

.panel-back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid rgba(0, 173, 181, 0.15);
  background: rgba(0, 173, 181, 0.06);
  color: rgba(0, 173, 181, 0.6);
  cursor: pointer;
  clip-path: polygon(0 4px, 4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%);
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.panel-back-btn:hover {
  background: rgba(0, 173, 181, 0.16);
  border-color: rgba(0, 173, 181, 0.45);
  color: rgba(0, 255, 245, 0.95);
  box-shadow: 0 0 16px rgba(0, 173, 181, 0.22);
  transform: skewX(-4deg);
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
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.08em;
  text-shadow: 0 0 8px rgba(0, 255, 245, 0.12);
}

.panel-subtitle {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
  color: var(--miya-text-dim);
  letter-spacing: 0.12em;
}

/* ═══ 内容 ═══ */
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
