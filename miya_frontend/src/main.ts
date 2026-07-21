import { definePreset } from '@primeuix/themes'
import Lara from '@primeuix/themes/lara'
import PrimeVue from 'primevue/config'
import { createApp } from 'vue'

import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import './style.css'
import 'virtual:uno.css'
import { initComponentColors } from '@/composables/useComponentColors'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: () => import('@/views/PanelView.vue') },
    { path: '/chat', component: () => import('@/views/MessageView.vue') },
    { path: '/mind', component: () => import('@/views/MindView.vue') },
    { path: '/config', component: () => import('@/views/ConfigView.vue') },
    { path: '/float', component: () => import('@/views/FloatingView.vue') },
    { path: '/openclaw', component: () => import('@/views/OpenClawView.vue') },
    { path: '/screen', component: () => import('@/views/ScreenVisionView.vue') },
    { path: '/platforms', component: () => import('@/views/PlatformsView.vue') },
    { path: '/inbox', component: () => import('@/views/MessageInbox.vue') },
    { path: '/terminal', component: () => import('@/views/TerminalView.vue') },
    { path: '/live2d', component: () => import('@/views/Live2dConfigView.vue') },
    { path: '/artboard', component: () => import('@/views/ArtboardView.vue') },
    { path: '/security', component: () => import('@/views/SecurityView.vue') },
    { path: '/hub', component: () => import('@/views/HubView.vue') },
    {
      path: '/community',
      children: [
        { path: '', component: () => import('@/forum/ForumListView.vue') },
        { path: ':id', component: () => import('@/forum/ForumPostView.vue') },
      ],
    },
  ],
})

createApp(App)
  .use(PrimeVue, {
    theme: {
      preset: definePreset(Lara),
      options: {
        darkModeSelector: '.p-dark',
      },
    },
  })
  .use(router)
  .mount('#app')

initComponentColors()
