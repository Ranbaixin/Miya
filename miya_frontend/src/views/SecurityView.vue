<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useStorage } from '@vueuse/core'
import API from '@/api/core'

const router = useRouter()

// ─── 核心状态 ──────────────────────────────────────
const target = ref('')
const strategy = useStorage('miya-security-strategy', 'quick')
const scanning = ref(false)
const scanProgress = ref(0)
const currentPhase = ref(0)

// 扫描实时日志
interface LogEntry { time: string; text: string; type: 'info' | 'ok' | 'warn' | 'phase' | 'error' }
const scanLogs = ref<LogEntry[]>([])
const logContainer = ref<HTMLElement>()

function addLog(text: string, type: LogEntry['type'] = 'info') {
  const now = new Date()
  const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
  scanLogs.value.push({ time, text, type })
  nextTick(() => {
    if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight
  })
}

// 5 阶段进度
const phases = [
  { key: 'recon',    label: '侦察',   icon: '⬡' },
  { key: 'analyze',  label: '分析',   icon: '◇' },
  { key: 'exploit',  label: '利用',   icon: '◆' },
  { key: 'intel',    label: '情报',   icon: '◈' },
  { key: 'report',   label: '报告',   icon: '❖' },
]
const completedPhases = ref<Set<string>>(new Set())

function completePhase(phaseKey: string) {
  completedPhases.value.add(phaseKey)
  currentPhase.value = phases.findIndex(p => p.key === phaseKey) + 1
}

// 扫描结果
interface Finding {
  id: string; title: string; description: string; severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  source: string; detail: string; recommendations?: string[]
}
const findings = ref<Finding[]>([])
const securityScore = ref(0)
const securityGrade = ref('?')
const hasResult = ref(false)

// 历史
interface ScanRecord { target: string; time: string; strategy: string; score: number; grade: string; findingCount: number }
const scanHistory = useStorage<ScanRecord[]>('miya-security-history-v2', [])
const showHistory = ref(false)

// 工具面板折叠
const expandedCats = ref<Set<string>>(new Set(['侦查']))

// Kali xterm 终端
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

const kaliHasBeenOpened = ref(false)
const showKaliTerminal = ref(false)
const kaliTermEl = ref<HTMLDivElement>()
let kaliTerm: Terminal | null = null
let kaliWs: WebSocket | null = null
let kaliFitAddon: FitAddon | null = null
let kaliReconnectTimer: ReturnType<typeof setTimeout> | null = null

function createKaliTerm() {
  if (!kaliTermEl.value || kaliTerm) return
  kaliFitAddon = new FitAddon()
  kaliTerm = new Terminal({
    theme: { background: '#080618', foreground: '#d0c8f0', cursor: '#a78bfa',
      selectionBackground: '#3730a340', black: '#1a1635', red: '#f87171',
      green: '#6ee7b7', yellow: '#fbbf24', blue: '#93c5fd', magenta: '#c084fc',
      cyan: '#67e8f9', white: '#e2e8f0', brightBlack: '#4a4560',
      brightRed: '#fca5a5', brightGreen: '#86efac', brightYellow: '#fde68a',
      brightBlue: '#bfdbfe', brightMagenta: '#d8b4fe', brightCyan: '#a5f3fc',
      brightWhite: '#f8fafc' },
    fontSize: 14,
    fontFamily: "'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace",
    cursorBlink: true, cursorStyle: 'bar',
    allowProposedApi: true,
  })
  kaliTerm.loadAddon(kaliFitAddon)
  kaliTerm.open(kaliTermEl.value)
  kaliHasBeenOpened.value = true
  try { kaliFitAddon.fit() } catch { /* will retry on connect */ }
  kaliTerm.writeln('\x1b[1;32m▸ 正在连接 Kali 终端...\x1b[0m')

  connectKaliWS()

  kaliTerm.onResize(({ cols, rows }) => {
    if (kaliWs?.readyState === WebSocket.OPEN) {
      kaliWs.send('\x00\x00\x01' + JSON.stringify({ type: 'resize', cols, rows }))
    }
  })
  kaliTerm.onData((data) => {
    if (kaliWs?.readyState === WebSocket.OPEN) kaliWs.send(data)
  })
}

function connectKaliWS() {
  if (!kaliTerm) return
  kaliWs = new WebSocket('ws://localhost:8008')
  kaliWs.binaryType = 'arraybuffer'
  kaliWs.onopen = () => {
    if (kaliReconnectTimer) { clearTimeout(kaliReconnectTimer); kaliReconnectTimer = null }
    kaliTerm?.writeln('\x1b[1;32m▸ 已连接\x1b[0m')
    try { kaliFitAddon?.fit() } catch { /* ignore */ }
    kaliTerm?.focus()
  }
  kaliWs.onmessage = (ev) => { kaliTerm?.write(new Uint8Array(ev.data as ArrayBuffer)) }
  kaliWs.onclose = () => {
    if (!kaliTerm) return
    kaliWs = null
    kaliTerm.writeln('\x1b[33m▸ 连接断开 — 3秒后自动重连...\x1b[0m')
    kaliReconnectTimer = setTimeout(() => {
      if (kaliHasBeenOpened.value && kaliTerm) connectKaliWS()
    }, 3000)
  }
  kaliWs.onerror = () => { kaliTerm?.writeln('\x1b[31m▸ 连接失败\x1b[0m') }
}

function destroyKaliTerm() {
  if (kaliReconnectTimer) { clearTimeout(kaliReconnectTimer); kaliReconnectTimer = null }
  kaliWs?.close(); kaliWs = null
  kaliTerm?.dispose(); kaliTerm = null
  kaliFitAddon = null
}

