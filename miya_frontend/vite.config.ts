import process from 'node:process'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import vue from '@vitejs/plugin-vue'
import unocss from 'unocss/vite'
import { defineConfig } from 'vite'
import electron from 'vite-plugin-electron/simple'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const isWebOnly = !!process.env.WEB_ONLY

// https://vite.dev/config/
export default defineConfig({
  base: './',
  plugins: [
    vue(),
    unocss(),
    !isWebOnly && electron({
      main: {
        entry: 'electron/main.ts',
        vite: {
          build: {
            rollupOptions: {
              external: ['electron', 'electron-updater', 'lodash.isequal', '@lydell/node-pty'],
            },
          },
        },
      },
      preload: {
        input: 'electron/preload.ts',
        vite: {
          build: {
            rollupOptions: {
              output: {
                entryFileNames: 'preload.cjs',
                format: 'cjs',
              },
            },
          },
        },
      },
    }),
  ],
  resolve: { alias: { '@': resolve(__dirname, 'src') } },
  optimizeDeps: {
    include: [
      'primevue/accordion',
      'primevue/inputtext',
      'primevue/inputnumber',
      'primevue/select',
      'primevue/toggleswitch',
      'primevue/divider',
      'primevue/datatable',
      'primevue/column',
      'd3',
      'd3-force',
      '@vueuse/core',
    ],
  },
})
