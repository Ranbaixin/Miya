import type { StreamChunk } from '@/utils/encoding'
import { aiter } from 'iterator-helper'
import { decodeStreamChunk, readerToMessageStream } from '@/utils/encoding'
import { ApiClient } from './index'

export interface MemoryStats {
  nodeCount: number
  edgeCount: number
  memorySize?: string
}

export interface EmotionState {
  dominant: string
  intensity: number
  emotions: Array<{ name: string, intensity: number }>
  inner_thought?: string
}

export interface SessionInfo {
  id: string
  name: string
  created_at?: string
  updated_at?: string
  message_count?: number
}

export class CoreApiClient extends ApiClient {
  // ── 系统 ──
  async health(): Promise<{ status: string }> {
    return this.instance.get('/health')
  }

  async systemStatus(): Promise<any> {
    return this.instance.get('/api/status')
  }

  // ── 对话 ──
  async chatSend(data: {
    message: string
    session_id?: string
    platform?: string
    user_id?: string
    usg_id?: string
  }): Promise<any> {
    return this.instance.post('/api/chat/send', data, {
      transformResponse: [(d: string) => d],  // 跳过 axios JSON 解析
    }).then((raw: string) => {
      try { return JSON.parse(raw) } catch { return raw }
    })
  }

  async listSessions(): Promise<SessionInfo[]> {
    const res: any = await this.instance.get('/api/chat/sessions')
    // 2026-09 修复：后端返回 {success, data:[...]}，调用方期望 res.sessions
    return { sessions: res?.data ?? res?.sessions ?? [] } as any
  }

  async getSession(sessionId: string): Promise<any> {
    const res: any = await this.instance.get(`/api/chat/get_session?session_id=${sessionId}`)
    // 2026-09 修复：后端返回 {data:{history}}，调用方期望 detail.messages
    const history = res?.data?.history ?? res?.data?.messages ?? res?.messages ?? []
    return { ...res, messages: history }
  }

  async deleteSession(sessionId: string): Promise<void> {
    return this.instance.get(`/api/chat/delete_session?session_id=${sessionId}`)
  }

  async updateSessionName(sessionId: string, name: string): Promise<void> {
    return this.instance.post('/api/chat/update_session_display_name', {
      session_id: sessionId,
      display_name: name,
    })
  }

  // ── 记忆 ──
  async getMemoryStats(): Promise<MemoryStats> {
    const res: any = await this.instance.get('/api/memory/stats')
    // 2026-09 修复：后端无 nodeCount/edgeCount 字段，包装层归一化
    return {
      nodeCount: Number(res?.nodeCount ?? res?.total ?? 0),
      edgeCount: Number(res?.edgeCount ?? 0),
      memorySize: res?.memorySize ?? res?.memory_size,
    }
  }

  async getMemoryList(limit?: number): Promise<any[]> {
    const res: any = await this.instance.get(`/api/memory/list${limit ? `?limit=${limit}` : ''}`)
    return res?.data?.items ?? res?.items ?? (Array.isArray(res) ? res : [])
  }

  async searchMemory(query: string, limit?: number): Promise<any[]> {
    const res: any = await this.instance.get(`/api/memory/search?query=${encodeURIComponent(query)}${limit ? `&limit=${limit}` : ''}`)
    return res?.memories ?? (Array.isArray(res) ? res : [])
  }

  // ── 人格 ──
  async getPersonaList(): Promise<any[]> {
    const res: any = await this.instance.get('/api/persona/list')
    return res?.personas ?? (Array.isArray(res) ? res : [])
  }

  async getCurrentPersona(): Promise<any> {
    return this.instance.get('/api/persona/current')
  }

  async switchPersona(personaId: string): Promise<void> {
    return this.instance.post('/api/persona/switch', { persona_id: personaId })
  }

  // ── 知识图谱 (记忆可视化) ──
  async getQuintuples(filter?: string): Promise<any> {
    const res = await this.instance.get('/api/plug/alkaid/ltm/graph')
    return res?.data || res || { nodes: [], edges: [] }
  }