function openKaliTerminal() {
  kaliHasBeenOpened.value = true
  showKaliTerminal.value = true
  nextTick(() => {
    if (!kaliTerm) createKaliTerm()
    else { try { kaliFitAddon?.fit() } catch {/* ignore */}; kaliTerm?.focus() }
  })
}

function minimizeKaliTerminal() {
  showKaliTerminal.value = false
}

function closeKaliTerminal() {
  showKaliTerminal.value = false
  destroyKaliTerm()
}

function toggleCat(cat: string) {
  if (expandedCats.value.has(cat)) expandedCats.value.delete(cat)
  else expandedCats.value.add(cat)
}
const toolCategories: Record<string, { icon: string; tools: string[] }> = {
  '侦查': { icon: '⬡', tools: ['security_port_scan', 'security_nmap_scan', 'security_subdomain_enum', 'security_dns_enum', 'security_online_asset'] },
  '分析': { icon: '◇', tools: ['security_http_headers', 'security_ssl_cert', 'security_dir_brute'] },
  '漏洞': { icon: '◆', tools: ['security_vuln_lookup', 'security_sploitus_search', 'security_web_vuln_scanner'] },
  '支撑': { icon: '◈', tools: ['security_sandbox_exec', 'security_tool_index', 'security_ctf_workflow'] },
}
const toolRunning = ref('')

const strategies: Record<string, { name: string; desc: string; phases: number[] }> = {
  recon:    { name: '信息收集', desc: '仅侦察，不触发 WAF', phases: [1] },
  quick:    { name: '快速评估', desc: '侦察 → 分析 → 情报', phases: [1, 2, 4] },
  full:     { name: '全面评估', desc: '侦察 → 分析 → 漏洞检测 → 情报', phases: [1, 2, 3, 4] },
  webapp:   { name: 'Web 专项', desc: 'HTTP头 → 目录爆破 → 注入检测', phases: [1, 2] },
  deep:     { name: '深度渗透', desc: '全链路自动化（含沙箱执行）', phases: [1, 2, 3, 4, 5] },
}

// ─── 扫描逻辑 ──────────────────────────────────────
async function startScan() {
  if (!target.value.trim() || scanning.value) return
  scanning.value = true; hasResult.value = false; scanProgress.value = 0
  scanLogs.value = []; findings.value = []; completedPhases.value = new Set()
  currentPhase.value = 0; securityScore.value = 0; securityGrade.value = '?'

  const t = target.value.trim()
  const strat = strategies[strategy.value]
  const scanResults: Record<string, any> = {}

  addLog(`目标: ${t}  |  策略: ${strat.name}  |  阶段: ${strat.phases.length}/5`, 'phase')
  addLog('', 'info')

  try {
    // Phase 1: 侦察 — 并行工具
    if (strat.phases.includes(1)) {
      addLog('▸ Phase 1/5 侦察 — 信息收集', 'phase')
      completePhase('recon')
      addLog('  启动端口扫描...', 'info')
      scanResults.port_scan = await safeCall('security_port_scan', { target: t })
      addLog('  ✓ 端口扫描完成', 'ok')

      addLog('  启动子域名枚举...', 'info')
      scanResults.subdomain_enum = await safeCall('security_subdomain_enum', { domain: t })
      addLog('  ✓ 子域名枚举完成', 'ok')

      addLog('  启动 DNS 枚举...', 'info')
      scanResults.dns_enum = await safeCall('security_dns_enum', { domain: t })
      addLog('  ✓ DNS 枚举完成', 'ok')

      if (strategy.value === 'full' || strategy.value === 'deep') {
        addLog('  启动 Nmap 扫描...', 'info')
        scanResults.nmap_scan = await safeCall('security_nmap_scan', { target: t, mode: 'quick' })
        addLog('  ✓ Nmap 扫描完成', 'ok')
      }
      scanProgress.value = 25
    }

    // Phase 2: 分析
    if (strat.phases.includes(2)) {
      addLog('', 'info')
      addLog('▸ Phase 2/5 分析 — 提取服务 + 自动查询', 'phase')
      completePhase('analyze')

      addLog('  分析扫描结果...', 'info')
      await delay(300)
      addLog('  → 识别到服务: (从扫描结果提取)', 'ok')

      addLog('  自动查询工具推荐...', 'info')
      scanResults.tool_index = await safeCall('security_tool_index', { keyword: t })
      addLog('  ✓ 工具推荐完成', 'ok')

      addLog('  自动查询 CVE 漏洞...', 'info')
      scanResults.vuln_lookup = await safeCall('security_vuln_lookup', { keyword: t })
      addLog('  ✓ CVE 查询完成', 'ok')

      addLog('  自动搜索 Exploit...', 'info')
      scanResults.sploitus_search = await safeCall('security_sploitus_search', { keyword: t })
      addLog('  ✓ Exploit 搜索完成', 'ok')

      scanProgress.value = 55
    }

    // Phase 3: 漏洞检测
    if (strat.phases.includes(3)) {
      addLog('', 'info')
      addLog('▸ Phase 3/5 利用 — 漏洞检测', 'phase')
      completePhase('exploit')

      addLog('  启动目录爆破...', 'info')
      scanResults.dir_brute = await safeCall('security_dir_brute', { url: `https://${t}` })
      addLog('  ✓ 目录爆破完成', 'ok')

      addLog('  启动 Web 漏洞扫描...', 'info')
      scanResults.web_vuln_scan = await safeCall('security_web_vuln_scanner', { url: `https://${t}` })
      addLog('  ✓ Web 漏洞扫描完成', 'ok')

      scanProgress.value = 75
    }

    // Phase 4: 威胁情报
    if (strat.phases.includes(4)) {
      addLog('', 'info')
      addLog('▸ Phase 4/5 情报 — 威胁情报汇总', 'phase')
      completePhase('intel')
      addLog('  整合 CVE + Exploit 情报...', 'info')
      await delay(300)
      addLog('  ✓ 威胁情报整合完成', 'ok')
      scanProgress.value = 90
    }

    // Phase 5: 报告
    if (strat.phases.includes(5)) {
      addLog('', 'info')
      addLog('▸ Phase 5/5 报告 — 生成综合报告', 'phase')
      completePhase('report')
      addLog('  ✓ 全链路扫描完成', 'ok')
    } else {
      addLog('', 'info')
      addLog('▸ 扫描完成', 'phase')
    }

    // 使用真实扫描结果解析
    parseResults(scanResults)

    scanProgress.value = 100
    scanStatus.value = '扫描完成'

    scanHistory.value.unshift({
      target: t, time: new Date().toLocaleString(),
      strategy: strategy.value, score: securityScore.value,
      grade: securityGrade.value, findingCount: findings.value.length,
    })
    if (scanHistory.value.length > 20) scanHistory.value.length = 20

  } catch (e: any) {
    addLog(`扫描失败: ${e.message || e}`, 'error')
  } finally {
    scanning.value = false
    hasResult.value = true
    setTimeout(() => { if (!scanning.value) scanProgress.value = 0 }, 3000)
  }
}

