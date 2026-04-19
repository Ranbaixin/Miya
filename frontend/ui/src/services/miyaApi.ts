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
}

export interface CognitiveEvent {
  id: string;
  document: string;
  score: number;
  metadata: Record<string, any>;
}

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

  async getRuntimeMeta(): Promise<RuntimeMeta | null> {
    return this._request<RuntimeMeta>('/api/v1/management/runtime/meta');
  }

  async getSystemInfo(): Promise<SystemInfo | null> {
    return this._request<SystemInfo>('/api/v1/management/system');
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

  async getTools(): Promise<{ tools: ToolDefinition[] } | null> {
    return this._request('/api/v1/management/runtime/tools');
  }

  async invokeTool(toolName: string, args: Record<string, any> = {}) {
    return this._request('/api/v1/management/runtime/tools/invoke', {
      method: 'POST',
      body: JSON.stringify({
        tool_name: toolName,
        parameters: args,
      }),
    });
  }

  async getMemory(params?: { limit?: number; offset?: number; query?: string }) {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    if (params?.query) query.set('query', params.query);
    const queryStr = query.toString() ? `?${query.toString()}` : '';
    return this._request(`/api/v1/memory${queryStr}`);
  }

  async addMemory(fact: string) {
    return this.invokeTool('memory_add', { fact });
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

  async getCognitiveProfiles(params?: { entity_type?: string; limit?: number }) {
    const query = new URLSearchParams();
    if (params?.entity_type) query.set('entity_type', params.entity_type);
    if (params?.limit) query.set('limit', String(params.limit));
    const queryStr = query.toString() ? `?${query.toString()}` : '';
    return this._request(`/api/v1/management/runtime/cognitive/profiles${queryStr}`);
  }

  async getCognitiveProfile(entityType: string, entityId: string) {
    return this._request(`/api/v1/management/runtime/cognitive/profile/${entityType}/${entityId}`);
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
        setError('无法连接到后端 API');
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
  const [stats, setStats] = useState<{total: number, important: number, emotion: number, conversation: number}>({
    total: 0, important: 0, emotion: 0, conversation: 0
  });

  const refresh = useCallback(async (limit: number = 50, query?: string) => {
    setLoading(true);
    try {
      const res = await miyaAPI.getMemory({ limit, query });
      if (res && res.memories) {
        setMemories(res.memories);
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
    const timeStr = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}`;
    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}`,
      content,
      sender: '佳',
      time: timeStr,
      type: 'user'
    };
    setMessages(prev => [...prev, userMsg]);

    try {
      const resp = await miyaAPI.sendChat(content);
      const respTime = new Date();
      const respTimeStr = `${respTime.getHours().toString().padStart(2,'0')}:${respTime.getMinutes().toString().padStart(2,'0')}`;
      const miyaMsg: ChatMessage = {
        id: `msg_${Date.now()}_miya`,
        content: resp.response || resp.content || String(resp),
        sender: '弥娅',
        time: respTimeStr,
        type: 'miya'
      };
      setMessages(prev => [...prev, miyaMsg]);
      return resp;
    } finally {
      setSending(false);
    }
  }, []);

  return { messages, send, sending };
}

export default miyaAPI;