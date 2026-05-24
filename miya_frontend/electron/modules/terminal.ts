import { type IPty, spawn } from '@lydell/node-pty'
import { resolve } from 'node:path'
import { readFileSync, existsSync } from 'node:fs'
import { execSync } from 'node:child_process'

function findNodeExe(): string {
  try {
    const result = execSync('where node', { timeout: 5000, encoding: 'utf-8' })
    const paths = result.trim().split('\r\n')
    for (const p of paths) {
      if (existsSync(p)) return p
    }
  }
  catch { /* fall through */ }

  const fallbacks = [
    'D:\\node.exe',
    'C:\\Program Files\\nodejs\\node.exe',
    process.env.NODE_EXE,
    process.env.NODE,
  ]

  for (const fb of fallbacks) {
    if (fb && existsSync(fb)) return fb
  }

  return 'node'
}

const NODE_EXE = findNodeExe()

function loadEnvVars(rootDir: string): Record<string, string> {
  const env: Record<string, string> = {}

  const candidates = [
    resolve(rootDir, 'config', '.env'),
    resolve(rootDir, 'resources', 'backend', '_internal', 'config', '.env'),
  ]

  const envPath = candidates.find(p => existsSync(p))
  if (envPath) {
    const content = readFileSync(envPath, 'utf-8')
    for (const line of content.split('\n')) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#')) continue
      const eqIdx = trimmed.indexOf('=')
      if (eqIdx === -1) continue
      const key = trimmed.slice(0, eqIdx).trim()
      const value = trimmed.slice(eqIdx + 1).trim()
      if (key && value) env[key] = value
    }
  }
  return env
}

let ptyProcess: IPty | null = null
let miyaRoot = ''
let terminalBuffer = ''

export function setMiyaRoot(root: string): void {
  miyaRoot = root
}

function buildEnv(rootDir: string, model?: string): Record<string, string> {
  const dotEnv = loadEnvVars(rootDir)
  const apiKey = dotEnv.DEEPSEEK_API_KEY || process.env.DEEPSEEK_API_KEY || ''
  const baseUrl = dotEnv.DEEPSEEK_API_BASE || 'https://api.deepseek.com/v1'
  const selectedModel = model || dotEnv.DEEPSEEK_MODEL || 'deepseek-v4-flash'

  return {
    ...process.env,
    CLAUDE_CODE_USE_OPENAI: '1',
    OPENAI_API_KEY: apiKey,
    OPENAI_BASE_URL: baseUrl,
    OPENAI_MODEL: selectedModel,
    FORCE_COLOR: '1',
    TERM: 'xterm-256color',
  } as Record<string, string>
}

export function startTerminal(
  options: { model?: string } = {},
  onData: (data: string) => void,
  onExit: (code: number) => void,
): void {
  if (ptyProcess) {
    stopTerminal()
  }

  const rootDir = miyaRoot || process.cwd()
  const env = buildEnv(rootDir, options.model)

  const cliCandidates = [
    resolve(rootDir, 'claude-code-engine', 'cli-node.js'),
    resolve(rootDir, 'claude-code-engine', 'dist', 'cli-node.js'),
    resolve(process.resourcesPath || '', 'claude-code-engine', 'cli-node.js'),
    resolve(process.resourcesPath || '', 'claude-code-engine', 'dist', 'cli-node.js'),
  ]

  const cliPath = cliCandidates.find(p => existsSync(p))

  if (!cliPath) {
    throw new Error(`Claude Code Engine not found. Checked: ${cliCandidates.filter(p => p).join(', ')}`)
  }

  if (!existsSync(NODE_EXE)) {
    throw new Error(`Node.js not found. Searched PATH and common locations. Try installing Node.js.`)
  }

  ptyProcess = spawn(NODE_EXE, [cliPath], {
    name: 'xterm-256color',
    cwd: rootDir,
    env,
    cols: 120,
    rows: 40,
  })

  terminalBuffer = ''

  ptyProcess.onData((data: string) => {
    terminalBuffer += data
    onData(data)
  })

  ptyProcess.onExit(({ exitCode }) => {
    onExit(exitCode)
    ptyProcess = null
  })
}

export function writeToTerminal(data: string): void {
  if (ptyProcess) {
    ptyProcess.write(data)
  }
}

export function resizeTerminal(cols: number, rows: number): void {
  if (ptyProcess) {
    ptyProcess.resize(cols, rows)
  }
}

export function stopTerminal(): void {
  if (ptyProcess) {
    ptyProcess.kill()
    ptyProcess = null
    terminalBuffer = ''
  }
}

export function isTerminalRunning(): boolean {
  return ptyProcess !== null
}

export function getTerminalBuffer(): string {
  return terminalBuffer
}
