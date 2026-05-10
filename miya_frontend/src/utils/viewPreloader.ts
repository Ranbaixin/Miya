const VIEW_IMPORTS: Array<{ name: string, load: () => Promise<any> }> = [
  { name: 'PanelView', load: () => import('@/views/PanelView.vue') },
  { name: 'MessageView', load: () => import('@/views/MessageView.vue') },
  { name: 'MindView', load: () => import('@/views/MindView.vue') },
  { name: 'ConfigView', load: () => import('@/views/ConfigView.vue') },
]

export async function preloadAllViews(
  onProgress?: (loaded: number, total: number) => void,
): Promise<void> {
  const total = VIEW_IMPORTS.length
  for (let i = 0; i < total; i++) {
    const view = VIEW_IMPORTS[i]!
    try {
      await view.load()
    }
    catch (e) {
      console.warn(`[Preload] ${view.name} 加载失败，跳过:`, e)
    }
    onProgress?.(i + 1, total)
  }
}