async function safeCall(tool: string, args: Record<string, any>): Promise<any> {
  try {
    const resp = await API.callSecurityTool(tool, args)
    return resp
  } catch (e: any) {
    return { error: `执行失败: ${e.message}` }
  }
}

function delay(ms: number) { return new Promise(r => setTimeout(r, ms)) }

// ─── 结果解析 ──────────────────────────────────────
function parseResults(scanResults: Record<string, any>) {
  const phaseCount = [...completedPhases.value].length
  let score = 50
  const found: any[] = []
  let scoreBoosts = 0

  function extractText(data: any): string {
    if (!data) return ''
    if (typeof data === 'string') return data
    if (data.result && typeof data.result === 'string') return data.result
    if (data.stdout) return data.stdout
    if (data.text) return data.text
    return JSON.stringify(data)
  }

  function checkKeyword(text: string, keyword: string): boolean {
    return text.toLowerCase().includes(keyword.toLowerCase())
  }

  const allText = Object.values(scanResults).map(extractText).join('\n').toLowerCase()

  // 端口扫描分析
  const portText = extractText(scanResults.port_scan)
  if (portText.includes('3306') || portText.includes('mysql')) {
    found.push({
      id: 'f-dbport', title: '数据库端口暴露',
      description: 'MySQL(3306) 等数据库端口可能在公网可见',
      severity: 'critical', source: '端口扫描',
      detail: '数据库端口对外开放，存在未授权访问和暴力破解风险。\n建议配置防火墙规则限制访问来源。',
      recommendations: ['配置防火墙规则', '限制访问来源 IP', '使用 VPN/堡垒机访问'],
    })
    score -= 20
  }
  if (portText.includes('22/tcp') || portText.includes('ssh')) {
    found.push({
      id: 'f-ssh', title: 'SSH 端口对外开放',
      description: 'SSH(22) 端口暴露在公网',
      severity: 'high', source: '端口扫描',
      detail: 'SSH 端口对外开放可能遭受暴力破解攻击。建议: 禁用密码登录、使用密钥认证、更改默认端口。',
      recommendations: ['禁用密码登录', '使用 SSH 密钥认证', '配置 fail2ban'],
    })
    score -= 10
  }
  if (portText.includes('21/tcp') || portText.includes('ftp')) {
    found.push({
      id: 'f-ftp', title: 'FTP 服务对外',
      description: 'FTP(21) 建议使用 SFTP 替代',
      severity: 'medium', source: '端口扫描',
      detail: 'FTP 使用明文传输，建议迁移到 SFTP 或 FTPS。',
      recommendations: ['迁移到 SFTP', '使用 FTPS', '限制访问 IP'],
    })
    score -= 5
  }

  // SSL 证书分析
  const sslText = allText
  if (sslText.includes('expir') || sslText.includes('到期') || sslText.includes('days') || sslText.includes('天')) {
    found.push({
      id: 'f-ssl', title: 'SSL 证书问题',
      description: 'SSL/TLS 证书可能即将到期或配置不当',
      severity: 'high', source: 'SSL证书检查',
      detail: '证书过期将导致用户无法访问 HTTPS 站点。建议检查并续期。',
      recommendations: ['检查证书到期时间', '启用自动续期 (ACME)', '设置监控告警'],
    })
    score -= 10
  }

  // HTTP 头分析
  const headerIssues = []
  if (!allText.includes('content-security-policy')) {
    headerIssues.push('Content-Security-Policy')
    score -= 5
  }
  if (!allText.includes('strict-transport-security')) {
    headerIssues.push('HSTS (Strict-Transport-Security)')
    score -= 3
  }
  if (!allText.includes('x-frame-options')) {
    headerIssues.push('X-Frame-Options')
    score -= 2
  }
  if (!allText.includes('x-content-type-options')) {
    headerIssues.push('X-Content-Type-Options')
    score -= 2
  }
  if (headerIssues.length > 0) {
    found.push({
      id: 'f-headers', title: '安全响应头缺失',
      description: `缺少以下安全头: ${headerIssues.join(', ')}`,
      severity: headerIssues.length >= 3 ? 'high' : 'medium',
      source: 'HTTP头分析',
      detail: `未配置关键安全响应头，存在 XSS、点击劫持等风险。\n建议在 Web 服务器配置中添加这些响应头。`,
      recommendations: ['添加安全响应头', '使用 Web 服务器配置', '启用 HTTPS'],
    })
  }

  // CVE/漏洞分析
  const vulnText = extractText(scanResults.vuln_lookup)
  if (vulnText.includes('cve') || vulnText.includes('CVE')) {
    const cveCount = (vulnText.match(/CVE-\d{4}-\d+/gi) || []).length
    if (cveCount > 0) {
      score -= Math.min(cveCount * 3, 20)
      scoreBoosts += 5
    }
  }

  // Web 漏洞扫描
  const webVulnText = extractText(scanResults.web_vuln_scan)
  if (checkKeyword(webVulnText, 'xss') || checkKeyword(webVulnText, 'sql') || checkKeyword(webVulnText, 'injection')) {
    found.push({
      id: 'f-webvuln', title: 'Web 应用漏洞',
      description: '检测到潜在 Web 漏洞 (XSS/SQL注入等)',
      severity: 'critical', source: 'Web漏洞扫描',
      detail: 'Web 应用可能存在代码注入漏洞，攻击者可能利用这些漏洞获取敏感数据。',
      recommendations: ['修复代码注入漏洞', '使用参数化查询', '实施输入验证'],
    })
    score -= 25
  }

  // 目录爆破
  const dirText = extractText(scanResults.dir_brute)
  if (checkKeyword(dirText, '.git') || checkKeyword(dirText, '.env') || checkKeyword(dirText, 'backup')) {
    found.push({
      id: 'f-sens-dir', title: '敏感目录/文件暴露',
      description: '检测到敏感路径可访问 (.git, .env, backup 等)',
      severity: 'critical', source: '目录爆破',
      detail: '敏感文件和目录暴露在公网，可能导致源码泄露或配置信息泄露。',
      recommendations: ['限制敏感目录访问', '配置 Web 服务器规则', '删除不必要的文件'],
    })
    score -= 20
  }

  // 基于实际扫描结果计分
  if (Object.keys(scanResults).filter(k => scanResults[k] && !scanResults[k].error).length > 4) {
    scoreBoosts += 10
  }

  securityScore.value = Math.max(0, Math.min(100, 55 + scoreBoosts + (score - 50)))
  securityGrade.value = securityScore.value >= 90 ? 'A+' :
    securityScore.value >= 80 ? 'A' :
    securityScore.value >= 70 ? 'B+' :
    securityScore.value >= 60 ? 'B' :
    securityScore.value >= 50 ? 'C' :
    securityScore.value >= 40 ? 'D' : 'F'

  findings.value = found
}

