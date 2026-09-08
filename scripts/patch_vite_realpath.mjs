#!/usr/bin/env node
/**
 * patch-vite-realpath.mjs — 根治「项目路径含 '#'」下 Vite 的模块解析失败。
 *
 * 背景：Vite 在 Windows 上把内部 realpath 实现优化为 fs.realpathSync.native，
 * 而 native realpath 会「穿透」junction/subst 映射，把模块 id 解析回真实路径。
 * 当真实路径含 '#'（如 F:\#Ranxin\Miya）时，Vite 的 cleanUrl 把 '#' 之后的内容
 * 当作 URL 锚点截断（postfixRE=/[?#].*$/），模块 id 变成 "F:/"，
 * 导致 EISDIR / Pre-transform error / 渲染层白屏。
 *
 * 修复：把 vite 产物中所有 realpathSync.native 替换为 realpathSync（JS 层实现）。
 * 实测（Node 22 / Win11）：非 native realpathSync 对 subst 盘符「不穿透」
 * （fs.realpathSync('M:/miya_frontend') === 'M:\\miya_frontend'），
 * 配合 start.bat 的 subst 盘符启动（:ensure_nohash）即彻底消除穿透。
 * 对普通无映射路径二者行为一致，仅存在微小性能差异。
 *
 * 幂等：替换后不再匹配原模式，可重复运行。挂到 postinstall 保证重装依赖后自动应用。
 */
import { readdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '..')
const roots = [join(repoRoot, 'miya_frontend'), join(repoRoot, 'frontend', 'ui')]

let totalFiles = 0
let totalHits = 0

for (const root of roots) {
  const viteDir = join(root, 'node_modules', 'vite', 'dist', 'node')
  if (!existsSync(viteDir)) continue

  const walk = (dir) => {
    let files = []
    for (const name of readdirSync(dir, { withFileTypes: true })) {
      const p = join(dir, name.name)
      if (name.isDirectory()) files = files.concat(walk(p))
      else if (name.name.endsWith('.js')) files.push(p)
    }
    return files
  }

  for (const file of walk(viteDir)) {
    const src = readFileSync(file, 'utf8')
    if (!src.includes('realpathSync.native')) continue
    const hits = src.split('realpathSync.native').length - 1
    writeFileSync(file, src.split('realpathSync.native').join('realpathSync'))
    totalFiles++
    totalHits += hits
    console.log(`[patch-vite-realpath] ${file} : ${hits} 处替换`)
  }
}

console.log(`[patch-vite-realpath] 完成：${totalFiles} 个文件，${totalHits} 处替换`)
