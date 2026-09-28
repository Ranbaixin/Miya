import process from 'node:process'
import fs from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import vue from '@vitejs/plugin-vue'
import unocss from 'unocss/vite'
import { defineConfig, type Plugin } from 'vite'
import electron from 'vite-plugin-electron/simple'

// 注意：Vite 加载配置文件时会用 native realpath 归一化 import.meta.url，
// 联接路径启动时 __dirname 仍可能被穿透为含 '#' 的真实路径；
// 此时回退到 process.cwd()（从联接路径启动时为无 '#' 的联接路径）。
const _configDir = fileURLToPath(new URL('.', import.meta.url))
const _cwd = process.cwd()
const __dirname =
  _configDir.includes('#') && !_cwd.includes('#') ? _cwd : _configDir
const isWebOnly = !!process.env.WEB_ONLY

// 2026-09 修复：项目路径含 '#' 时（如 F:\#Ranxin\Miya），Vite 的 cleanUrl
// （postfixRE=/[?#].*$/）把模块路径中 '#' 之后的内容当 URL 锚点截断，解析必败。
// 三层修复：
//   1. start.bat 创建无 '#' 的目录联接（junction）并从联接路径启动；
//   2. preserveSymlinks 阻止大部分 native realpath 穿透联接；
//   3. 下面的插件兜底：Vite 内部异步切换 realpath 实现（native 穿透联接），
//      仍会有部分模块 id 带上真实路径，且失败点随机。此插件把含 '#' 的
//      id/importer 确定性映射回联接路径后再走默认解析。
const _realRoot = [_configDir, _cwd].find((p) => p.includes('#')) ?? ''
const _launchRoot = [_configDir, _cwd].find((p) => !p.includes('#')) ?? ''
const _norm = (p: string) => p.replace(/\\/g, '/')
const _realRootN = _norm(_realRoot).replace(/\/+$/, '')
const _launchRootN = _norm(_launchRoot).replace(/\/+$/, '')

function mapHashPath(p: string): string {
  if (!_realRootN || !_launchRootN) return p
  const n = _norm(p)
  if (n.toLowerCase().startsWith(_realRootN.toLowerCase() + '/')) {
    return _launchRootN + n.slice(_realRootN.length)
  }
  return p
}

function hashPathFixPlugin(): Plugin {
  if (!_realRootN || !_launchRootN) return {
    name: 'miya-hash-path-fix-disabled',
    enforce: 'pre',
  }
  return {
    name: 'miya-hash-path-fix',
    enforce: 'pre',
    resolveId(source, importer) {
      const mappedImporter = importer ? mapHashPath(importer) : importer
      if (mappedImporter && importer && mappedImporter !== importer) {
        // importer 曾被 native realpath 穿透为含 '#' 的真实路径：
        // 用映射后的干净 importer 重新走一遍默认解析管线（跳过本钩子防递归）
        return this.resolve(mapHashPath(source), mappedImporter, {
          skipSelf: true,
        })
      }
      return null
    },
    load(id) {
      const mapped = mapHashPath(id)
      if (mapped === id || id.includes('\0')) return null
      try {
        if (fs.statSync(mapped).isFile()) {
          return fs.readFileSync(mapped, 'utf-8')
        }
      } catch {
        /* 非真实文件（虚拟模块等），交给默认加载器 */
      }
      return null
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  base: './',
  plugins: [
    hashPathFixPlugin(),
    vue(),
    unocss(),
    !isWebOnly && electron({
      main: {
        entry: 'electron/main.ts',
        vite: {
          resolve: { preserveSymlinks: true },
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
          resolve: { preserveSymlinks: true },
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
  resolve: { alias: { '@': resolve(__dirname, 'src') }, preserveSymlinks: true },
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