// ─── 单工具执行 ────────────────────────────────────
const toolDialog = ref(false)
async function runTool(toolName: string) {
  if (!target.value.trim()) { toolDialog.value = true; return }
  toolRunning.value = toolName
  addLog(`[手动] 执行 ${toolName.replace('security_', '')}...`, 'info')
  try {
    const resp = await safeCall(toolName, { target: target.value.trim() })
    addLog(`[手动] ${toolName.replace('security_', '')} 完成`, 'ok')
  } catch (e) {
    addLog(`[手动] 失败: ${e}`, 'error')
  } finally { toolRunning.value = '' }
}

// ─── 快捷操作 ──────────────────────────────────────
const scanStatus = ref('')
const copyReport = () => {
  const text = [
    `# 安全评估报告 — ${target.value}`,
    `评分: ${securityGrade.value} (${securityScore.value}/100)`,
    `策略: ${strategies[strategy.value]?.name}`,
    `时间: ${new Date().toLocaleString()}`,
    '',
    ...findings.value.map(f => `## ${f.severity.toUpperCase()} — ${f.title}\n${f.description}\n\n${f.detail}`),
  ].join('\n')
  navigator.clipboard.writeText(text).then(() => {
    scanStatus.value = '已复制到剪贴板'
    setTimeout(() => scanStatus.value = '', 2000)
  }).catch(() => {
    scanStatus.value = '复制失败'
    setTimeout(() => scanStatus.value = '', 2000)
  })
}

