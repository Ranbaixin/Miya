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

  async chatStream(data: {
    message: string
    session_id?: string
    platform?: string
    user_id?: string
  }): Promise<AsyncIterableIterator<StreamChunk>> {
    return this.instance.post('/api/chat', data, {
      responseType: 'stream',
      timeout: 0,
      headers: { Accept: 'text/event-stream' },
    }).then(res => {
      const reader = res.data?.getReader?.()
      return reader
        ? aiter(decodeStreamChunk(readerToMessageStream(reader)))
        : aiter<StreamChunk>([])
    })
  }

  async chatStop(): Promise<void> {
    return this.instance.post('/api/chat/stop')
  }

  async listSessions(): Promise<SessionInfo[]> {
    return this.instance.get('/api/chat/sessions')
  }

  async getSession(sessionId: string): Promise<any> {
    return this.instance.get(`/api/chat/get_session?session_id=${sessionId}`)
  }

  async newSession(): Promise<{ id: string }> {
    return this.instance.get('/api/chat/new_session')
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
    return this.instance.get('/api/memory/stats')
  }

  async getMemoryList(limit?: number): Promise<any[]> {
    return this.instance.get(`/api/memory/list${limit ? `?limit=${limit}` : ''}`)
  }

  async searchMemory(query: string, limit?: number): Promise<any[]> {
    return this.instance.get(`/api/memory/search?query=${query}${limit ? `&limit=${limit}` : ''}`)
  }

  // ── 人格 ──
  async getPersonaList(): Promise<any[]> {
    return this.instance.get('/api/persona/list')
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

  async searchQuintuples(query: string): Promise<any> {
    const res = await this.instance.get(`/api/plug/alkaid/ltm/graph/search?query=${encodeURIComponent(query)}`)
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
    return this.instance.get('/api/plugin/market_list')
  }

  async getToolsList(): Promise<any[]> {
    return this.instance.get('/api/tools/list')
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
}

export default new CoreApiClient(8000)
