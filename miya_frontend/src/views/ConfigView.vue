<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { Slider, InputText, ToggleSwitch } from 'primevue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import API from '@/api/core'
import { CONFIG } from '@/utils/config'
import { audioSettings, bgmFileOptions, playBgm, stopBgm } from '@/composables/useAudio'
import { componentColors, COLOR_GROUPS } from '@/composables/useComponentColors'

const router = useRouter()
type TabKey = 'appearance' | 'model' | 'soul' | 'memory' | 'system' | 'audio' | 'color' | 'live2d'
const activeTab = ref<TabKey>('appearance')
const backendOnline = ref(false)

// ── 实时数据 ──
const systemStatus = ref<any>(null)
const personaData = ref<any>(null)
const platformData = ref<any[]>([])
const memoryStats = ref<any>(null)
const providerList = ref<any[]>([])

// ── 配置文件编辑器 ──
const configFiles = ref<Array<{ name: string, path: string, size: number }>>([])
const editingFile = ref('')
const editingContent = ref('')
const editingSaved = ref(false)

// ── Live2D 独立窗口配置 ──
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

async function loadConfigFiles() {
  try {
    const res = await fetch('http://localhost:9800/api/desktop/files/list?path=config').then(r => r.json())
    configFiles.value = (res.files || []).filter((f: any) => !f.is_dir && (f.name.endsWith('.json') || f.name.endsWith('.yaml') || f.name.endsWith('.yml')))
  } catch {}
}

async function openConfigFile(filePath: string) {
  try {
    const res = await fetch(`http://localhost:9800/api/desktop/files/read?path=${encodeURIComponent(filePath)}`).then(r => r.json())
    editingFile.value = filePath
    editingContent.value = res.content || JSON.stringify(res.data || res, null, 2)
    editingSaved.value = false
  } catch { editingContent.value = '读取失败' }
}

async function saveConfigFile() {
  try {
    await fetch('http://localhost:9800/api/desktop/files/write', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: editingFile.value, content: editingContent.value }),
    })
    editingSaved.value = true
    setTimeout(() => editingSaved.value = false, 2000)
  } catch { alert('保存失败') }
}

onMounted(async () => {
  loadBgManifest()
  try {
    const health = await API.health()
    backendOnline.value = health.status === 'healthy'
    if (!backendOnline.value) return

    const [status, persona, mem, providers] = await Promise.allSettled([
      API.systemStatus(),
      API.getCurrentPersona(),
      API.getMemoryStats(),
      API.getConfig().then((c: any) => c?.providers || []).catch(() => []),
    ])
    systemStatus.value = status.status === 'fulfilled' ? status.value : null
    personaData.value = persona.status === 'fulfilled' ? persona.value : null
    memoryStats.value = mem.status === 'fulfilled' ? mem.value : null
    providerList.value = providers.status === 'fulfilled' ? providers.value : []

    // 平台
    const plat = await fetch('http://localhost:9800/api/v1/platforms').then(r => r.json()).catch(() => ({}))
    platformData.value = plat.platforms || []
    loadConfigFiles()
  } catch {}
})

const tabs: { key: TabKey, label: string, icon: string }[] = [
  { key: 'appearance', label: '外观', icon: '✦' },
  { key: 'model', label: '模型', icon: '◈' },
  { key: 'soul', label: '灵魂', icon: '♥' },
  { key: 'memory', label: '记忆', icon: '◆' },
  { key: 'audio', label: '声音', icon: '♪' },
  { key: 'color', label: '调色', icon: '⬡' },
  { key: 'live2d', label: 'Live2D', icon: '◉' },
  { key: 'system', label: '系统', icon: '◎' },
]

// 外观
const cardScale = useStorage('miya-panel-card-scale', 1.0)
const verseText = useStorage('miya-verse-text', '雪落无声 — 愿系铃中')
const showStatus = useStorage('miya-show-status', true)
const logoBrightness = useStorage('miya-logo-brightness', 1.0)
const footerBrightness = useStorage('miya-footer-brightness', 1.0)

