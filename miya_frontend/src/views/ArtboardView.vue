<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import API from '@/api/art'
import type { ArtProviderInfo, ArtImageEntry, ArtGenerateResult } from '@/types/art'
import PromptPanel from '@/components/artboard/PromptPanel.vue'
import GallerySidebar from '@/components/artboard/GallerySidebar.vue'
import DoodleCanvas from '@/components/artboard/DoodleCanvas.vue'

const isInArtboardWindow = ref(false)
const showDoodle = ref(false)
const router = useRouter()
const previewImage = ref<ArtImageEntry | null>(null)
const selectedImage = ref<ArtImageEntry | null>(null)
const zoom = ref(1)

const generating = ref(false)
const generateResult = ref<ArtGenerateResult | null>(null)
const error = ref('')

const gallery = ref<ArtImageEntry[]>([])
const showGallery = ref(true)

onMounted(async () => {
  try {
    isInArtboardWindow.value = !!(window as any).__IS_ARTBOARD_WINDOW__
  } catch {}
  await loadGallery()
})

async function loadGallery() {
  try {
    const res = await API.getGallery({ limit: 100 })
    gallery.value = res.images || []
  } catch {}
}

async function handleGenerate(params: {
  prompt: string
  provider: string
  negativePrompt: string
  width: number
  height: number
  steps: number
  cfgScale: number
  seed: number | null
  numImages: number
  style: string
}) {
  generating.value = true
  error.value = ''
  generateResult.value = null

  try {
    const res = await API.generate(params)
    generateResult.value = res

    if (res.success && res.images.length > 0) {
      gallery.value.unshift(...res.images)
      selectImage(res.images[0]!)
    } else {
      error.value = res.error || '生成失败'
    }
  } catch (e: any) {
    error.value = e?.message || '请求失败'
  } finally {
    generating.value = false
  }
}

function selectImage(img: ArtImageEntry) {
  selectedImage.value = img
  zoom.value = 1
}

function deleteImage(img: ArtImageEntry) {
  API.deleteImage(img.id)
  gallery.value = gallery.value.filter(i => i.id !== img.id)
  if (selectedImage.value?.id === img.id) {
    selectedImage.value = null
  }
}

function clearGallery() {
  API.clearGallery()
  gallery.value = []
  selectedImage.value = null
}

function getImageSrc(img: ArtImageEntry): string {
  return API.getImageUrl(img.filename)
}

async function fitCanvas() {
  zoom.value = 1
  await new Promise(r => setTimeout(r, 50))
  const canvas = document.getElementById('art-canvas')?.parentElement
  if (!canvas || !selectedImage.value) return
  const cw = canvas.clientWidth - 40
  const ch = canvas.clientHeight - 40
  const iw = selectedImage.value.width || 1024
  const ih = selectedImage.value.height || 1024
  zoom.value = Math.min(cw / iw, ch / ih, 2)
}

function handleWheel(e: WheelEvent) {
  e.preventDefault()
  zoom.value = Math.max(0.1, Math.min(5, zoom.value - e.deltaY * 0.001))
}
</script>

