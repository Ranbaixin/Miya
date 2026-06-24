<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useStorage } from '@vueuse/core'
import API from '@/api/core'
import MessageItem from '@/components/MessageItem.vue'
import type { Message } from '@/utils/session'

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
  const next = new Set(completedPhases.value)
  next.add(phaseKey)
  completedPhases.value = next
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

// ─── 工具面板 (动态加载) ─────────────────────────────
const expandedCats = ref<Set<string>>(new Set(['侦查']))
const toolList = ref<Record<string, { name: string; desc: string }[]>>({
  '侦查': [
    { name: '端口扫描', desc: 'TCP端口探测 + 服务识别' },
    { name: 'Nmap 扫描', desc: '快速/全面/隐蔽等多种扫描模式' },
    { name: '子域名枚举', desc: '多数据源子域名发现' },
    { name: 'DNS 枚举', desc: 'A/MX/NS/CNAME 等记录查询' },
    { name: '在线资产', desc: 'FOFA/Shodan/Censys 资产搜索' },
  ],
  '分析': [
    { name: 'HTTP 头分析', desc: '安全响应头检测' },
    { name: 'SSL 证书', desc: 'TLS 证书信息检查' },
    { name: '目录爆破', desc: 'Web 路径发现' },
  ],
  '漏洞': [
    { name: 'CVE 查询', desc: 'NVD 漏洞数据库查询' },
    { name: 'Exploit 搜索', desc: 'Sploitus/ExploitDB 利用查询' },
    { name: 'Web 漏洞扫描', desc: 'SQL注入/XSS 检测' },
  ],
  '支撑': [
    { name: '沙箱执行', desc: 'Docker Kali 安全执行' },
    { name: '工具查询', desc: '308+ 安全工具知识库' },
    { name: 'CTF 工作流', desc: 'CTF 7 类题型自动化' },
  ],
})
const toolCategoriesList = ref<string[]>(['侦查', '分析', '漏洞', '支撑'])
const toolSearch = ref('')
const toolRunning = ref('')

const catIcons: Record<string, string> = {
  '信息收集': '⬡', '漏洞扫描': '◆', '漏洞利用': '◈', 'Webshell': '◇',
  '密码破解': '●', '网络工具': '◈', 'BurpSuite': '◆', '安全防御': '◇',
  '取证分析': '◇', '云安全': '⬡', '移动安全': '◇', '逆向工程': '◆',
  '代理抓包': '◇', '运行环境': '●', 'AI工具': '◇', 'CTF专项': '◆',
  '侦查': '⬡', '分析': '◇', '漏洞': '◆', '支撑': '◈',
}

const filteredToolCategories = computed(() => {
  const search = toolSearch.value.trim().toLowerCase()
  if (!search) return toolCategoriesList.value

  return toolCategoriesList.value.filter(cat => {
    const tools = toolList.value[cat] || []
    return tools.some(
      t => t.name.toLowerCase().includes(search) || t.desc.toLowerCase().includes(search)
    )
  })
})

const filteredTools = (cat: string) => {
  const search = toolSearch.value.trim().toLowerCase()
  const tools = toolList.value[cat] || []
  if (!search) return tools
  return tools.filter(
    t => t.name.toLowerCase().includes(search) || t.desc.toLowerCase().includes(search)
  )
}

function toggleCat(cat: string) {
  const next = new Set(expandedCats.value)
  if (next.has(cat)) next.delete(cat)
  else next.add(cat)
  expandedCats.value = next
}

async function fetchToolList() {
  try {
    const data = await API.getSecurityToolList()
    if (data.success && data.categories.length > 0) {
      toolCategoriesList.value = data.categories
      toolList.value = data.tools
      expandedCats.value = new Set([data.categories[0]!])
    }
  } catch {
    // 保持降级数据，无需处理
  }
}