const hudColorMode = useStorage('miya-hud-color', 'mixed')
const COLOR_MODES = [
  { key: 'mixed', label: '混色', colors: ['#00e5ff', '#ff6b9d', '#b44dff', '#ff4488'] },
  { key: 'cyan', label: '青蓝', colors: ['#00e5ff'] },
  { key: 'warm', label: '暖粉', colors: ['#ff6b9d', '#ff4488'] },
  { key: 'purple', label: '紫调', colors: ['#b44dff'] },
  { key: 'blue', label: '深蓝', colors: ['#4488ff'] },
]

// 背景
const bgImage = useStorage('miya-bg-image', '')
const bgOpacity = useStorage('miya-bg-opacity', 0.35)
const bgFileInput = ref<HTMLInputElement>()
const BUILTIN_BG = ['aims.jpg']
const builtinBgs = ref<string[]>([...BUILTIN_BG])

// 加载背景列表
async function loadBgManifest() {
  try {
    const res = await fetch('/backgrounds/manifest.json')
    if (res.ok) {
      const list = await res.json()
      if (Array.isArray(list)) builtinBgs.value = [...new Set([...BUILTIN_BG, ...list])]
    }
  } catch {}
}

function pickBgFile() { bgFileInput.value?.click() }
function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => { bgImage.value = reader.result as string }
  reader.readAsDataURL(file)
}
function selectBg(name: string) { bgImage.value = `/backgrounds/${name}` }
function selectNone() { bgImage.value = '' }

// ── 辅助 ──
const modelDefaults: Record<string, string> = {
  simple_chat: '对话', complex_reasoning: '推理', code_analysis: '代码分析',
  creative_writing: '创作', tool_calling: '工具调用', summarization: '摘要',
  image_description: '图像', agent_mode: 'Agent', computer_use: '电脑操作',
}

// ── 声音 ──
const currentBgmFile = ref(bgmFileOptions[0] || '')

function formatBgmName(file: string): string {
  return file.replace(/\.\w+$/, '').replace(/^\d+\.\s*/, '')
}

function switchBgm(file: string) {
  currentBgmFile.value = file
  if (audioSettings.value.bgmEnabled) {
    playBgm(file)
  }
}

// ── 调色 ──
function resetAllComponentColors() {
  const map: Record<string, string> = {}
  for (const g of COLOR_GROUPS) {
    for (const c of g.colors) map[c.key] = c.default
  }
  componentColors.value = map
}
function resetComponentGroup(id: string) {
  const g = COLOR_GROUPS.find(x => x.id === id)
  if (!g) return
  const updated = { ...(componentColors.value as Record<string, string>) }
  for (const c of g.colors) updated[c.key] = c.default
  componentColors.value = updated
}

function getRouteModel(key: string): string {
  const names: Record<string, string> = {
    simple_chat: 'deepseek-v4-flash', complex_reasoning: 'deepseek-v4-flash',
    code_analysis: 'deepseek-v4-flash', creative_writing: 'deepseek-v4-flash',
    tool_calling: 'deepseek-v4-flash', summarization: 'llama-3.1-8b',
    image_description: 'glm-4.6v', agent_mode: 'claude-sonnet', computer_use: 'claude-sonnet',
  }
  return names[key] || key
}
</script>