  async addMemoryEntry(data: { subject: string, predicate: string, obj: string }): Promise<any> {
    return this.instance.post('/api/memory/add', {
      subject: data.subject,
      predicate: data.predicate,
      object: data.obj,
      type: 'memory',
    })
  }

  // ── 配置 ──
  async getConfig(): Promise<any> {
    return this.instance.get('/api/config/get')
  }

  // ── 插件 / 工具 ──
  async getPluginList(): Promise<any[]> {
    const res: any = await this.instance.get('/api/plugin/market_list')
    return res?.data ?? (Array.isArray(res) ? res : [])
  }

  async getToolsList(): Promise<any[]> {
    const res: any = await this.instance.get('/api/tools/list')
    return res?.tools ?? (Array.isArray(res) ? res : [])
  }

  // ── MCP 工具调用 ──
  async mcpCall(service: string, tool: string, params: Record<string, any> = {}): Promise<any> {
    return this.instance.post('/api/mcp/call', { service, tool, ...params }, {
      transformRequest: [(d: any) => JSON.stringify(d)],
      transformResponse: [(d: string) => {
        try { return JSON.parse(d) } catch { return d }
      }],
    })
  }

  // ── OpenClaw ──
  async openclawStatus(): Promise<any> {
    return this.mcpCall('openclaw', 'get_status')
  }

  async openclawSend(message: string, opts: Record<string, any> = {}): Promise<any> {
    return this.mcpCall('openclaw', 'send_message', { message, ...opts })
  }

  async openclawStart(): Promise<any> {
    return this.mcpCall('openclaw', 'start_gateway')
  }

  async openclawStop(): Promise<any> {
    return this.mcpCall('openclaw', 'stop_gateway')
  }

  async openclawHistory(sessionKey: string, limit: number = 20): Promise<any> {
    return this.mcpCall('openclaw', 'get_history', { session_key: sessionKey, limit })
  }

  // ── 会话（别名） ──
  async getSessions(): Promise<SessionInfo[]> { return this.listSessions() }

  // ── 文件 ──
  async parseDocument(file: File): Promise<any> {
    const fd = new FormData(); fd.append('file', file)
    return this.instance.post('/api/desktop/files/parse', fd)
  }
  async uploadDocument(file: File): Promise<any> {
    const fd = new FormData(); fd.append('file', file)
    return this.instance.post('/api/desktop/files/upload', fd)
  }

  // ── 音频 ──
  async transcribeAudio(blob: Blob, _opts?: any): Promise<any> {
    const fd = new FormData(); fd.append('audio', blob, 'recording.webm')
    return this.instance.post('/api/audio/transcribe', fd)
  }

  // ── 系统信息 ──
  async systemInfo(): Promise<any> { return this.instance.get('/api/status') }
  async getToolStatus(): Promise<any> { return this.instance.get('/api/tools/list') }
  async getOpenclawTasks(): Promise<any> { return this.openclawHistory('default') }

  // ── Agent 健康检查 ──
  async agentServerHealth(): Promise<any> { return this.health() }
  async agentServerFullHealth(): Promise<any> { return this.instance.get('/api/status') }
  async agentServerOpenclawHealth(): Promise<any> { return this.openclawStatus() }

  // ── 系统 Prompt ──
  async getSystemPrompt(): Promise<any> { return this.instance.get('/api/config/system_prompt') }
  async setSystemPrompt(content: string): Promise<any> {
    return this.instance.post('/api/config/system_prompt', { content })
  }
  async setSystemConfig(payload: Record<string, any>): Promise<any> {
    return this.instance.post('/api/config/set', payload)
  }
}

// 2026-09 修复：业务路由（chat/memory/persona/config 等）在 Web API(8000)，
// 此前硬编码 9800(管理API) 导致 30+ 调用 404；可用 VITE_CORE_PORT 覆盖
export default new CoreApiClient(Number(import.meta.env.VITE_CORE_PORT) || 8000)
