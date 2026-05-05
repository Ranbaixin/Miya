import { useState, useEffect, useCallback } from 'react';

const API_PORTS = [8000, 8001, 8002, 8003, 8004, 8005];
let cachedApiBase: string | null = null;
const API_KEY = 'changeme';

async function findAvailableApiPort(): Promise<string> {
  if (cachedApiBase) return cachedApiBase;

  for (const port of API_PORTS) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1000);

      const res = await fetch(`http://localhost:${port}/api/health`, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        cachedApiBase = `http://localhost:${port}`;
        console.log(`[MiyaAPI] 找到可用 API 端口: ${port}`);
        return cachedApiBase;
      }
    } catch {
      continue;
    }
  }
  return 'http://localhost:8000';
}

function getAuthHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-Undefined-API-Key': API_KEY,
  };
}

export interface EmotionState {
  dominant_emotion: string;
  intensity: number;
  emotion_tags: string[];
  reasoning: string;
  inner_thought: string;
  attribution: string;
}

export interface IdentityData {
  uuid: string;
  name: string;
  version: string;
  birth_time: string;
  awake_time: string;
  awake_duration: number;
  god_attributes: Record<string, string>;
  capabilities: string[];
  limitations: string[];
}

export interface MemoryStats {
  total: number;
  important: number;
  emotion: number;
  conversation: number;
}

export interface MemoryItem {
  uuid: string;
  fact: string;
  created_at: string;
}

export interface ToolDefinition {
  function: {
    name: string;
    description: string;
    parameters?: {
      type: string;
      properties: Record<string, any>;
      required?: string[];
    };
  };
}

export interface ToolInfo {
  name: string;
  description: string;
  category: string;
}

export interface ModelInfo {
  name: string;
  provider: string;
  status: 'active' | 'idle' | 'error';
  tokens: number;
}

export interface SystemInfo {
  cpu_model: string;
  cpu_usage_percent: number;
  memory_total_gb: number;
  memory_used_gb: number;
  memory_usage_percent: number;
  system_version: string;
  system_arch: string;
  python_version: string;
  undefined_version: string;
}

export interface RuntimeMeta {
  enabled: boolean;
  host: string;
  port: number;
  openapi_enabled: boolean;
}

export interface VectorData {
  name: string;
  value: number;
  min: number;
  max: number;
}

export interface ChatMessage {
  id: string;
  sender: string;
  content: string;
  time: string;
  type: 'user' | 'miya';
  timestamp?: Date;
}

export interface CognitiveProfile {
  entity_type: string;
  entity_id: string;
  document: string;
  metadata: Record<string, any>;
  id?: string;
  score?: number;
}

export interface CognitiveEvent {
  id: string;
  document: string;
  score: number;
  metadata: Record<string, any>;
}

// ============================================================
// 平台相关类型
// ============================================================

export interface PlatformInfo {
  platform_id: string;
  name: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error' | 'unknown';
  config: Record<string, any>;
  description?: string;
  icon?: string;
}

export interface PlatformStats {
  total: number;
  enabled_count: number;
  connected_count: number;
  platforms: PlatformInfo[];
}

export interface PlatformMetadata {
  platform_id: string;
  name: string;
  description: string;
  config_fields: ConfigField[];
  tutorial_url?: string;
  icon?: string;
}

export interface ConfigField {
  field: string;
  label: string;
  type: 'string' | 'number' | 'boolean' | 'password' | 'select';
  required: boolean;
  options?: { value: string; label: string }[];
  placeholder?: string;
  description?: string;
}

// ============================================================
// 插件/MCP 相关类型
// ============================================================

export interface PluginInfo {
  name: string;
  description: string;
  author: string;
  version: string;
  enabled: boolean;
  category?: string;
  icon_url?: string;
  download_url?: string;
  installed_at?: string;
  config?: Record<string, any>;
}

export interface MCPServerInfo {
  name: string;
  enabled: boolean;
  status: 'running' | 'stopped' | 'error';
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  tools?: string[];
}

export interface MCPListResponse {
  mcpServers: Record<string, MCPServerConfig>;
}

export interface MCPServerConfig {
  command: string;
  args?: string[];
  env?: Record<string, string>;
  disabled?: boolean;
}

// ============================================================
// 知识库相关类�?// ============================================================

export interface KnowledgeBaseInfo {
  id: string;
  name: string;
  description: string;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeBaseDoc {
  id: string;
  title: string;
  content_preview: string;
  created_at: string;
  updated_at: string;
}

// ============================================================

class MiyaAPI {
  private baseUrl: string;
  private listeners: Map<string, Set<Function>> = new Map();
  private initialized: boolean = false;

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl;
  }