<template>
  <div class="config-layout">
    <!-- 侧边 Tab 栏 -->
    <aside class="config-sidebar">
      <div class="sidebar-header">
        <button class="back-btn" @click="router.push('/')" title="返回首页">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
        </button>
        <span class="sidebar-title">弥娅调谐</span>
      </div>
      <nav class="sidebar-nav">
        <button
          v-for="tab in tabs" :key="tab.key"
          class="tab-btn" :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <span class="tab-icon">{{ tab.icon }}</span>
          <span class="tab-label">{{ tab.label }}</span>
        </button>
      </nav>
      <div class="sidebar-version">v{{ CONFIG.system.version || '7.0' }}</div>
    </aside>

    <!-- 内容区 -->
    <main class="config-main">
      <!-- ═══ 外观 ═══ -->
      <div v-show="activeTab === 'appearance'" class="config-page">
        <h2>外观设置</h2>

        <div class="config-section">
          <h3>背景图片</h3>
          <p class="hint">将图片放入 public/backgrounds/ 文件夹</p>
          <div class="bg-grid">
            <div class="bg-thumb" :class="{ active: !bgImage }" @click="selectNone"><span class="bg-default">默认</span></div>
            <div v-for="name in builtinBgs" :key="name" class="bg-thumb" :class="{ active: bgImage === `/backgrounds/${name}` }" @click="selectBg(name)">
              <img :src="`/backgrounds/${name}`" alt="">
            </div>
          </div>
          <div class="bg-actions">
            <button class="action-btn" @click="pickBgFile">+ 添加图片</button>
            <input ref="bgFileInput" type="file" accept="image/*" class="hidden" @change="onFileChange">
          </div>
          <div class="config-item" style="margin-top:0.6rem">
            <label>不透明度</label>
            <div class="slider-row"><Slider v-model="bgOpacity" :min="0" :max="1" :step="0.01" /><span class="slider-val">{{ Math.round(bgOpacity * 100) }}%</span></div>
          </div>
        </div>

        <div class="config-section">
          <h3>首页卡片大小</h3>
          <div class="config-item">
            <div class="slider-row">
              <Slider v-model="cardScale" :min="0.6" :max="2" :step="0.05" />
              <span class="slider-val">{{ Math.round(cardScale * 100) }}%</span>
            </div>
          </div>
        </div>

        <div class="config-section">
          <h3>Logo 辉光</h3>
          <div class="config-item">
            <div class="slider-row">
              <Slider v-model="logoBrightness" :min="0.3" :max="2.5" :step="0.01" />
              <span class="slider-val">{{ Math.round(logoBrightness * 100) }}%</span>
            </div>
          </div>
        </div>

        <div class="config-section">
          <h3>首页底栏</h3>
          <div class="config-item">
            <label>底部文案</label>
            <InputText v-model="verseText" placeholder="输入一句话..." class="input-sm" />
          </div>
          <div class="config-item">
            <label>显示在线状态</label>
            <ToggleSwitch v-model="showStatus" />
          </div>
          <div class="config-item" style="margin-top:0.6rem">
            <label>底栏亮度</label>
            <div class="slider-row">
              <Slider v-model="footerBrightness" :min="0.3" :max="2.5" :step="0.01" />
              <span class="slider-val">{{ Math.round(footerBrightness * 100) }}%</span>
            </div>
          </div>
        </div>

        <div class="config-section">
          <h3>HUD 色彩</h3>
          <p class="hint">全局配色请至「调色」tab</p>
          <div class="color-modes">
            <button v-for="m in COLOR_MODES" :key="m.key" class="color-btn" :class="{ active: hudColorMode === m.key }" @click="hudColorMode = m.key">
              <span class="color-dots"><span v-for="c in m.colors" :key="c" class="dot" :style="{ background: c }" /></span>
              <span class="color-label">{{ m.label }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- ═══ 模型 ═══ -->
      <div v-show="activeTab === 'model'" class="config-page">
        <h2>模型配置</h2>
        <div v-if="!backendOnline" class="offline-hint">● 后端未连接</div>
        <template v-else>
        <div class="config-section">
          <h3>默认路由</h3>
          <div class="model-item" v-for="(label, key) in modelDefaults" :key="key">
            <span class="model-name">{{ label }}</span>
            <span class="model-val">{{ getRouteModel(key) }}</span>
          </div>
        </div>
        <div class="config-section">
          <h3>注册模型 ({{ providerList.length }})</h3>
          <div class="model-item" v-for="p in providerList.slice(0, 8)" :key="p.id || p.name">
            <span class="model-name">{{ p.name || p.id }}</span>
            <span class="model-val status-on">{{ p.provider || 'API' }}</span>
          </div>
        </div>
        <div class="config-section">
          <h3>协作模式</h3>
          <div class="model-item"><span class="model-name">单模型</span><span class="model-val">复杂度 ≤ 2</span></div>
          <div class="model-item"><span class="model-name">链式</span><span class="model-val">复杂度 ≤ 3</span></div>
          <div class="model-item"><span class="model-name">并行</span><span class="model-val">复杂度 ≤ 4</span></div>
        </div>
        </template>
      </div>

      <!-- ═══ 灵魂 ═══ -->
      <div v-show="activeTab === 'soul'" class="config-page">
        <h2>灵魂 & 情绪</h2>
        <div v-if="!backendOnline" class="offline-hint">● 后端未连接</div>
        <template v-else>
        <div class="config-section">
          <h3>当前状态</h3>
          <div class="model-item"><span class="model-name">人格</span><span class="model-val">{{ personaData?.persona?.name || personaData?.persona?.id || '默认' }}</span></div>
        </div>
        </template>
      </div>

      <!-- ═══ 记忆 ═══ -->
      <div v-show="activeTab === 'memory'" class="config-page">
        <h2>记忆系统</h2>
        <div v-if="!backendOnline" class="offline-hint">● 后端未连接</div>
        <template v-else>
        <div class="config-section">
          <h3>存储统计</h3>
          <div class="model-item"><span class="model-name">记忆节点</span><span class="model-val">{{ memoryStats?.nodeCount || memoryStats?.node_count || 0 }}</span></div>
          <div class="model-item"><span class="model-name">记忆边</span><span class="model-val">{{ memoryStats?.edgeCount || memoryStats?.edge_count || 0 }}</span></div>
          <div class="model-item"><span class="model-name">存储大小</span><span class="model-val">{{ memoryStats?.memorySize || memoryStats?.memory_size || 'N/A' }}</span></div>
        </div>
        <div class="config-section">
          <h3>记忆层级</h3>
          <div class="model-item"><span class="model-name">短期记忆</span><span class="model-val">TTL 3600s</span></div>
          <div class="model-item"><span class="model-name">对话记忆</span><span class="model-val">每会话 100 条</span></div>
          <div class="model-item"><span class="model-name">长期记忆</span><span class="model-val">最多 10000 条</span></div>
          <div class="model-item"><span class="model-name">语义记忆</span><span class="model-val status-on">SQLite / 1024维</span></div>
        </div>
        </template>
      </div>

      <!-- ═══ 系统 ═══ -->
      <div v-show="activeTab === 'system'" class="config-page">
        <h2>系统</h2>
        <div class="config-section">
          <h3>API 连接</h3>
          <div class="model-item"><span class="model-name">后端状态</span><span class="model-val" :class="backendOnline ? 'status-on' : ''">{{ backendOnline ? '● 在线' : '○ 离线' }}</span></div>
          <div class="config-item" style="margin-top:0.5rem">
            <label>API 地址</label>
            <InputText v-model="CONFIG.api.base_url" placeholder="http://localhost:9800" class="input-sm" />
          </div>
        </div>
        <div class="config-section">
          <h3>平台状态 ({{ platformData.length }})</h3>
          <div class="model-item" v-for="p in platformData" :key="p.platform_id">
            <span class="model-name">{{ p.platform_name }}</span>
            <span class="model-val" :class="p.status === 'online' ? 'status-on' : ''">{{ p.status === 'online' ? '在线' : p.status }}</span>
          </div>
          <div v-if="!platformData.length && backendOnline" class="model-item"><span class="model-name">加载中...</span></div>
        </div>
        <div class="config-section">
          <h3>安全</h3>
          <div class="model-item"><span class="model-name">权限管理</span><span class="model-val status-on">已启用</span></div>
          <div class="model-item"><span class="model-name">注入检测</span><span class="model-val status-on">已启用</span></div>
          <div class="model-item"><span class="model-name">审计日志</span><span class="model-val status-on">已启用</span></div>
        </div>
        <div class="config-section">
          <h3>配置文件</h3>
          <p class="hint">编辑 JSON/YAML 配置文件，保存后需重启生效</p>
          <div class="file-list">
            <button v-for="f in configFiles" :key="f.name" class="file-btn" :class="{ active: editingFile === f.path }" @click="openConfigFile(f.path)">
              <span class="file-name">{{ f.name }}</span>
              <span class="file-size">{{ (f.size / 1024).toFixed(1) }}KB</span>
            </button>
          </div>
          <div v-if="editingFile" class="editor-area" style="margin-top:0.5rem">
            <div class="editor-header">
              <span class="editor-path">{{ editingFile }}</span>
              <div class="editor-actions">
                <span v-if="editingSaved" class="saved-msg">✓ 已保存</span>
                <button class="action-btn" @click="saveConfigFile">保存</button>
                <button class="action-btn" @click="editingFile = ''">关闭</button>
              </div>
            </div>
            <textarea v-model="editingContent" class="editor-text" rows="20" spellcheck="false" />
          </div>
        </div>
      </div>

      <!-- ═══ 声音 ═══ -->
      <div v-show="activeTab === 'audio'" class="config-page">
        <h2>声音</h2>
        <div class="config-section">
          <h3>背景音乐</h3>
          <div class="toggle-row">
            <span class="model-name">启用</span>
            <ToggleSwitch v-model="audioSettings.bgmEnabled" />
          </div>
          <div class="config-item" style="margin-top:0.5rem">
            <label>音量</label>
            <div class="slider-row">
              <Slider v-model="audioSettings.bgmVolume" :min="0" :max="1" :step="0.01" />
              <span class="slider-val">{{ Math.round(audioSettings.bgmVolume * 100) }}%</span>
            </div>
          </div>
          <div class="config-item">
            <label>曲目</label>
            <div class="color-modes">
              <button
                v-for="file in bgmFileOptions" :key="file"
                class="color-btn file-btn-audio"
                :class="{ active: currentBgmFile === file }"
                @click="switchBgm(file)"
              >
                {{ formatBgmName(file) }}
              </button>
            </div>
          </div>
        </div>
        <div class="config-section">
          <h3>音效</h3>
          <div class="toggle-row">
            <span class="model-name">启用</span>
            <ToggleSwitch v-model="audioSettings.effectEnabled" />
          </div>
          <div class="config-item" style="margin-top:0.5rem">
            <label>音量</label>
            <div class="slider-row">
              <Slider v-model="audioSettings.effectVolume" :min="0" :max="1" :step="0.01" />
              <span class="slider-val">{{ Math.round(audioSettings.effectVolume * 100) }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ 调色 ═══ -->
      <div v-show="activeTab === 'color'" class="config-page">
        <h2>组件调色</h2>
        <p class="hint" style="margin-top:-0.5rem">每个组件独立配色，点击色块即可调整</p>
        <button class="action-btn" style="margin-bottom:0.8rem" @click="resetAllComponentColors()">
          恢复全部默认
        </button>
        <div v-for="group in COLOR_GROUPS" :key="group.id" class="config-section color-group">
          <h3 class="color-group-header">
            <span>{{ group.icon }} {{ group.label }}</span>
            <button class="action-btn ml-a" @click="resetComponentGroup(group.id)">恢复</button>
          </h3>
          <div class="color-picker-grid">
            <div v-for="c in group.colors" :key="c.key" class="color-picker-item">
              <label class="cp-label">{{ c.label }}</label>
              <div class="cp-row">
                <input
                  type="color"
                  :value="componentColors[c.key] || c.default"
                  class="cp-input"
                  @input="(e: Event) => { const tar = e.target as HTMLInputElement; componentColors[c.key] = tar.value }"
                >
                <span class="cp-val">{{ componentColors[c.key] || c.default }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ Live2D 独立窗口 ═══ -->
      <div v-show="activeTab === 'live2d'" class="config-page">
        <h2>Live2D 独立窗口</h2>
        <p class="hint" style="margin-top:-0.5rem">控制独立弥娅渲染窗口的显示效果</p>

        <div class="config-section">
          <h3>窗口背景</h3>
          <div class="live2d-color-row">
            <input
              type="color"
              :value="live2dCfg.bgColor"
              class="cp-input"
              style="width:48px;height:36px;border-radius:6px;border:1px solid rgba(0,229,255,0.2)"
              @input="setLive2dBg($event)"
            >
            <span style="font-size:0.75rem;color:var(--miya-text-dim)">{{ live2dCfg.bgColor }}</span>
          </div>
        </div>

        <div class="config-section">
          <h3>背景透明度</h3>
          <div class="slider-row">
            <Slider v-model="live2dCfg.bgAlpha" :min="0" :max="1" :step="0.05" style="flex:1" @update:model-value="setLive2dBg()" />
            <span class="slider-val">{{ Math.round(live2dCfg.bgAlpha * 100) }}%</span>
          </div>
        </div>

        <div class="config-section">
          <h3>窗口缩放</h3>
          <div class="slider-row">
            <Slider v-model="live2dCfg.windowScale" :min="50" :max="200" :step="5" style="flex:1" @update:model-value="setLive2dScale()" />
            <span class="slider-val">{{ live2dCfg.windowScale }}%</span>
          </div>
        </div>

        <div class="config-section">
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

        <div class="config-section">
          <h3>窗口位置</h3>
          <div style="display:flex;gap:0.5rem">
            <button class="action-btn" @click="resetLive2dPos()">重置位置</button>
            <button class="action-btn" @click="resetLive2dSize()">重置大小</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.config-layout { display: flex; height: 100%; }
.config-sidebar {
  width: 140px; flex-shrink: 0;
  background: rgba(8,14,24,0.6); border-right: 1px solid rgba(0,229,255,0.08);
  display: flex; flex-direction: column; padding: 0.8rem 0;
}
.sidebar-header { display: flex; align-items: center; gap: 0.5rem; padding: 0 0.8rem 0.6rem; border-bottom: 1px solid rgba(0,229,255,0.06); }
.sidebar-title { font-family: 'Noto Serif SC', serif; font-size: 0.9rem; color: var(--miya-accent); }
.sidebar-version { margin-top: auto; padding: 0.6rem 0.8rem 0; font-size: 0.6rem; color: var(--miya-text-dim); border-top: 1px solid rgba(0,229,255,0.04); }

.sidebar-nav { display: flex; flex-direction: column; padding: 0.4rem; gap: 1px; }
.tab-btn {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem 0.6rem; border-radius: 0.3rem; cursor: pointer;
  background: transparent; border: none; color: var(--miya-text-dim);
  font-size: 0.78rem; transition: all 0.2s; text-align: left;
}
.tab-btn:hover { background: rgba(0,229,255,0.05); color: var(--miya-text); }
.tab-btn.active { background: rgba(0,229,255,0.08); color: var(--miya-accent); }
.tab-icon { font-size: 0.8rem; width: 1.2rem; text-align: center; }

.config-main { flex: 1; overflow-y: auto; padding: 1.2rem 1.5rem; color: var(--miya-text); font-size: 0.82rem; }
.config-page h2 { font-family: 'Noto Serif SC', serif; font-size: 1.1rem; color: var(--miya-accent); margin: 0 0 1.2rem; }
.config-section { margin-bottom: 1.4rem; }
.config-section h3 { font-size: 0.72rem; font-weight: 600; color: var(--miya-primary); margin: 0 0 0.6rem; letter-spacing: 0.08em; text-transform: uppercase; }
.hint { font-size: 0.68rem; color: var(--miya-text-dim); margin-bottom: 0.6rem; }

.config-item { margin-bottom: 0.7rem; }
.config-item label { display: block; font-size: 0.75rem; color: var(--miya-text); margin-bottom: 0.25rem; }
.slider-row { display: flex; align-items: center; gap: 0.6rem; }
.slider-row :first-child { flex: 1; }
.slider-val { font-size: 0.7rem; color: var(--miya-text-dim); min-width: 2.5rem; text-align: right; }

.input-sm { width: 100%; max-width: 280px; background: rgba(10,18,32,0.8) !important; border: 1px solid rgba(0,229,255,0.15) !important; border-radius: 0.3rem !important; color: rgba(220,235,255,0.9) !important; padding: 0.3rem 0.5rem !important; font-size: 0.75rem; }

.back-btn { display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 0.3rem; border: 1px solid rgba(0,229,255,0.12); background: rgba(0,229,255,0.04); color: rgba(0,229,255,0.6); cursor: pointer; transition: all 0.2s; }
.back-btn:hover { background: rgba(0,229,255,0.1); border-color: rgba(0,229,255,0.3); }

/* 背景 */
.bg-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.3rem; }
.bg-thumb { aspect-ratio: 4/3; border-radius: 0.2rem; overflow: hidden; cursor: pointer; border: 2px solid transparent; background: var(--miya-surface); display: flex; align-items: center; justify-content: center; }
.bg-thumb img { width: 100%; height: 100%; object-fit: cover; }
.bg-thumb:hover { border-color: rgba(0,229,255,0.15); }
.bg-thumb.active { border-color: rgba(0,229,255,0.4); }
.bg-default { font-size: 0.6rem; color: var(--miya-text-dim); }
.bg-actions { margin-top: 0.4rem; }

.action-btn { padding: 0.2rem 0.6rem; font-size: 0.68rem; border: 1px dashed rgba(0,229,255,0.15); border-radius: 0.2rem; background: transparent; color: rgba(0,229,255,0.35); cursor: pointer; transition: all 0.2s; }
.action-btn:hover { border-color: rgba(0,229,255,0.4); color: rgba(0,229,255,0.6); }
.ml-a { margin-left: auto; }

/* 颜色 */
.color-modes { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.color-btn { display: flex; align-items: center; gap: 0.25rem; padding: 0.2rem 0.5rem; border-radius: 0.25rem; cursor: pointer; border: 1px solid rgba(0,229,255,0.06); background: rgba(0,229,255,0.02); color: var(--miya-text-dim); font-size: 0.7rem; transition: all 0.2s; }
.color-btn:hover { border-color: rgba(0,229,255,0.2); }
.color-btn.active { border-color: rgba(0,229,255,0.4); background: rgba(0,229,255,0.06); color: var(--miya-accent); }
.color-dots { display: flex; gap: 1px; }
.dot { width: 6px; height: 6px; border-radius: 50%; }

/* 模型/灵魂/记忆/系统信息项 */
.model-item { display: flex; justify-content: space-between; align-items: center; padding: 0.35rem 0; border-bottom: 1px solid rgba(0,229,255,0.04); font-size: 0.75rem; }
.model-name { color: var(--miya-text-dim); }
.model-val { color: var(--miya-text); font-size: 0.7rem; }
.status-on { color: rgba(0,229,255,0.6); }

.offline-hint {
  padding: 1rem; text-align: center;
  color: var(--miya-text-dim); font-size: 0.8rem;
  border: 1px dashed rgba(0,229,255,0.1); border-radius: 0.3rem;
}

.emotion-bar {
  flex: 1; height: 6px; background: rgba(0,229,255,0.06);
  border-radius: 3px; overflow: hidden; margin-left: 0.5rem;
  max-width: 120px;
}
.emotion-fill {
  height: 100%; background: linear-gradient(90deg, rgba(0,229,255,0.3), rgba(0,229,255,0.6));
  transition: width 0.5s ease;
}

/* 声音 */
.toggle-row { display: flex; align-items: center; justify-content: space-between; padding: 0.35rem 0; border-bottom: 1px solid rgba(0,229,255,0.04); }
.file-btn-audio { font-size: 0.68rem; }

/* 调色 */
.color-group-header { display: flex; align-items: center; gap: 0.4rem; }
.color-picker-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; margin-top: 0.4rem; }
.color-picker-item { padding: 0.4rem; background: rgba(0,0,0,0.15); border-radius: 0.25rem; border: 1px solid rgba(0,229,255,0.05); }
.cp-label { display: block; font-size: 0.65rem; color: var(--miya-text-dim); margin-bottom: 0.3rem; }
.cp-row { display: flex; align-items: center; gap: 0.4rem; }
.cp-input { width: 28px; height: 22px; border: 1px solid rgba(0,229,255,0.15); border-radius: 0.2rem; background: transparent; cursor: pointer; padding: 1px; }
.cp-val { font-size: 0.6rem; color: var(--miya-text-dim); font-family: 'JetBrains Mono', monospace; }

/* Live2D 配置 */
.live2d-color-row { display: flex; align-items: center; gap: 0.6rem; }
.slider-row { display: flex; align-items: center; gap: 0.8rem; }
.slider-row .p-slider { flex: 1; }
.slider-val { font-size: 0.72rem; color: var(--miya-accent); min-width: 3rem; text-align: right; }
.toggle-row { display: flex; align-items: center; justify-content: space-between; padding: 0.3rem 0; }
</style>
