<script lang="ts">
import * as PIXI from 'pixi.js'
</script>

<script setup lang="ts">
import { Live2DModel } from 'pixi-live2d-display/cubism4'
import { computed, nextTick, onMounted, onUnmounted, ref, useTemplateRef, watch } from 'vue'
import { CONFIG } from '@/utils/config'
import { ensureLive2dCoreLoaded } from '@/utils/live2dCoreLoader'
import { destroyController, initController } from '@/utils/live2dController'

const { source, width, height, x, y, scale, ssaa } = defineProps<{
  source: string
  width: number
  height: number
  x: number
  y: number
  scale: number
  ssaa: number
}>()

const emit = defineEmits<{
  modelReady: [pos: { faceX: number, faceY: number }]
}>()

;(window as Window & typeof globalThis & { PIXI: typeof PIXI }).PIXI = PIXI

let app: PIXI.Application

const computedScale = computed(() => scale * ssaa)
const computedWidth = computed(() => width * ssaa)
const computedHeight = computed(() => height * ssaa)

const canvas = useTemplateRef('canvas')

onMounted(async () => {
  if (!canvas.value) return

  app = new PIXI.Application({
    view: canvas.value,
    width: computedWidth.value,
    height: computedHeight.value,
    antialias: true,
    backgroundAlpha: 0,
    resizeTo: canvas.value,
  })

  watch(() => [width, height, ssaa], () => nextTick().then(() => app.resize()))

  watch(() => source, async (source, _, onCleanUp) => {
    try {
      await ensureLive2dCoreLoaded()
      const rawModel = await Live2DModel.from(source)
      const model = Object.assign(rawModel, {
        rawWidth: rawModel.width,
        rawHeight: rawModel.height,
      })

      const computedX = computed(() => width * ssaa * (1 + x) - model.rawWidth * computedScale.value)
      const computedY = computed(() => height * ssaa * (1 + y) - model.rawHeight * computedScale.value)

      const handles = [
        watch(computedScale, scale => model.scale.set(scale), { immediate: true }),
        watch(computedX, x => model.x = x / 2, { immediate: true }),
        watch(computedY, y => model.y = y / 2, { immediate: true }),
      ]

      const s = computedScale.value
      const faceY = CONFIG.value.web_live2d.face_y_ratio ?? 0.25
      const faceX = (model.x + model.rawWidth * s * 0.5) / ssaa
      const fY = (model.y + model.rawHeight * s * faceY) / ssaa
      emit('modelReady', { faceX, faceY: fY })

      model.autoInteract = false
      app.stage.addChild(model)
      await initController(rawModel, source)

      onCleanUp(() => {
        destroyController()
        app.stage.removeChild(model)
        model.destroy()
        handles.forEach(h => h.stop())
      })
    }
    catch (error) {
      console.error('Failed to initialize Live2D:', error)
    }
  }, { immediate: true })
})

onUnmounted(() => {
  if (app) app.destroy()
})
</script>

<template>
  <canvas
    ref="canvas"
    :width="computedWidth" :height="computedHeight"
    :style="{ transform: `scale(${1 / ssaa})`, transformOrigin: '0 0', touchAction: 'none' }"
  />
</template>
