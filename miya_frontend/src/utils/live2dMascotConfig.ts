import { useStorage } from '@vueuse/core'

export const mascotCfg = useStorage('miya-live2d-mascot-config', {
  enabled: true,
})