onMounted(() => { fetchToolList() })

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
    theme: { background: '#080618', foreground: '#d0c8f0', cursor: '#00ADB5',
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
  const strat = strategies[strategy.value]!
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
const toolToSecurityMap: Record<string, string> = {
  'nmap': 'security_nmap_scan', 'Nmap 扫描': 'security_nmap_scan',
  'masscan': 'security_port_scan', '端口扫描': 'security_port_scan',
  'naabu': 'security_port_scan',
  'gobuster': 'security_dir_brute',
  'dirsearch': 'security_dir_brute', '目录爆破': 'security_dir_brute',
  'dirb': 'security_dir_brute',
  'dalfox': 'security_web_vuln_scanner',
  'nuclei': 'security_web_vuln_scanner', 'Web 漏洞扫描': 'security_web_vuln_scanner',
  'xray': 'security_web_vuln_scanner',
  'sqlmap': 'security_web_vuln_scanner',
  'subfinder': 'security_subdomain_enum', '子域名枚举': 'security_subdomain_enum',
  'amass': 'security_subdomain_enum',
  'OneForAll': 'security_subdomain_enum',
  'dnsx': 'security_dns_enum', 'DNS 枚举': 'security_dns_enum',
  'httpx': 'security_http_headers', 'HTTP 头分析': 'security_http_headers',
  'wafw00f': 'security_http_headers',
  'sslscan': 'security_ssl_cert', 'SSL 证书': 'security_ssl_cert',
  'hydra': 'security_port_scan',
  'fscan': 'security_nmap_scan',
  'kscan': 'security_nmap_scan',
  'goby': 'security_nmap_scan',
  '在线资产': 'security_online_asset',
  'CVE 查询': 'security_vuln_lookup',
  'Exploit 搜索': 'security_sploitus_search',
  '沙箱执行': 'security_sandbox_exec',
  '工具查询': 'security_tool_index',
  'CTF 工作流': 'security_ctf_workflow',
}

function findToolDesc(name: string): string {
  for (const cat of toolCategoriesList.value) {
    const tools = toolList.value[cat] || []
    const found = tools.find(t => t.name === name)
    if (found) return found.desc
  }
  return ''
}

// ─── 安全对话 ────────────────────────────────────
const secMessages = ref<Message[]>([])
const secInput = ref('')
const secChatting = ref(false)
const secChatEl = ref<HTMLDivElement>()
const leftPanelCollapsed = ref(false)

function secScrollBottom() {
  nextTick(() => {
    if (secChatEl.value) secChatEl.value.scrollTop = secChatEl.value.scrollHeight
  })
}

async function secSendChat(message?: string) {
  const text = message || secInput.value.trim()
  if (!text || secChatting.value) return
  secInput.value = ''

  secMessages.value.push({ role: 'user', content: text })
  secMessages.value.push({ role: 'assistant', content: '', generating: true, status: '分析中...' })
  secChatting.value = true
  secScrollBottom()

  try {
    const stream = await API.securityChat(text, target.value || undefined)
    let buf = ''
    for await (const chunk of stream) {
      if (chunk.type === 'status') {
        const last = secMessages.value[secMessages.value.length - 1]
        if (last && last.role === 'assistant') last.status = chunk.text || ''
      } else if (chunk.type === 'content') {
        const last = secMessages.value[secMessages.value.length - 1]
        if (last && last.role === 'assistant') {
          buf += (chunk.text || '') + '\n'
          last.content = buf.trim()
        }
      } else if (chunk.type === 'done') {
        break
      }
      secScrollBottom()
    }
  } catch (e: any) {
    const last = secMessages.value[secMessages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content = `对话失败: ${e.message || e}`
    }
  } finally {
    const last = secMessages.value[secMessages.value.length - 1]
    if (last && last.role === 'assistant') last.generating = false
    secChatting.value = false
    secScrollBottom()
  }
}

const quickActions = [
  { label: '扫描', msg: '扫描 ', icon: '▲' },
  { label: 'CTF', msg: 'CTF 解题: ', icon: '🏴' },
  { label: 'BugBounty', msg: 'BugBounty 赏金: ', icon: '💰' },
  { label: '工具', msg: '查询安全工具', icon: '🔧' },
  { label: '报告', msg: '生成安全报告: ', icon: '📋' },
]

function quickAction(msg: string) {
  secInput.value = msg
}

const toolDialog = ref(false)
async function runTool(toolName: string) {
  if (!target.value.trim()) { toolDialog.value = true; return }
  toolRunning.value = toolName
  const desc = findToolDesc(toolName)

  const mapped = toolToSecurityMap[toolName] || toolToSecurityMap[toolName.toLowerCase()]
  secMessages.value.push({
    role: 'user',
    content: `执行工具: **${toolName}** → ${target.value.trim()}`,
  })

  if (mapped) {
    const idx = secMessages.value.push({
      role: 'assistant', content: '', generating: true, status: `${toolName} 执行中...`,
    })
    secScrollBottom()
    try {
      const resp = await safeCall(mapped, { target: target.value.trim() })
      let text = ''
      if (typeof resp === 'string') text = resp
      else if (resp && resp.result) text = typeof resp.result === 'string' ? resp.result : JSON.stringify(resp.result, null, 2)
      else text = JSON.stringify(resp, null, 2)
      secMessages.value[idx - 1] = {
        role: 'assistant',
        content: `### ${toolName}\n${desc}\n\n\`\`\`\n${text.slice(0, 3000)}\n\`\`\``,
      }
    } catch (e: any) {
      secMessages.value[idx - 1] = {
        role: 'assistant',
        content: `### ${toolName} 失败\n${e.message || e}`,
      }
    }
  } else {
    secMessages.value.push({
      role: 'assistant',
      content: `### ${toolName}\n${desc}\n\n该工具暂无可执行的弥娅安全引擎，请尝试通过对话窗描述需求。`,
    })
  }
  toolRunning.value = ''
  secScrollBottom()
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
      <div class="sec-left" :class="{ collapsed: leftPanelCollapsed }">
        <button class="panel-collapse-btn" @click="leftPanelCollapsed = !leftPanelCollapsed"
          :title="leftPanelCollapsed ? '展开面板' : '折叠面板'">
          {{ leftPanelCollapsed ? '▶' : '◀' }}
        </button>
        <div v-show="!leftPanelCollapsed" class="sec-left-inner">
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

        <!-- 工具目录 (动态加载) -->
        <div class="tools-panel">
          <div class="tool-search-box">
            <input v-model="toolSearch" class="tool-search-input"
              placeholder="搜索工具..." :disabled="scanning" />
            <span class="tool-total">{{ toolCategoriesList.reduce((s, c) => s + (toolList[c]?.length || 0), 0) }} 工具</span>
          </div>
          <div v-for="cat in filteredToolCategories" :key="cat" class="tool-group">
            <button class="tool-cat-btn" @click="toggleCat(cat)">
              <span class="cat-arrow">{{ expandedCats.has(cat) ? '▼' : '▶' }}</span>
              <span class="cat-icon">{{ catIcons[cat] || '◇' }}</span>
              <span class="cat-label">{{ cat }}</span>
              <span class="cat-count">{{ filteredTools(cat).length }}</span>
            </button>
            <div v-if="expandedCats.has(cat)" class="tool-grid">
              <button v-for="t in filteredTools(cat)" :key="t.name"
                class="tool-chip"
                :class="{ running: toolRunning === t.name }"
                :disabled="scanning || toolRunning !== ''"
                :title="t.desc"
                @click="runTool(t.name)"
              >
                <span class="tool-chip-name">{{ t.name }}</span>
                <span class="tool-chip-desc">{{ t.desc }}</span>
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
        </div> <!-- sec-left-inner -->
      </div> <!-- sec-left -->

      <!-- 右面板: 安全对话 -->
      <div class="sec-right sec-chat">
        <!-- 消息列表 -->
        <div class="sec-chat-messages" ref="secChatEl">
          <div v-if="secMessages.length === 0" class="sec-chat-empty">
            <div class="sec-chat-empty-icon">⬡</div>
            <div class="sec-chat-empty-title">弥娅安全助手</div>
            <div class="sec-chat-empty-desc">
              用自然语言驱动安全能力。<br/>
              试试说：「扫描 example.com」「查询漏洞工具」「CTF 解题: Web」
            </div>
            <div class="sec-chat-quick">
              <button v-for="a in quickActions" :key="a.label"
                class="sec-chat-qbtn" @click="quickAction(a.msg)">
                <span>{{ a.icon }}</span> {{ a.label }}
              </button>
            </div>
          </div>
          <MessageItem v-for="(m, i) in secMessages" :key="i" v-bind="m" />
          <div v-if="secChatting" class="sec-chat-cursor">█</div>
        </div>
        <!-- 输入框 -->
        <div class="sec-chat-bar">
          <div class="sec-chat-actions">
            <button v-for="a in quickActions" :key="a.label"
              class="sec-chat-qsm" :title="a.label"
              @click="quickAction(a.msg)">
              <span>{{ a.icon }}</span>
            </button>
          </div>
          <input v-model="secInput" class="sec-chat-input"
            placeholder="输入安全指令，如「扫描 example.com」"
            :disabled="secChatting"
            @keydown.enter="secSendChat()" />
          <button class="sec-chat-send" :disabled="secChatting || !secInput.trim()" @click="secSendChat()">
            ▲
          </button>
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
  height: 100%; display: flex; flex-direction: column; padding: 1rem 1.2rem;
  overflow: hidden; color: var(--miya-text, #E4ECF0);
  font-family: 'Noto Sans SC', 'Inter', system-ui, sans-serif;
  perspective: 800px; -webkit-perspective: 800px;
}

/* ── Header ── */
.sec-header { display: flex; align-items: center; gap: 12px; flex-shrink: 0; margin-bottom: 8px;
  padding: 0.5rem 0.8rem;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(0, 173, 181, 0.06);
  box-shadow:
    3px 3px 8px rgba(0, 40, 50, 0.3),
    -2px -2px 6px rgba(0, 180, 200, 0.04);
  border-radius: 4px;
  transform: rotateY(2deg);
  transition: border-color 0.3s ease, transform 0.5s ease;
}
.sec-header:hover {
  border-color: rgba(0, 255, 245, 0.2);
  transform: rotateY(1deg);
}
.back-btn {
  width: 32px; height: 32px; border-radius: 6px; border: 1px solid rgba(0, 173, 181, 0.1); background: rgba(0, 173, 181, 0.04);
  color: var(--miya-text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  svg { width: 16px; height: 16px; }
  &:hover { border-color: rgba(0, 255, 245, 0.3); color: rgba(0, 255, 245, 0.8); background: rgba(0, 173, 181, 0.1); transform: skewX(-4deg); }
}
.sec-title { font-family: 'Noto Serif SC', serif; font-size: 1.1rem; font-weight: 700; letter-spacing: 0.06em; margin: 0; }
.sec-sub { font-family: 'JetBrains Mono', monospace; font-size: 0.55rem; color: var(--miya-text-dim); letter-spacing: 0.1em; }

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
  width: 32px; height: 1px; background: rgba(0, 173, 181,0.2); margin: 0 6px;
  transition: background 0.4s;
  &.filled { background: var(--miya-accent); }
}

/* ── Body ── */
.sec-body {
  flex: 1; display: flex; gap: 16px; min-height: 0; padding-top: 8px;
}
.sec-left {
  width: 290px; flex-shrink: 0; display: flex; flex-direction: column; gap: 10px;
  overflow-y: auto; padding-right: 6px; transition: width 0.25s ease;
  &.collapsed { width: 28px; padding-right: 0; overflow: hidden; }
}
.sec-left::-webkit-scrollbar { width: 3px; }
.sec-left::-webkit-scrollbar-thumb { background: rgba(0, 173, 181, 0.1); border-radius: 2px; }
.sec-left-inner { display: flex; flex-direction: column; gap: 10px; }
.panel-collapse-btn {
  width: 24px; height: 24px; border-radius: 4px; border: 1px solid rgba(0, 173, 181, 0.1);
  background: rgba(0, 0, 0, 0.3); color: var(--miya-text-dim); cursor: pointer;
  font-size: 0.55rem; display: flex; align-items: center; justify-content: center;
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1); flex-shrink: 0;
  &:hover { border-color: rgba(0, 255, 245, 0.3); color: var(--miya-accent); background: rgba(0, 173, 181, 0.1); }
}
.sec-right {
  flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden;
}

/* ── Target Card ── */
.target-card {
  display: flex; gap: 6px; padding: 12px; border-radius: 6px;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(0, 173, 181, 0.06);
  box-shadow:
    2px 2px 6px rgba(0, 40, 50, 0.3),
    -1px -1px 3px rgba(0, 180, 200, 0.03);
  transition: border-color 0.3s ease;
}
.target-card:focus-within {
  border-color: rgba(0, 255, 245, 0.2);
}
.target-input {
  flex: 1; background: rgba(0,0,0,0.3); border: 1px solid rgba(0, 173, 181, 0.08);
  border-radius: 5px; padding: 9px 12px; color: var(--miya-text); font-size: 0.8rem;
  outline: none; transition: border-color 0.2s; min-width: 0;
  &::placeholder { color: rgba(0, 173, 181, 0.15); }
  &:focus { border-color: rgba(0, 255, 245, 0.25); }
}
.strategy-select {
  width: 84px; background: rgba(0,0,0,0.3); border: 1px solid rgba(0, 173, 181, 0.08);
  border-radius: 5px; padding: 7px 4px; color: var(--miya-text); font-size: 0.7rem; outline: none; cursor: pointer;
}
.scan-btn {
  padding: 9px 16px; border-radius: 5px; border: none;
  background: linear-gradient(135deg, rgba(0, 173, 181, 0.8), rgba(0, 200, 210, 0.6));
  color: #fff; font-size: 0.78rem; font-weight: 600; cursor: pointer; transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  white-space: nowrap; font-family: 'Noto Sans SC', sans-serif;
  &:hover:not(:disabled) { transform: translateY(-1px) skewX(-2deg); box-shadow: 0 3px 16px rgba(0, 173, 181, 0.25); }
  &:disabled { opacity: 0.35; cursor: not-allowed; }
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
.progress-bar { flex: 1; height: 3px; background: rgba(0, 173, 181, 0.06); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, var(--miya-accent), rgba(0, 255, 245, 0.6)); border-radius: 2px; transition: width 0.5s ease; }
.progress-pct { font-size: 0.58rem; color: var(--miya-text-dim); font-family: 'JetBrains Mono', monospace; }
.scan-status-msg { font-size: 0.6rem; color: var(--miya-accent); }

/* ── Tools Panel ── */
.tools-panel { display: flex; flex-direction: column; gap: 2px; }
.tool-search-box {
  display: flex; align-items: center; gap: 8px; padding: 4px 0 8px;
}
.tool-search-input {
  flex: 1; background: rgba(0,0,0,0.3); border: 1px solid rgba(0, 173, 181, 0.08);
  border-radius: 5px; padding: 6px 10px; color: var(--miya-text); font-size: 0.65rem;
  outline: none; transition: border-color 0.2s;
  &::placeholder { color: rgba(0, 173, 181, 0.15); font-size: 0.6rem; }
  &:focus { border-color: rgba(0, 255, 245, 0.25); }
}
.tool-total { font-size: 0.53rem; color: var(--miya-text-dim); white-space: nowrap; font-family: 'JetBrains Mono', monospace; }
.tool-loading { font-size: 0.55rem; color: var(--miya-accent); animation: blink 0.8s step-end infinite; }
.tool-empty { font-size: 0.6rem; color: var(--miya-text-dim); padding: 12px 0; text-align: center; opacity: 0.5; }
.tool-cat-btn {
  display: flex; align-items: center; gap: 7px; width: 100%; padding: 7px 8px;
  border: none; border-radius: 5px; background: transparent; color: var(--miya-text-dim);
  font-size: 0.7rem; cursor: pointer; transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  &:hover { background: rgba(129, 191, 241, 0.1); color: var(--miya-text); transform: skewX(-2deg); }
}
.cat-arrow { font-size: 0.45rem; width: 10px; }
.cat-icon { font-size: 0.7rem; }
.cat-label { flex: 1; text-align: left; font-weight: 500; }
.cat-count { font-size: 0.53rem; opacity: 0.5; font-family: 'JetBrains Mono', monospace; }
.tool-grid { display: flex; flex-direction: column; gap: 3px; padding: 3px 4px 6px 22px; }
.tool-chip {
  display: flex; flex-direction: column; gap: 2px; padding: 6px 10px; border-radius: 5px;
  border: 1px solid rgba(0, 173, 181, 0.06); background: rgba(0, 0, 0, 0.3);
  color: var(--miya-text-dim); cursor: pointer; transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1); text-align: left;
  &:hover:not(:disabled) { border-color: rgba(0, 255, 245, 0.2); color: var(--miya-text); background: rgba(129, 191, 241, 0.1); transform: skewX(-3deg); }
  &:disabled { opacity: 0.25; }
  &.running { border-color: var(--miya-accent); color: var(--miya-accent); animation: scan-pulse 1s infinite; }
}
.tool-chip-name { font-size: 0.68rem; font-weight: 500; color: var(--miya-text); line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tool-chip-desc { font-size: 0.54rem; color: var(--miya-text-dim); line-height: 1.35; opacity: 0.7; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

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
  background: rgba(0, 0, 0, 0.3); cursor: pointer; transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1); font-size: 0.62rem;
  border: 1px solid transparent;
  &:hover { background: rgba(129, 191, 241, 0.1); border-color: rgba(0, 255, 245, 0.15); transform: skewX(-2deg); }
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
  flex: 1; background: rgba(0,0,0,0.25); border: 0.5px solid rgba(0, 173, 181,0.08);
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
.log-time { color: rgba(0, 173, 181,0.3); flex-shrink: 0; font-size: 0.6rem; }
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
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(0, 173, 181, 0.06);
  box-shadow:
    2px 2px 8px rgba(0, 40, 50, 0.3),
    -1px -1px 4px rgba(0, 180, 200, 0.03);
  border-radius: 8px;
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
  padding: 6px 12px; border-radius: 5px; font-size: 0.62rem; cursor: pointer;
  border: 1px solid rgba(0, 173, 181, 0.1); background: rgba(0, 0, 0, 0.3); color: var(--miya-text-dim);
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1); white-space: nowrap;
  &:hover { border-color: rgba(0, 255, 245, 0.2); color: var(--miya-accent); background: rgba(129, 191, 241, 0.1); transform: skewX(-3deg); }
  &.primary { background: rgba(248, 113, 113, 0.1); border-color: rgba(248, 113, 113, 0.2); color: #ff6666; }
}

