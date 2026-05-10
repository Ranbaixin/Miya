<script setup lang="ts">
import ScrollPanel from 'primevue/scrollpanel'
import { useTemplateRef } from 'vue'
import { useParallax } from '@/composables/useParallax'

const _props = withDefaults(defineProps<{ parallax?: boolean, boxClass?: string, noScroll?: boolean, hideBack?: boolean }>(), { parallax: true, boxClass: 'w-3/5', noScroll: false, hideBack: false })
const { transform: boxTransform } = useParallax({ rotateX: 3, rotateY: 3, translateX: 12, translateY: 8, invertRotate: true })

const scrollPanelRef = useTemplateRef<{
  scrollTop: (scrollTop: number) => void
}>('scrollPanelRef')

defineExpose({
  scrollToBottom() {
    scrollPanelRef.value?.scrollTop(Infinity)
  },
})
</script>

<template>
  <div
    class="flex min-h-0"
    :class="{ 'will-change-transform': parallax }"
    :style="parallax ? { transform: boxTransform } : undefined"
  >
    <div v-if="!hideBack" class="back-btn" @click="$router.back" title="返回">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="15 18 9 12 15 6" />
      </svg>
    </div>
    <div class="box flex flex-col min-h-0 min-w-0 overflow-hidden" :class="boxClass">
      <div class="box-bracket-tl" />
      <div class="box-bracket-br" />
      <!-- header slot：固定在滚动区域上方，不随内容滚动 -->
      <slot name="header" />
      <template v-if="noScroll">
        <div class="p-4 w-full flex flex-col min-h-0">
          <slot />
        </div>
      </template>
      <ScrollPanel
        v-else
        ref="scrollPanelRef"
        class="size-full"
        :pt="{
          barY: {
            class: 'w-2! rounded! bg-#373737! transition!',
          },
        }"
      >
        <div class="p-4 w-full min-w-0 overflow-hidden">
          <slot />
        </div>
      </ScrollPanel>
    </div>
  </div>
</template>

<style scoped>
.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  margin-right: 0.75rem;
  border: 1px solid color-mix(in srgb, var(--miya-border) 20%, transparent);
  background: color-mix(in srgb, var(--miya-border) 5%, transparent);
  color: color-mix(in srgb, var(--miya-border) 60%, transparent);
  cursor: pointer;
  transition: all 0.25s ease;
}
.back-btn:hover {
  background: color-mix(in srgb, var(--miya-border) 12%, transparent);
  border-color: color-mix(in srgb, var(--miya-border) 50%, transparent);
  color: rgba(0, 229, 255, 0.95);
  box-shadow: 0 0 16px color-mix(in srgb, var(--miya-border) 20%, transparent);
}

.box-bracket-tl {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 20px;
  height: 20px;
  border-top: 2px solid color-mix(in srgb, var(--miya-border) 70%, transparent);
  border-left: 2px solid color-mix(in srgb, var(--miya-border) 70%, transparent);
  pointer-events: none;
  z-index: 3;
}

.box-bracket-br {
  position: absolute;
  bottom: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border-bottom: 2px solid color-mix(in srgb, var(--miya-chat-user) 50%, transparent);
  border-right: 2px solid color-mix(in srgb, var(--miya-chat-user) 50%, transparent);
  pointer-events: none;
  z-index: 3;
}

::-webkit-scrollbar {
  background-color: transparent;
  width: 5px;
}
::-webkit-scrollbar-thumb {
  background-color: color-mix(in srgb, var(--miya-border) 15%, transparent);
  border-radius: 3px;
  height: 20%;
}
::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 229, 255, 0.3);
}
</style>