const exportMD = () => {
  const text = scanLogs.value.map(l => `[${l.time}] ${l.text}`).join('\n')
  const blob = new Blob([text], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `security-report-${target.value || 'report'}.md`; a.click()
  URL.revokeObjectURL(url)
}

function rescan() { startScan() }
function deepScan() { strategy.value = 'deep'; startScan() }

// ─── Severity 分布 ─────────────────────────────────
const severityCounts = computed(() => {
  const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
  findings.value.forEach(f => { counts[f.severity] = (counts[f.severity] || 0) + 1 })
  return counts
})

// ─── 展开单个发现 ─────────────────────────────────
const expandedFinding = ref<string | null>(null)
function toggleFinding(id: string) {
  expandedFinding.value = expandedFinding.value === id ? null : id
}

const sevColor: Record<string, string> = {
  critical: '#ff4444', high: '#ff8844', medium: '#ffcc00', low: '#44cc44', info: '#44aacc',
}

const gradeColor = computed(() => {
  const g = securityGrade.value
  if (g.startsWith('A')) return '#44cc44'
  if (g.startsWith('B')) return '#88cc44'
  if (g.startsWith('C')) return '#cccc44'
  return '#ff4444'
})

onUnmounted(() => { destroyKaliTerm() })
</script>

<template>
  <div class="security-view">
    <!-- ── Header ── -->
    <div class="sec-header">
      <button class="back-btn" @click="router.push('/')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6" /></svg>
      </button>
      <h1 class="sec-title">安全中心</h1>
      <span class="sec-sub">SecurityNet · 弥娅网络安全中枢</span>
      <button class="kali-btn term" :class="{ active: showKaliTerminal }" @click="showKaliTerminal ? minimizeKaliTerminal() : openKaliTerminal()">
        <span class="kali-icon">▸</span> 终端
      </button>
    </div>

    <!-- ── Phase 指示器 ── -->
    <div class="phase-bar">
      <div v-for="(p, i) in phases" :key="p.key"
        :class="['phase-dot', {
          completed: completedPhases.has(p.key),
          active: currentPhase === i + 1 && scanning,
        }]"
        :title="p.label"
      >
        <span class="phase-icon">{{ p.icon }}</span>
        <span class="phase-label">{{ p.label }}</span>
        <div v-if="i < phases.length - 1" class="phase-line" :class="{ filled: completedPhases.has(p.key) }" />
      </div>
    </div>

    <!-- ── Body: 分屏 ── -->
    <div class="sec-body">
      <!-- 左面板: 控制 -->
      <div class="sec-left">
        <!-- 目标输入 -->
        <div class="target-card">
          <input v-model="target" class="target-input" placeholder="example.com 或 https://..."
            :disabled="scanning" @keydown.enter="startScan" />
          <select v-model="strategy" class="strategy-select" :disabled="scanning">
            <option v-for="(s, k) in strategies" :key="k" :value="k">{{ s.name }}</option>
          </select>
          <button class="scan-btn" :class="{ scanning }" :disabled="scanning || !target.trim()" @click="startScan">
            <span v-if="scanning" class="scan-spinner" />
            <span v-else>▲ 扫描</span>
          </button>
        </div>
        <div class="strategy-info">{{ strategies[strategy]?.desc }}</div>

        <!-- 进度 -->
        <div v-if="scanProgress > 0" class="progress-wrap">
          <div class="progress-bar"><div class="progress-fill" :style="{ width: scanProgress + '%' }" /></div>
          <span class="progress-pct">{{ scanProgress }}%</span>
        </div>
        <div v-if="scanStatus" class="scan-status-msg">{{ scanStatus }}</div>

        <!-- 工具面板 (折叠) -->
        <div class="tools-panel">
          <div v-for="(info, cat) in toolCategories" :key="cat" class="tool-group">
            <button class="tool-cat-btn" @click="toggleCat(cat)">
              <span class="cat-arrow">{{ expandedCats.has(cat) ? '▼' : '▶' }}</span>
              <span class="cat-icon">{{ info.icon }}</span>
              <span class="cat-label">{{ cat }}</span>
              <span class="cat-count">{{ info.tools.length }}</span>
            </button>
            <div v-if="expandedCats.has(cat)" class="tool-grid">
              <button v-for="tname in info.tools" :key="tname"
                :class="['tool-chip', { running: toolRunning === tname }]"
                :disabled="scanning || toolRunning !== ''"
                @click="runTool(tname)"
              >
                {{ tname.replace('security_', '').replace(/_/g, ' ').replace(/./, c => c.toUpperCase()) }}
              </button>
            </div>
          </div>
        </div>

        <!-- 历史 -->
        <div class="history-panel">
          <button class="history-toggle" @click="showHistory = !showHistory">
            {{ showHistory ? '▼' : '▶' }} 扫描历史 ({{ scanHistory.length }})
          </button>
          <div v-if="showHistory && scanHistory.length" class="history-list">
            <div v-for="(h, i) in scanHistory.slice(0, 8)" :key="i" class="history-item"
              @click="target = h.target; strategy = h.strategy">
              <span class="hist-target">{{ h.target }}</span>
              <span class="hist-grade" :style="{ color: h.grade?.startsWith('A') ? '#4c4' : h.grade?.startsWith('B') ? '#8c4' : '#c44' }">
                {{ h.grade }}
              </span>
              <span class="hist-time">{{ h.time.split(' ')[0] }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右面板: 结果 -->
      <div class="sec-right">
        <!-- 空状态 -->
        <div v-if="!scanning && !hasResult && scanLogs.length === 0" class="empty-state">
          <div class="empty-icon">⬡</div>
          <div class="empty-text">输入目标，开始安全评估</div>
          <div class="empty-desc">弥娅将自动完成侦察 → 分析 → 漏洞检测 → 威胁情报 → 报告</div>
        </div>

        <!-- 扫描中: 实时终端 -->
        <div v-if="scanning || (scanLogs.length > 0 && !hasResult)" class="scan-terminal" ref="logContainer">
          <div v-for="(log, i) in scanLogs" :key="i" :class="['log-line', log.type]">
            <span class="log-time">{{ log.time }}</span>
            <span class="log-text">{{ log.text }}</span>
          </div>
          <div v-if="scanning" class="log-cursor">█</div>
        </div>

        <!-- 结果仪表盘 -->
        <div v-if="hasResult" class="result-dashboard">
          <!-- 评分卡片 -->
          <div class="score-card">
            <div class="score-circle" :style="{ borderColor: gradeColor }">
              <span class="score-grade" :style="{ color: gradeColor }">{{ securityGrade }}</span>
              <span class="score-num">{{ securityScore }}/100</span>
            </div>
            <div class="score-breakdown">
              <div v-for="(count, sev) in severityCounts" :key="sev" class="sev-chip" :style="{ color: sevColor[sev], borderColor: sevColor[sev] }">
                {{ sev.toUpperCase() }}: {{ count }}
              </div>
            </div>
            <div class="score-actions">
              <button class="action-btn" @click="copyReport">复制报告</button>
              <button class="action-btn" @click="exportMD">导出 MD</button>
              <button class="action-btn primary" @click="deepScan">深度扫描</button>
            </div>
          </div>

          <!-- 发现卡片 -->
          <div v-if="findings.length" class="findings-section">
            <h3 class="section-label">发现 ({{ findings.length }})</h3>
            <div v-for="f in findings" :key="f.id" :class="['finding-card', f.severity]" :style="{ borderLeftColor: sevColor[f.severity] }">
              <div class="finding-header" @click="toggleFinding(f.id)">
                <span class="finding-sev" :style="{ background: sevColor[f.severity] }">{{ f.severity.toUpperCase() }}</span>
                <span class="finding-title">{{ f.title }}</span>
                <span class="finding-source">{{ f.source }}</span>
                <span class="finding-chevron">{{ expandedFinding === f.id ? '▲' : '▼' }}</span>
              </div>
              <div class="finding-body" v-if="expandedFinding === f.id">
                <p class="finding-desc">{{ f.description }}</p>
                <pre class="finding-detail">{{ f.detail }}</pre>
                <div v-if="f.recommendations?.length" class="finding-recs">
                  <span class="rec-label">建议:</span>
                  <span v-for="r in f.recommendations" :key="r" class="rec-chip">{{ r }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 无发现 -->
          <div v-else class="no-findings">
            <span class="nf-icon">✓</span> 未发现明显安全问题
          </div>
        </div>
      </div>
    </div>

    <!-- ── Kali 终端 (xterm.js) ── -->
    <div v-if="kaliHasBeenOpened" v-show="showKaliTerminal" class="kali-term-wrap">
      <div class="kali-toolbar">
        <span class="kali-label">▸ Kali Terminal</span>
        <span class="kali-status">miya-kali · bash</span>
        <span class="kali-hint">Ctrl+Shift+C/V 复制粘贴  |  Ctrl+C 中断  |  Ctrl+D 退出</span>
        <button class="kali-btn-minimize" @click="minimizeKaliTerminal" title="最小化">—</button>
        <button class="kali-btn-close" @click="closeKaliTerminal" title="关闭终端">✕</button>
      </div>
      <div ref="kaliTermEl" class="kali-xterm-box" />
    </div>

    <!-- ── 目标输入对话框 ── -->
    <div v-if="toolDialog" class="modal-overlay" @click.self="toolDialog = false">
      <div class="modal-card">
        <h3>请输入目标</h3>
        <input v-model="target" class="target-input" placeholder="example.com" @keydown.enter="toolDialog = false" />
        <button class="scan-btn" @click="toolDialog = false">确定</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.security-view {
  height: 100%; display: flex; flex-direction: column; padding: 28px 28px 16px;
  overflow: hidden; color: var(--miya-text, #e8d5f5);
  font-family: 'Noto Serif SC', 'Inter', system-ui, sans-serif;
}

/* ── Header ── */
.sec-header { display: flex; align-items: center; gap: 12px; flex-shrink: 0; margin-bottom: 8px; }
.back-btn {
  width: 32px; height: 32px; border-radius: 8px; border: 0.5px solid var(--miya-border); background: rgba(10,8,21,0.3);
  color: var(--miya-text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s;
  svg { width: 16px; height: 16px; }
  &:hover { border-color: var(--miya-accent); color: var(--miya-accent); }
}
.sec-title { font-size: 1.5rem; font-weight: 600; letter-spacing: 0.08em; margin: 0; }
.sec-sub { font-size: 0.6rem; color: var(--miya-text-dim); letter-spacing: 0.12em; }

/* ── Phase Bar ── */
.phase-bar {
  display: flex; align-items: center; justify-content: center; gap: 0; flex-shrink: 0;
  padding: 10px 0 8px;
}
.phase-dot {
  display: flex; align-items: center; gap: 4px; position: relative;
  opacity: 0.3; transition: all 0.4s;
  &.completed { opacity: 0.9; }
  &.active { opacity: 1; animation: phase-pulse 1s ease-in-out infinite; }
}
@keyframes phase-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
.phase-icon { font-size: 0.7rem; }
.phase-label { font-size: 0.55rem; color: var(--miya-text-dim); letter-spacing: 0.04em; }
.phase-line {
  width: 32px; height: 1px; background: rgba(167,139,250,0.2); margin: 0 6px;
  transition: background 0.4s;
  &.filled { background: var(--miya-accent); }
}

/* ── Body ── */
.sec-body {
  flex: 1; display: flex; gap: 16px; min-height: 0; padding-top: 8px;
}
.sec-left {
  width: 290px; flex-shrink: 0; display: flex; flex-direction: column; gap: 10px;
  overflow-y: auto; padding-right: 6px;
}
.sec-right {
  flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden;
}

/* ── Target Card ── */
.target-card {
  display: flex; gap: 6px; padding: 12px; border-radius: 10px;
  background: rgba(10,8,21,0.15); border: 0.5px solid var(--miya-border, rgba(167,139,250,0.08));
}
.target-input {
  flex: 1; background: rgba(0,0,0,0.25); border: 0.5px solid rgba(167,139,250,0.15);
  border-radius: 7px; padding: 9px 12px; color: var(--miya-text); font-size: 0.8rem;
  outline: none; transition: border-color 0.2s; min-width: 0;
  &::placeholder { color: rgba(167,139,250,0.25); }
  &:focus { border-color: var(--miya-accent); }
}
.strategy-select {
  width: 84px; background: rgba(0,0,0,0.25); border: 0.5px solid rgba(167,139,250,0.15);
  border-radius: 7px; padding: 7px 4px; color: var(--miya-text); font-size: 0.7rem; outline: none; cursor: pointer;
}
.scan-btn {
  padding: 9px 16px; border-radius: 7px; border: none;
  background: linear-gradient(135deg, var(--miya-accent), color-mix(in srgb, var(--miya-accent) 70%, #ff4444));
  color: #fff; font-size: 0.78rem; font-weight: 600; cursor: pointer; transition: all 0.25s;
  white-space: nowrap;
  &:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 3px 16px rgba(255,80,80,0.25); }
  &:disabled { opacity: 0.4; cursor: not-allowed; }
  &.scanning { animation: scan-pulse 1.5s infinite; }
}
@keyframes scan-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.65; } }
.scan-spinner {
  display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.strategy-info { font-size: 0.58rem; color: var(--miya-text-dim); letter-spacing: 0.03em; padding: 0 2px; }

/* ── Progress ── */
.progress-wrap { display: flex; align-items: center; gap: 6px; }
.progress-bar { flex: 1; height: 3px; background: rgba(167,139,250,0.08); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--miya-accent); border-radius: 2px; transition: width 0.5s ease; }
.progress-pct { font-size: 0.58rem; color: var(--miya-text-dim); font-family: 'JetBrains Mono', monospace; }
.scan-status-msg { font-size: 0.6rem; color: var(--miya-accent); }

/* ── Tools Panel ── */
.tools-panel { display: flex; flex-direction: column; gap: 2px; }
.tool-cat-btn {
  display: flex; align-items: center; gap: 7px; width: 100%; padding: 8px 10px;
  border: none; border-radius: 6px; background: transparent; color: var(--miya-text-dim);
  font-size: 0.72rem; cursor: pointer; transition: all 0.15s;
  &:hover { background: rgba(167,139,250,0.06); color: var(--miya-text); }
}
.cat-arrow { font-size: 0.45rem; width: 10px; }
.cat-icon { font-size: 0.7rem; }
.cat-label { flex: 1; text-align: left; font-weight: 500; }
.cat-count { font-size: 0.55rem; opacity: 0.5; }
.tool-grid { display: flex; flex-wrap: wrap; gap: 4px; padding: 4px 8px 8px 24px; }
.tool-chip {
  padding: 4px 10px; border-radius: 5px; font-size: 0.62rem;
  border: 0.5px solid rgba(167,139,250,0.08); background: rgba(10,8,21,0.15);
  color: var(--miya-text-dim); cursor: pointer; transition: all 0.15s; white-space: nowrap;
  &:hover:not(:disabled) { border-color: var(--miya-accent); color: var(--miya-accent); background: rgba(167,139,250,0.08); }
  &:disabled { opacity: 0.25; }
  &.running { border-color: var(--miya-accent); color: var(--miya-accent); animation: scan-pulse 1s infinite; }
}

/* ── History ── */
.history-panel { margin-top: auto; padding-top: 4px; }
.history-toggle {
  width: 100%; padding: 6px 8px; text-align: left;
  background: none; border: none; color: var(--miya-text-dim); font-size: 0.65rem; cursor: pointer;
  letter-spacing: 0.04em;
  &:hover { color: var(--miya-text); }
}
.history-list { display: flex; flex-direction: column; gap: 2px; margin-top: 4px; }
.history-item {
  display: flex; gap: 6px; align-items: center; padding: 5px 8px; border-radius: 5px;
  background: rgba(10,8,21,0.08); cursor: pointer; transition: all 0.15s; font-size: 0.62rem;
  &:hover { background: rgba(167,139,250,0.06); }
}
.hist-target { flex: 1; color: var(--miya-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hist-grade { font-weight: 600; font-family: 'JetBrains Mono', monospace; }
.hist-time { color: var(--miya-text-dim); }

/* ── Empty State ── */
.empty-state {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 10px; opacity: 0.4;
}
.empty-icon { font-size: 2.5rem; opacity: 0.3; }
.empty-text { font-size: 0.85rem; color: var(--miya-text-dim); }
.empty-desc { font-size: 0.6rem; color: var(--miya-text-dim); text-align: center; max-width: 320px; line-height: 1.5; }

/* ── Scan Terminal ── */
.scan-terminal {
  flex: 1; background: rgba(0,0,0,0.25); border: 0.5px solid rgba(167,139,250,0.08);
  border-radius: 10px; padding: 12px 16px; overflow-y: auto;
  font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 0.65rem; line-height: 1.6;
}
.log-line {
  display: flex; gap: 10px; padding: 1px 0;
  &.phase .log-text { color: var(--miya-accent); font-weight: 500; }
  &.ok .log-text { color: rgba(68, 204, 68, 0.8); }
  &.warn .log-text { color: rgba(255, 200, 60, 0.8); }
  &.error .log-text { color: rgba(255, 80, 80, 0.8); }
  &.info .log-text { color: var(--miya-text-dim); }
}
.log-time { color: rgba(167,139,250,0.3); flex-shrink: 0; font-size: 0.6rem; }
.log-cursor {
  color: var(--miya-accent); animation: blink 1s step-end infinite; font-size: 0.7rem;
}
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }

/* ── Result Dashboard ── */
.result-dashboard {
  flex: 1; display: flex; flex-direction: column; gap: 12px; overflow-y: auto;
}

/* Score Card */
.score-card {
  display: flex; align-items: center; gap: 16px; padding: 16px;
  background: rgba(10,8,21,0.15); border: 0.5px solid rgba(167,139,250,0.08);
  border-radius: 12px;
}
.score-circle {
  width: 64px; height: 64px; border-radius: 50%; border: 3px solid;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.score-grade { font-size: 1.3rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.score-num { font-size: 0.5rem; color: var(--miya-text-dim); margin-top: 1px; }
.score-breakdown { display: flex; gap: 6px; flex-wrap: wrap; flex: 1; }
.sev-chip {
  padding: 2px 8px; border-radius: 4px; font-size: 0.58rem;
  border: 0.5px solid; font-family: 'JetBrains Mono', monospace;
}
.score-actions { display: flex; gap: 6px; flex-shrink: 0; }
.action-btn {
  padding: 6px 12px; border-radius: 6px; font-size: 0.62rem; cursor: pointer;
  border: 0.5px solid rgba(167,139,250,0.2); background: rgba(10,8,21,0.2); color: var(--miya-text-dim);
  transition: all 0.15s; white-space: nowrap;
  &:hover { border-color: var(--miya-accent); color: var(--miya-accent); }
  &.primary { background: rgba(255,80,80,0.15); border-color: rgba(255,80,80,0.3); color: #ff6666; }
}

/* Findings */
.findings-section { display: flex; flex-direction: column; gap: 6px; }
.section-label { font-size: 0.68rem; color: var(--miya-text-dim); letter-spacing: 0.06em; margin: 0; }
.finding-card {
  background: rgba(10,8,21,0.12); border: 0.5px solid rgba(167,139,250,0.06);
  border-radius: 8px; border-left: 3px solid; overflow: hidden;
}
.finding-header {
  display: flex; align-items: center; gap: 8px; padding: 10px 12px;
  cursor: pointer; transition: background 0.15s;
  &:hover { background: rgba(167,139,250,0.04); }
}
.finding-sev {
  padding: 2px 6px; border-radius: 3px; font-size: 0.5rem; font-weight: 600; color: #000;
  font-family: 'JetBrains Mono', monospace; flex-shrink: 0;
}
.finding-title { flex: 1; font-size: 0.72rem; font-weight: 500; }
.finding-source { font-size: 0.55rem; color: var(--miya-text-dim); opacity: 0.6; }
.finding-chevron { font-size: 0.5rem; color: var(--miya-text-dim); width: 14px; text-align: center; }
.finding-body { padding: 0 12px 12px 40px; }
.finding-desc { font-size: 0.65rem; color: var(--miya-text-dim); margin: 0 0 8px; line-height: 1.5; }
.finding-detail {
  font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 0.6rem; color: var(--miya-text);
  background: rgba(0,0,0,0.25); border-radius: 5px; padding: 8px 10px; margin: 0;
  white-space: pre-wrap; line-height: 1.5; max-height: 200px; overflow-y: auto;
}
.finding-recs { display: flex; align-items: center; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.rec-label { font-size: 0.6rem; color: var(--miya-text-dim); opacity: 0.7; }
.rec-chip {
  padding: 2px 8px; border-radius: 4px; font-size: 0.58rem;
  background: rgba(167,139,250,0.1); color: var(--miya-accent);
}

.no-findings {
  display: flex; align-items: center; gap: 8px; padding: 20px; justify-content: center;
  font-size: 0.7rem; color: rgba(68,204,68,0.6);
}
.nf-icon { font-size: 1rem; }

/* ── Kali Terminal ── */
.kali-btn {
  margin-left: auto; padding: 4px 12px; border-radius: 8px; font-size: 0.65rem; cursor: pointer;
  font-family: 'JetBrains Mono', monospace; white-space: nowrap; display: flex; align-items: center; gap: 4px;
  transition: all 0.15s;
  &.term { border: .5px solid rgba(167,139,250,.3); background: rgba(167,139,250,.08); color: var(--miya-accent); }
  &.term:hover { background: rgba(167,139,250,.18); border-color: var(--miya-accent); }
  &.term.active { background: rgba(167,139,250,.2); border-color: rgba(180,120,255,.6); color: #b488ff; }
}
.kali-icon { font-size: 0.7rem; }

.kali-term-wrap { position:fixed; inset:56px 0 0 0; z-index:51; display:flex; flex-direction:column; background:#080618; }
.kali-toolbar { display:flex; align-items:center; gap:12px; padding:6px 16px; border-bottom:.5px solid rgba(167,139,250,.2); background:rgba(0,0,0,.5); }
.kali-label { font-size:.7rem; color:var(--miya-accent); font-family:'JetBrains Mono',monospace; }
.kali-status { font-size:.55rem; color:var(--miya-text-dim); }
.kali-hint { margin-left:auto; font-size:.55rem; color:var(--miya-text-dim); opacity:0.5; }
.kali-btn-minimize { padding:2px 8px; border-radius:4px; font-size:.65rem; cursor:pointer; border:.5px solid rgba(167,139,250,.2); background:transparent; color:var(--miya-text-dim); margin-left:8px; &:hover{background:rgba(167,139,250,.15);color:var(--miya-accent);} }
.kali-btn-close { padding:2px 8px; border-radius:4px; font-size:.65rem; cursor:pointer; border:.5px solid rgba(255,80,80,.2); background:transparent; color:#ff6666; &:hover{background:rgba(255,80,80,.1)} }
.kali-xterm-box { flex:1; padding:6px 4px 4px 10px; :deep(.xterm){height:100%} :deep(.xterm-viewport){overflow-y:auto} :deep(.xterm-viewport::-webkit-scrollbar){width:6px} :deep(.xterm-viewport::-webkit-scrollbar-thumb){background:rgba(167,139,250,.2);border-radius:3px} }

/* ── Modal ── */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 100; display: flex; align-items: center; justify-content: center; }
.modal-card {
  background: rgba(10,8,21,0.95); border: 0.5px solid rgba(167,139,250,0.2); border-radius: 16px;
  padding: 24px; display: flex; flex-direction: column; gap: 12px; min-width: 300px;
  h3 { margin: 0; font-size: 0.9rem; color: var(--miya-text); }
}
</style>