  private async _ensureBaseUrl() {
    if (!this.initialized) {
      this.baseUrl = await findAvailableApiPort();
      this.initialized = true;
    }
  }

  private async _request<T = any>(path: string, options?: RequestInit): Promise<T | null> {
    await this._ensureBaseUrl();
    try {
      const res = await fetch(`${this.baseUrl}${path}`, {
        ...options,
        headers: {
          ...getAuthHeaders(),
          ...options?.headers,
        },
      });
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      console.error(`API请求失败: ${path}`, e);
      return null;
    }
  }

  async healthCheck(): Promise<boolean> {
    await this._ensureBaseUrl();
    try {
      const res = await fetch(`${this.baseUrl}/api/health`);
      return res.ok;
    } catch {
      return false;
    }
  }

  // ============================================================
  // 运行�?API
  // ============================================================

  async getRuntimeMeta(): Promise<RuntimeMeta | null> {
    return this._request<RuntimeMeta>('/api/status');
  }

  async getSystemInfo(): Promise<SystemInfo | null> {
    return this._request<SystemInfo>('/api/status');
  }

  async getRuntimeChatHistory(params?: { limit?: number; before?: string }) {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.before) query.set('before', params.before);
    const queryStr = query.toString() ? `?${query.toString()}` : '';
    return this._request(`/api/v1/management/runtime/chat/history${queryStr}`);
  }

  async sendChat(message: string, stream: boolean = false) {
    return this._request('/api/v1/management/runtime/chat', {
      method: 'POST',
      body: JSON.stringify({ message, stream }),
    });
  }

  async getChatSessions(): Promise<{ success: boolean; data: any[] } | null> {
    return this._request('/api/chat/sessions');
  }

  async getTools(): Promise<{ tools: ToolDefinition[] } | null> {
    const res = await this._request<any>('/api/tools');
    if (!res) return { tools: [] };
    return {
      tools: res.tools || [],
    };
  }

  async invokeTool(toolName: string, args: Record<string, any> = {}) {
    return this._request('/api/tools/invoke', {
      method: 'POST',
      body: JSON.stringify({ name: toolName, args }),
    });
  }

  // ============================================================
  // 记忆 API
  // ============================================================

  async getMemory(params?: { limit?: number; offset?: number; query?: string }) {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    if (params?.query) query.set('query', params.query);
    const queryStr = query.toString() ? `?${query.toString()}` : '';
    return this._request(`/api/memory/list${queryStr}`);
  }

  async addMemory(fact: string) {
    return this._request('/api/memory/add', {
      method: 'POST',
      body: JSON.stringify({ text: fact }),
    });
  }

  async getMemoryStats() {
    return this._request('/api/memory/stats');
  }

  async deleteMemory(memoryUuid: string) {
    return this.invokeTool('memory_delete', { memory_uuid: memoryUuid });
  }

  async getMemes() {
    return this._request('/api/v1/memes');
  }

  async getMemeStats() {
    return this._request('/api/v1/memes/stats');
  }

  async getMemeDetail(uid: string) {
    return this._request(`/api/v1/memes/${uid}`);
  }

  // ============================================================
  // 认知 API
  // ============================================================

  async getCognitiveProfiles(params?: { entity_type?: string; limit?: number }) {
    const query = new URLSearchParams();
    if (params?.entity_type) query.set('entity_type', params.entity_type);
    if (params?.limit) query.set('limit', String(params.limit));
    const queryStr = query.toString() ? `?${query.toString()}` : '';
    return this._request(`/api/cognitive/profiles${queryStr}`);
  }

  async getCognitiveProfile(entityType: string, entityId: string) {
    return this._request(`/api/cognitive/profiles/${entityType}/${entityId}`);
  }

  async getCognitiveEvents(params?: {
    query?: string;
    entity_type?: string;
    entity_id?: string;
    limit?: number;
    time_from?: string;
    time_to?: string;
  }) {
    const query = new URLSearchParams();
    if (params?.query) query.set('query', params.query);
    if (params?.entity_type) query.set('entity_type', params.entity_type);
    if (params?.entity_id) query.set('entity_id', params.entity_id);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.time_from) query.set('time_from', params.time_from);
    if (params?.time_to) query.set('time_to', params.time_to);
    const queryStr = query.toString() ? `?${query.toString()}` : '';
    return this._request(`/api/v1/management/runtime/cognitive/events${queryStr}`);
  }

  // ============================================================
  // 平台 API �?  // ============================================================

  async getPlatformList(): Promise<PlatformStats | null> {
    const res = await this._request<any>('/api/platform/stats');
    if (!res) return null;
    const mapped = (res.platforms || []).map((p: any) => ({
      platform_id: p.id,
      name: p.name,
      enabled: p.enable,
      status: p.status === 'running' ? 'connected' : p.status === 'stopped' ? 'disconnected' : 'unknown',
      config: {},
    }));
    return {
      total: res.total || 0,
      enabled_count: mapped.filter((p: PlatformInfo) => p.enabled)?.length || 0,
      connected_count: mapped.filter((p: PlatformInfo) => p.status === 'connected')?.length || 0,
      platforms: mapped,
    };
  }

  async getPlatformStats(): Promise<PlatformStats | null> {
    return this.getPlatformList();
  }

  async getPlatformConfig(): Promise<{ config: any; metadata: any } | null> {
    return this._request('/api/platform/config');
  }

  async updatePlatformConfig(platformId: string, config: Record<string, any>) {
    return this._request(`/api/platform/config`, {
      method: 'POST',
      body: JSON.stringify({
        platform_id: platformId,
        config,
      }),
    });
  }

  async connectPlatform(platformId: string) {
    return this._request(`/api/platform/connect`, {
      method: 'POST',
      body: JSON.stringify({ platform_id: platformId }),
    });
  }

  async disconnectPlatform(platformId: string) {
    return this._request(`/api/platform/disconnect`, {
      method: 'POST',
      body: JSON.stringify({ platform_id: platformId }),
    });
  }

  // ============================================================
  // 插件市场 API �?  // ============================================================

  async getPluginMarketList(): Promise<{ total: number; data: PluginInfo[] } | null> {
    const res = await this._request<any>('/api/plugin/market_list');
    if (!res) return null;
    return {
      total: res.total || 0,
      data: res.data || [],
    };
  }

  async searchPluginMarket(query: string): Promise<{ total: number; data: PluginInfo[] } | null> {
    const res = await this._request<any>(`/api/plugin/market_list?query=${encodeURIComponent(query)}`);
    if (!res) return null;
    return {
      total: res.total || 0,
      data: res.data || [],
    };
  }

  // ============================================================
  // 插件管理 API �?  // ============================================================

  async getInstalledPlugins(): Promise<{ total: number; data: PluginInfo[] } | null> {
    const res = await this._request<any>('/api/plugin/get');
    if (!res) return null;
    return {
      total: res.total || 0,
      data: res.data || [],
    };
  }

  async installPlugin(name: string): Promise<{ success: boolean; message: string } | null> {
    return this._request('/api/plugin/install', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  async uninstallPlugin(name: string): Promise<{ success: boolean; message: string } | null> {
    return this._request('/api/plugin/uninstall', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  async enablePlugin(name: string): Promise<{ success: boolean; message: string } | null> {
    return this._request('/api/plugin/on', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  async disablePlugin(name: string): Promise<{ success: boolean; message: string } | null> {
    return this._request('/api/plugin/off', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  async reloadPlugins(): Promise<{ success: boolean; message: string } | null> {
    return this._request('/api/plugin/reload', {
      method: 'POST',
    });
  }

  // ============================================================
  // MCP 服务 API 
  // ============================================================

  async getMCPServers(): Promise<MCPListResponse | null> {
    const res = await this._request<any>('/api/mcp/list');
    if (!res) return null;
    return res;
  }

  async getMCPServerList(): Promise<{ servers: MCPServerInfo[] } | null> {
    const res = await this._request<any>('/api/tools/mcp/servers');
    if (!res) return null;
    return res;
  }

  // ============================================================
  // 语音 API 
  // ============================================================

  async getVoiceConfig(): Promise<any | null> {
    return this._request('/api/voice/config');
  }

  async saveVoiceConfig(config: Record<string, any>): Promise<{ success: boolean } | null> {
    return this._request('/api/voice/config', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async testVoice(): Promise<{ success: boolean; audio_url?: string } | null> {
    return this._request('/api/voice/test', {
      method: 'POST',
    });
  }

  // ============================================================
  // 自主决策 API 
  // ============================================================

  async getAutonomySettings(): Promise<any | null> {
    return this._request('/api/autonomy/settings');
  }

  async saveAutonomySettings(settings: Record<string, any>): Promise<{ success: boolean } | null> {
    return this._request('/api/autonomy/settings', {
      method: 'POST',
      body: JSON.stringify(settings),
    });
  }

  async getAutonomyLogs(): Promise<any | null> {
    return this._request('/api/autonomy/logs');
  }

  async getAutonomyStats(): Promise<any | null> {
    return this._request('/api/autonomy/stats');
  }

  // ============================================================
  // 知识 API
  // ============================================================

  async getKnowledgeBases(): Promise<KnowledgeBaseInfo[] | null> {
    const res = await this._request<any>('/api/knowledge_base/list');
    if (!res) return null;
    return res.data || [];
  }

  async createKnowledgeBase(name: string, description?: string): Promise<KnowledgeBaseInfo | null> {
    return this._request('/api/knowledge_base/create', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    });
  }

  async queryKnowledgeBase(kbId: string, query: string): Promise<any | null> {
    return this._request(`/api/knowledge_base/query`, {
      method: 'POST',
      body: JSON.stringify({ kb_id: kbId, query }),
    });
  }

  // ============================================================
  // 灵魂/情绪 API
  // ============================================================

  async getSoulState(): Promise<EmotionState | null> {
    return this._request<EmotionState>('/api/emotion');
  }

  async getEmotionPool(): Promise<any | null> {
    return this._request('/api/emotion');
  }

  async getEmotionHistory(params?: { limit?: number; time_from?: string; time_to?: string }) {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.time_from) query.set('time_from', params.time_from);
    if (params?.time_to) query.set('time_to', params.time_to);
    const queryStr = query.toString() ? `?${query.toString()}` : '';
    return this._request(`/api/emotion/history${queryStr}`);
  }

  // ============================================================
  // 人格向量 API
  // ============================================================

  async getPersonalityVectors(): Promise<{ vectors: VectorData[] } | null> {
    return this._request<{ vectors: VectorData[] }>('/api/v1/personality/vectors');
  }

  async getPersonalityForms(): Promise<string[] | null> {
    return this._request<string[]>('/api/v1/personality/forms');
  }

  async setPersonalityForm(form: string): Promise<{ success: boolean } | null> {
    return this._request('/api/v1/personality/forms', {
      method: 'POST',
      body: JSON.stringify({ form }),
    });
  }

  // ============================================================
  // 事件订阅
  // ============================================================

  subscribe(event: string, callback: Function) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
    return () => {
      this.listeners.get(event)?.delete(callback);
    };
  }

  emit(event: string, data: any) {
    this.listeners.get(event)?.forEach(cb => cb(data));
  }
}

export const miyaAPI = new MiyaAPI();

// ============================================================
// React Hooks
// ============================================================

export function useMiyaStatus() {
  const [meta, setMeta] = useState<RuntimeMeta | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetch = async () => {
      const ok = await miyaAPI.healthCheck();
      setConnected(ok);
      if (ok) {
        const m = await miyaAPI.getRuntimeMeta();
        setMeta(m);
        setError(null);
      } else {
        setError('无法连接到后�?API');
      }
    };
    fetch();
    const interval = setInterval(fetch, 5000);
    return () => clearInterval(interval);
  }, []);

  return { meta, connected, error };
}

export function useSystemInfo() {
  const [info, setInfo] = useState<SystemInfo | null>(null);

  useEffect(() => {
    const fetch = async () => {
      const s = await miyaAPI.getSystemInfo();
      if (s) setInfo(s);
    };
    fetch();
    const interval = setInterval(fetch, 3000);
    return () => clearInterval(interval);
  }, []);

  return info;
}

export function useMiyaTools() {
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await miyaAPI.getTools();
      if (res?.tools) {
        setTools(res.tools);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { tools, loading, refresh };
}

export function useMiyaMemory() {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<{ total: number; important: number; emotion: number; conversation: number }>({
    total: 0,
    important: 0,
    emotion: 0,
    conversation: 0,
  });

  const refresh = useCallback(async (limit: number = 50, query?: string) => {
    setLoading(true);
    try {
      const res = await miyaAPI.getMemory({ limit, query });
      if (res && res.memories) {
        setMemories(res.memories);
      }

      const statsRes = await miyaAPI.getMemoryStats();
      if (statsRes) {
        setStats({
          total: statsRes.total ?? 0,
          important: statsRes.important_memories ?? statsRes.long_term ?? 0,
          emotion: statsRes.emotional_memories ?? 0,
          conversation: statsRes.short_term ?? 0,
        });
      } else if (res && res.memories) {
        setStats({
          total: res.total || res.memories.length || 0,
          important: Math.floor((res.memories.length || 0) * 0.15),
          emotion: Math.floor((res.memories.length || 0) * 0.25),
          conversation: Math.floor((res.memories.length || 0) * 0.6),
        });
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const add = useCallback(async (fact: string) => {
    const result = await miyaAPI.addMemory(fact);
    if (!result?.error) await refresh();
    return result;
  }, [refresh]);

  const remove = useCallback(async (uuid: string) => {
    const result = await miyaAPI.deleteMemory(uuid);
    if (!result?.error) await refresh();
    return result;
  }, [refresh]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { memories, loading, refresh, add, remove, stats };
}

export function useCognitiveProfiles() {
  const [profiles, setProfiles] = useState<CognitiveProfile[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async (entityType?: string, limit: number = 20) => {
    setLoading(true);
    try {
      const res = await miyaAPI.getCognitiveProfiles({ entity_type: entityType, limit });
      if (res) setProfiles(res);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { profiles, loading, refresh };
}

export function useMiyaChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);

  const send = useCallback(async (content: string) => {
    setSending(true);
    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}`,
      content,
      sender: 'user',
      time: timeStr,
      type: 'user',
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const resp = await miyaAPI.sendChat(content);
      const respTime = new Date();
      const respTimeStr = `${respTime.getHours().toString().padStart(2, '0')}:${respTime.getMinutes().toString().padStart(2, '0')}`;
      const miyaMsg: ChatMessage = {
        id: `msg_${Date.now()}_miya`,
        content: resp?.response || resp?.content || String(resp),
        sender: '弥娅',
        time: respTimeStr,
        type: 'miya',
      };
      setMessages((prev) => [...prev, miyaMsg]);
      return resp;
    } finally {
      setSending(false);
    }
  }, []);

  return { messages, send, sending };
}

// ============================================================
// 平台 Hook �?// ============================================================

export function usePlatforms() {
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<{ total: number; enabled: number; connected: number }>({
    total: 0,
    enabled: 0,
    connected: 0,
  });

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await miyaAPI.getPlatformStats();
      if (res) {
        setPlatforms(res.platforms);
        setStats({
          total: res.total,
          enabled: res.enabled_count,
          connected: res.connected_count,
        });
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const connect = useCallback(async (platformId: string) => {
    const result = await miyaAPI.connectPlatform(platformId);
    if (result?.success) await refresh();
    return result;
  }, [refresh]);

  const disconnect = useCallback(async (platformId: string) => {
    const result = await miyaAPI.disconnectPlatform(platformId);
    if (result?.success) await refresh();
    return result;
  }, [refresh]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { platforms, loading, refresh, stats, connect, disconnect };
}

// ============================================================
// 插件市场 Hook �?// ============================================================

export function usePluginMarket() {
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async (query?: string) => {
    setLoading(true);
    try {
      const res = query
        ? await miyaAPI.searchPluginMarket(query)
        : await miyaAPI.getPluginMarketList();
      if (res) {
        setPlugins(res.data);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { plugins, loading, refresh };
}

// ============================================================
// 插件管理 Hook �?// ============================================================

export function usePlugins() {
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await miyaAPI.getInstalledPlugins();
      if (res) {
        setPlugins(res.data);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const install = useCallback(async (name: string) => {
    const result = await miyaAPI.installPlugin(name);
    if (result?.success) await refresh();
    return result;
  }, [refresh]);

  const uninstall = useCallback(async (name: string) => {
    const result = await miyaAPI.uninstallPlugin(name);
    if (result?.success) await refresh();
    return result;
  }, [refresh]);

  const enable = useCallback(async (name: string) => {
    const result = await miyaAPI.enablePlugin(name);
    if (result?.success) await refresh();
    return result;
  }, [refresh]);

  const disable = useCallback(async (name: string) => {
    const result = await miyaAPI.disablePlugin(name);
    if (result?.success) await refresh();
    return result;
  }, [refresh]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { plugins, loading, refresh, install, uninstall, enable, disable };
}

// ============================================================
// MCP 服务 Hook �?// ============================================================

export function useMCPServers() {
  const [servers, setServers] = useState<MCPServerInfo[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await miyaAPI.getMCPServerList();
      if (res?.servers) {
        setServers(res.servers);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { servers, loading, refresh };
}

export default miyaAPI;