<template>
  <div class="artboard-layout h-screen flex bg-gray-950 text-gray-100 overflow-hidden">
    <!-- Left Panel: Prompt Input -->
    <div class="left-panel w-72 shrink-0 border-r border-gray-800 flex flex-col">
      <div class="p-3 border-b border-gray-800 flex items-center gap-2">
        <button
          class="w-6 h-6 rounded flex items-center justify-center text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
          title="返回"
          @click="router.push('/')"
        >
          ←
        </button>
        <div class="w-3 h-3 rounded-full bg-blue-500" />
        <span class="text-sm font-medium">弥娅画板</span>
        <div class="flex-1" />
        <button
          class="w-7 h-7 rounded-md flex items-center justify-center text-gray-500 hover:text-white hover:bg-gray-800 text-xs transition-colors"
          :class="{ 'text-blue-400 bg-gray-800': showDoodle }"
          title="涂鸦模式"
          @click="showDoodle = !showDoodle"
        >
          ✏
        </button>
        <button
          class="w-7 h-7 rounded-md flex items-center justify-center text-gray-500 hover:text-white hover:bg-gray-800 text-xs transition-colors"
          :class="{ 'text-blue-400 bg-gray-800': !showGallery }"
          title="切换画廊"
          @click="showGallery = !showGallery"
        >
          {{ showGallery ? '⊟' : '⊞' }}
        </button>
      </div>

      <div class="flex-1 overflow-y-auto">
        <PromptPanel
          :generating="generating"
          @generate="handleGenerate"
        />
      </div>

      <div class="p-2 border-t border-gray-800 text-xs text-gray-600 flex items-center justify-between">
        <span>{{ gallery.length }} 张作品</span>
        <button
          v-if="gallery.length > 0"
          class="text-red-700 hover:text-red-500 transition-colors"
          title="清空画廊"
          @click="clearGallery"
        >
          清空
        </button>
      </div>
    </div>

    <!-- Center: Canvas / Doodle -->
    <div class="flex-1 flex flex-col min-w-0">
      <div
        v-if="showDoodle"
        class="flex-1 flex items-center justify-center"
      >
        <DoodleCanvas
          :reference-image="selectedImage ? getImageSrc(selectedImage) : ''"
          @close="showDoodle = false"
        />
      </div>

      <div
        v-else-if="selectedImage"
        class="flex-1 flex flex-col items-center justify-center p-4 overflow-auto"
        @wheel="handleWheel"
      >
        <div class="flex items-center gap-2 mb-3 shrink-0">
          <button class="art-btn-sm" @click="zoom = Math.max(0.1, zoom - 0.2)">−</button>
          <span class="text-xs text-gray-500 w-12 text-center">{{ Math.round(zoom * 100) }}%</span>
          <button class="art-btn-sm" @click="zoom = Math.min(5, zoom + 0.2)">+</button>
          <button class="art-btn-sm" @click="fitCanvas">适应</button>
          <button class="art-btn-sm" @click="zoom = 1">1:1</button>
        </div>

        <div id="art-canvas" class="flex-1 flex items-center justify-center min-h-0 w-full">
          <img
            :src="getImageSrc(selectedImage)"
            :style="{
              transform: `scale(${zoom})`,
              maxWidth: `${100 / zoom}%`,
              maxHeight: `${100 / zoom}%`,
            }"
            class="rounded-lg shadow-2xl transition-transform duration-150 object-contain"
            draggable="false"
          >
        </div>

        <div class="text-xs text-gray-600 mt-2 shrink-0 text-center">
          {{ selectedImage.prompt?.slice(0, 100) || '' }}
          <span class="text-gray-700"> · {{ selectedImage.width }}x{{ selectedImage.height }}</span>
          <span v-if="selectedImage.provider" class="text-gray-700"> · {{ selectedImage.provider }}</span>
        </div>
      </div>

      <!-- Generating state -->
      <div
        v-else-if="generating"
        class="flex-1 flex flex-col items-center justify-center gap-4"
      >
        <div class="w-12 h-12 border-3 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <span class="text-gray-400">弥娅正在创作中...</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="error"
        class="flex-1 flex flex-col items-center justify-center gap-3"
      >
        <span class="text-red-400">{{ error }}</span>
        <button class="art-btn" @click="error = ''">关闭</button>
      </div>

      <!-- Empty -->
      <div
        v-else
        class="flex-1 flex flex-col items-center justify-center gap-3 text-gray-600"
      >
        <svg class="w-16 h-16 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <span>在左侧输入 prompt，让弥娅为你创作</span>
      </div>
    </div>

    <!-- Right Panel: Gallery -->
    <div
      v-if="showGallery"
      class="right-panel w-64 shrink-0 border-l border-gray-800"
    >
      <GallerySidebar
        :images="gallery"
        :selected-id="selectedImage?.id"
        @select="selectImage"
        @delete="deleteImage"
      />
    </div>
  </div>
</template>

<style scoped>
.artboard-layout {
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
}

.art-btn {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  background: #1e293b;
  color: #e2e8f0;
  border: 1px solid #334155;
  cursor: pointer;
  transition: all 0.15s;
}
.art-btn:hover {
  background: #334155;
  border-color: #475569;
}
.art-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.art-btn-sm {
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 12px;
  background: #1e293b;
  color: #cbd5e1;
  border: 1px solid #334155;
  cursor: pointer;
  transition: all 0.15s;
}
.art-btn-sm:hover {
  background: #334155;
  color: #f1f5f9;
}

.art-input {
  width: 100%;
  padding: 8px 10px;
  border-radius: 6px;
  background: #1a1f2e;
  border: 1px solid #334155;
  color: #e2e8f0;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}
.art-input:focus {
  border-color: #3b82f6;
}

.art-select {
  width: 100%;
  padding: 8px 10px;
  border-radius: 6px;
  background: #1a1f2e;
  border: 1px solid #334155;
  color: #e2e8f0;
  font-size: 13px;
  outline: none;
  cursor: pointer;
}
</style>
