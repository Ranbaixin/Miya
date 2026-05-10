import type { Buffer } from 'node:buffer'
import type { ChildProcess } from 'node:child_process'
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { app } from 'electron'
import { getMainWindow } from './window'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

let backendProcess: ChildProcess | null = null
const BACKEND_LOG_MAX_LINES = 1200
const backendLogLines: string[] = []

function appendBackendLog(line: string, stream: 'stdout' | 'stderr' | 'system' = 'system') {
  const normalized = line.replace(/\r/g, '').trimEnd()
  if (!normalized.trim())
    return

  const entry = stream === 'system' ? normalized : `[${stream}] ${normalized}`
  backendLogLines.push(entry)
  if (backendLogLines.length > BACKEND_LOG_MAX_LINES) {
    backendLogLines.splice(0, backendLogLines.length - BACKEND_LOG_MAX_LINES)
  }

  try {
    getMainWindow()?.webContents.send('backend:log', { line: entry })
  }
  catch {
    // ignore renderer delivery failures
  }
}

function createChunkForwarder(
  stream: 'stdout' | 'stderr',
  onLine: (line: string) => boolean | void,
) {
  let carry = ''

  return (text: string) => {
    const normalized = `${carry}${text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')}`
    const parts = normalized.split('\n')
    carry = parts.pop() ?? ''
    for (const part of parts) {
      const line = part.trimEnd()
      if (!line.trim())
        continue
      const shouldMirror = onLine(line)
      if (shouldMirror !== false) {
        appendBackendLog(line, stream)
      }
    }
  }
}

export function getBackendLogs(): string {
  return backendLogLines.join('\n')
}

function quoteWindowsArg(arg: string): string {
  if (arg.length === 0) {
    return '""'
  }
  if (!/[\s"]/u.test(arg)) {
    return arg
  }
  return `"${arg.replaceAll('"', '""')}"`
}

function resolveVenvPython(cwd: string): string {
  return process.platform === 'win32'
    ? join(cwd, '.venv', 'Scripts', 'python.exe')
    : join(cwd, '.venv', 'bin', 'python')
}

export function startBackend(): void {
  let cmd: string
  let args: string[]
  let cwd: string

  if (app.isPackaged) {
    // 打包模式：spawn PyInstaller 编译的二进制
    const backendDir = join(process.resourcesPath, 'backend')
    const ext = process.platform === 'win32' ? '.exe' : ''
    cmd = join(backendDir, `miya-backend${ext}`)
    args = []
    cwd = backendDir
  }
  else {
    // 开发模式：尝试 venv Python → 系统 Python → 跳过
    cwd = join(__dirname, '..', '..')
    let pythonPath = resolveVenvPython(cwd)
    if (!existsSync(pythonPath)) {
      // 尝试系统全局 Python 3.11
      const sysPython = process.platform === 'win32'
        ? 'D:/Python/python3.11.9/python.exe'
        : 'python3'
      if (existsSync(sysPython)) {
        pythonPath = sysPython
        console.log('[Backend] 使用系统 Python:', sysPython)
      }
      else {
        console.warn('[Backend] 未找到 Python 解释器，跳过后端启动')
        appendBackendLog('[Backend] Python not found, skipping backend start')
        return
      }
    }
    cmd = pythonPath
    args = ['run/miya_demo.py']
  }

  console.log(`[Backend] Starting from ${cwd}`)
  console.log(`[Backend] Command: ${cmd} ${args.join(' ')}`)
  appendBackendLog(`[Backend] Starting from ${cwd}`)
  appendBackendLog(`[Backend] Command: ${cmd} ${args.join(' ')}`)

  const env: Record<string, string | undefined> = { ...process.env, PYTHONUNBUFFERED: '1' }

  // Collect all output for error reporting
  const outputLines: string[] = []
  const PROGRESS_PREFIX = '##PROGRESS##'
  const consumeStdoutChunk = createChunkForwarder('stdout', (trimmed) => {
    outputLines.push(trimmed)

    if (trimmed.startsWith(PROGRESS_PREFIX)) {
      try {
        const payload = JSON.parse(trimmed.slice(PROGRESS_PREFIX.length))
        getMainWindow()?.webContents.send('backend:progress', payload)
      }
      catch {
        // malformed progress line, ignore
      }
      return false
    }
    return true
  })
  const consumeStderrChunk = createChunkForwarder('stderr', (trimmed) => {
    outputLines.push(trimmed)
    return true
  })

  backendProcess = spawn(cmd, args, {
    cwd,
    stdio: ['ignore', 'pipe', 'pipe'],
    env,
    // 创建独立进程组，关闭时用 process.kill(-pid) 杀掉所有子进程
    detached: process.platform !== 'win32',
  })

  backendProcess.stdout?.on('data', (data: Buffer) => {
    const text = data.toString()
    consumeStdoutChunk(text)
    console.log(`[Backend] ${text.trimEnd()}`)
  })

  backendProcess.stderr?.on('data', (data: Buffer) => {
    const text = data.toString()
    console.error(`[Backend] ${text.trimEnd()}`)
    consumeStderrChunk(text)
  })

  backendProcess.on('error', (err) => {
    console.error(`[Backend] Failed to start: ${err.message}`)
    appendBackendLog(`[Backend] Failed to start: ${err.message}`)
  })

  backendProcess.on('exit', (code) => {
    console.log(`[Backend] Exited with code ${code}`)
    appendBackendLog(`[Backend] Exited with code ${code}`)
    backendProcess = null

    // Notify renderer of backend crash (non-zero exit, not a manual stop)
    if (code !== null && code !== 0) {
      const logs = outputLines.slice(-200).join('\n')
      getMainWindow()?.webContents.send('backend:error', { code, logs })
    }
  })
}

export function stopBackend(): void {
  if (!backendProcess)
    return
  const pid = backendProcess.pid
  console.log('[Backend] Stopping...')
  appendBackendLog('[Backend] Stopping...')

  if (!pid) {
    backendProcess = null
    return
  }

  if (process.platform === 'win32') {
    // /T 连同子进程树一起终止
    spawn('taskkill', ['/pid', String(pid), '/f', '/t'])
  }
  else {
    // 杀整个进程组（负 PID），确保 uvicorn workers 等子进程一起退出
    try {
      process.kill(-pid, 'SIGTERM')
    }
    catch {
      // 进程组不存在，回退杀单个进程
      try {
        process.kill(pid, 'SIGTERM')
      }
      catch {
        /* already dead */
      }
    }
    // 保险：200ms 后 SIGKILL 整个进程组
    setTimeout(() => {
      try {
        process.kill(-pid, 'SIGKILL')
      }
      catch {
        try {
          process.kill(pid, 'SIGKILL')
        }
        catch {
          /* already dead */
        }
      }
    }, 200)
  }

  backendProcess = null
}