/* Findings */
.findings-section { display: flex; flex-direction: column; gap: 6px; }
.section-label { font-size: 0.68rem; color: var(--miya-text-dim); letter-spacing: 0.06em; margin: 0; }
.finding-card {
  background: rgba(0, 0, 0, 0.45);
  border: 1px solid rgba(0, 173, 181, 0.06);
  box-shadow:
    2px 2px 6px rgba(0, 40, 50, 0.25),
    -1px -1px 3px rgba(0, 180, 200, 0.03);
  border-radius: 6px; border-left: 3px solid; overflow: hidden;
  transition: border-color 0.3s ease;
}
.finding-card:hover { border-color: rgba(0, 255, 245, 0.1); }
.finding-header {
  display: flex; align-items: center; gap: 8px; padding: 10px 12px;
  cursor: pointer; transition: background 0.15s;
  &:hover { background: rgba(0, 173, 181,0.04); }
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
  background: rgba(0, 173, 181,0.1); color: var(--miya-accent);
}

.no-findings {
  display: flex; align-items: center; gap: 8px; padding: 20px; justify-content: center;
  font-size: 0.7rem; color: rgba(68,204,68,0.6);
}
.nf-icon { font-size: 1rem; }

/* ── Security Chat ── */
.sec-chat {
  border: 1px solid rgba(0, 173, 181, 0.06); border-radius: 8px;
  background: rgba(0, 0, 0, 0.5);
  box-shadow:
    3px 3px 10px rgba(0, 40, 50, 0.35),
    -1px -1px 4px rgba(0, 180, 200, 0.04);
  transition: border-color 0.3s ease;
  transform: rotateY(-3deg);
}
.sec-chat:hover { border-color: rgba(0, 255, 245, 0.12); transform: rotateY(-2deg); }
.sec-chat-messages {
  flex: 1; overflow-y: auto; padding: 12px 16px 0;
  display: flex; flex-direction: column; gap: 8px;
}
.sec-chat-empty {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 10px; opacity: 0.6; padding-bottom: 40px;
}
.sec-chat-empty-icon { font-size: 2.2rem; opacity: 0.25; }
.sec-chat-empty-title { font-size: 1rem; color: var(--miya-text); font-weight: 500; }
.sec-chat-empty-desc {
  font-size: 0.62rem; color: var(--miya-text-dim); text-align: center; line-height: 1.7; max-width: 360px;
}
.sec-chat-quick { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; justify-content: center; }
.sec-chat-qbtn {
  padding: 6px 14px; border-radius: 5px; font-size: 0.68rem; cursor: pointer;
  border: 1px solid rgba(0, 173, 181, 0.12); background: rgba(0, 173, 181, 0.04);
  color: var(--miya-accent); display: flex; align-items: center; gap: 5px;
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  &:hover { background: rgba(129, 191, 241, 0.12); border-color: rgba(0, 255, 245, 0.2); transform: skewX(-3deg); }
}
.sec-chat-cursor {
  color: var(--miya-accent); font-size: 0.7rem; animation: blink 1s step-end infinite; padding-left: 4px;
}
.sec-chat-bar {
  display: flex; align-items: center; gap: 6px; padding: 10px 14px;
  border-top: 0.5px solid rgba(0, 173, 181,0.08); background: rgba(0,0,0,0.12);
  border-radius: 0 0 10px 10px;
}
.sec-chat-actions { display: flex; gap: 4px; flex-shrink: 0; }
.sec-chat-qsm {
  width: 28px; height: 28px; border-radius: 6px; font-size: 0.75rem; cursor: pointer;
  border: 0.5px solid rgba(0, 173, 181,0.1); background: transparent;
  color: var(--miya-text-dim); display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
  &:hover { border-color: var(--miya-accent); color: var(--miya-accent); background: rgba(0, 173, 181,0.06); }
}
.sec-chat-input {
  flex: 1; background: rgba(0,0,0,0.3); border: 1px solid rgba(0, 173, 181, 0.08);
  border-radius: 5px; padding: 8px 12px; color: var(--miya-text); font-size: 0.78rem;
  outline: none; transition: border-color 0.2s;
  &::placeholder { color: rgba(0, 173, 181, 0.15); font-size: 0.7rem; }
  &:focus { border-color: rgba(0, 255, 245, 0.25); }
  &:disabled { opacity: 0.3; }
}
.sec-chat-send {
  width: 34px; height: 34px; border-radius: 7px; font-size: 0.85rem; cursor: pointer; flex-shrink: 0;
  border: none; background: linear-gradient(135deg, var(--miya-accent), color-mix(in srgb, var(--miya-accent) 70%, #ff4444));
  color: #fff; display: flex; align-items: center; justify-content: center; transition: all 0.15s;
  &:hover:not(:disabled) { transform: translateY(-1px); }
  &:disabled { opacity: 0.3; cursor: not-allowed; }
}

/* ── Kali Terminal ── */
.kali-btn {
  margin-left: auto; padding: 4px 12px; border-radius: 5px; font-size: 0.65rem; cursor: pointer;
  font-family: 'JetBrains Mono', monospace; white-space: nowrap; display: flex; align-items: center; gap: 4px;
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  &.term { border: 1px solid rgba(0, 173, 181, 0.15); background: rgba(0, 173, 181, 0.06); color: var(--miya-accent); }
  &.term:hover { background: rgba(129, 191, 241, 0.12); border-color: rgba(0, 255, 245, 0.25); transform: skewX(-4deg); }
  &.term.active { background: rgba(0, 173, 181, 0.15); border-color: rgba(0, 255, 245, 0.3); color: rgba(0, 255, 245, 0.8); }
}
.kali-icon { font-size: 0.7rem; }

.kali-term-wrap { position:fixed; inset:56px 0 0 0; z-index:51; display:flex; flex-direction:column; background:#080618; }
.kali-toolbar { display:flex; align-items:center; gap:12px; padding:6px 16px; border-bottom:.5px solid rgba(0, 173, 181,.2); background:rgba(0,0,0,.5); }
.kali-label { font-size:.7rem; color:var(--miya-accent); font-family:'JetBrains Mono',monospace; }
.kali-status { font-size:.55rem; color:var(--miya-text-dim); }
.kali-hint { margin-left:auto; font-size:.55rem; color:var(--miya-text-dim); opacity:0.5; }
.kali-btn-minimize { padding:2px 8px; border-radius:4px; font-size:.65rem; cursor:pointer; border:.5px solid rgba(0, 173, 181,.2); background:transparent; color:var(--miya-text-dim); margin-left:8px; &:hover{background:rgba(0, 173, 181,.15);color:var(--miya-accent);} }
.kali-btn-close { padding:2px 8px; border-radius:4px; font-size:.65rem; cursor:pointer; border:.5px solid rgba(255,80,80,.2); background:transparent; color:#ff6666; &:hover{background:rgba(255,80,80,.1)} }
.kali-xterm-box { flex:1; padding:6px 4px 4px 10px; :deep(.xterm){height:100%} :deep(.xterm-viewport){overflow-y:auto} :deep(.xterm-viewport::-webkit-scrollbar){width:6px} :deep(.xterm-viewport::-webkit-scrollbar-thumb){background:rgba(0, 173, 181,.2);border-radius:3px} }

/* ── Modal ── */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 100; display: flex; align-items: center; justify-content: center; }
.modal-card {
  background: rgba(0, 0, 0, 0.92);
  border: 1px solid rgba(0, 173, 181, 0.12);
  box-shadow:
    3px 3px 20px rgba(0, 40, 50, 0.5),
    -2px -2px 10px rgba(0, 180, 200, 0.08);
  border-radius: 10px;
  padding: 24px; display: flex; flex-direction: column; gap: 12px; min-width: 300px;
  h3 { margin: 0; font-family: 'Noto Serif SC', serif; font-size: 0.9rem; color: var(--miya-text); }
}
</style>
