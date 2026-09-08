import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'path'
import { fileURLToPath } from 'node:url'

// 2026-09 修复：项目路径含 '#' 时（如 F:\#Ranxin\Miya），Vite 的 cleanUrl
// 把模块路径中 '#' 之后的内容当 URL 锚点截断，解析必败。
// 解法：start.bat 创建无 '#' 的目录联接并从联接路径启动，此配置做两层兜底：
//   1. preserveSymlinks 阻止 native realpath 穿透联接回真实路径；
//   2. hashPathFixPlugin 把仍带真实路径的 id/importer 映射回联接路径。
// 注意：__dirname 会被 Vite 用 native realpath 穿透，需回退 process.cwd()。
const _configDir = path.dirname(fileURLToPath(import.meta.url))
const _cwd = process.cwd()
const __dirname = _configDir.includes('#') && !_cwd.includes('#') ? _cwd : _configDir

const _norm = (p: string) => p.replace(/\\/g, '/')
const _realRootN = _norm([_configDir, _cwd].find((p) => p.includes('#')) ?? '').replace(/\/+$/, '')
const _launchRootN = _norm([_configDir, _cwd].find((p) => !p.includes('#')) ?? '').replace(/\/+$/, '')

function mapHashPath(p: string): string {
  if (!_realRootN || !_launchRootN) return p
  const n = _norm(p)
  if (n.toLowerCase().startsWith(_realRootN.toLowerCase() + '/')) {
    return _launchRootN + n.slice(_realRootN.length)
  }
  return p
}

function hashPathFixPlugin(): Plugin {
  if (!_realRootN || !_launchRootN) return { name: 'miya-hash-path-fix-disabled', enforce: 'pre' }
  return {
    name: 'miya-hash-path-fix',
    enforce: 'pre',
    resolveId(source, importer) {
      const mappedImporter = importer ? mapHashPath(importer) : importer
      if (mappedImporter && importer && mappedImporter !== importer) {
        return this.resolve(mapHashPath(source), mappedImporter, { skipSelf: true })
      }
      return null
    },
    load(id) {
      const mapped = mapHashPath(id)
      if (mapped === id || id.includes('\0')) return null
      try {
        if (fs.statSync(mapped).isFile()) return fs.readFileSync(mapped, 'utf-8')
      } catch {
        /* 虚拟模块交给默认加载器 */
      }
      return null
    },
  }
}

export default defineConfig({
  plugins: [hashPathFixPlugin(), react()],
  resolve: { preserveSymlinks: true },
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/mgmt': {
        target: 'http://localhost:9800',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/mgmt/, '/api/v1'),
      },
    },
  },
  build: {
    outDir: path.resolve(__dirname, '..', 'packages', 'web', 'dist'),
    emptyOutDir: true,
  },
})
