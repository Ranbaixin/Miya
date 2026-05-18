// ============================================================
// 弥娅运维中心 API · MIYA Ops Center v7.0
//   Web API (:8000) + Management API (:9800) + WebSocket
// ============================================================

const CORE = 'http://localhost:8000';
const MGMT = 'http://localhost:9800';
const MGMT_WS = 'ws://localhost:9800/api/v1/ws';
const API_KEY = 'changeme';

function hdrs(extra?: HeadersInit): Record<string, string> {
  const base: Record<string, string> = { 'Content-Type': 'application/json', 'X-Undefined-API-Key': API_KEY };
  if (!extra) return base;
  if (extra instanceof Headers) { const r = { ...base }; extra.forEach((v, k) => { r[k] = v; }); return r; }
  if (Array.isArray(extra)) return Object.assign(base, Object.fromEntries(extra));
  return { ...base, ...(extra as Record<string, string>) };
}

async function req<T = any>(baseUrl: string, path: string, init?: RequestInit): Promise<T | null> {
  try {
    const r = await fetch(`${baseUrl}${path}`, { ...init, headers: hdrs(init?.headers) });
    if (!r.ok) return null;
    const t = await r.text();
    try { return JSON.parse(t); } catch { return t as any; }
  } catch { return null; }
}

// ---- Core API (:8000) ----

export async function fetchHealth(): Promise<boolean> {
  try { return (await fetch(`${CORE}/api/health`)).ok; } catch { return false; }
}

export async function fetchDashboard() {
  const r = await req<any>(CORE, '/api/status');
  if (r) return r;
  return {
    identity: { name: '弥娅·阿尔缪斯', version: '7.0.0', uuid: 'edc00845' },
    subsystems: { mlink: true, memorynet: true, toolnet: true, webnet: true, qqnet: true, tts: true, scheduler: true, proactive: true },
    models: [], agents: [],
    emotion: { dominant_emotion: '温暖', intensity: 85, emotions: { '温暖': 85, '依恋': 70, '幸福': 60 }, inner_thought: '', attribution: '', reflection: '', relationship_impact: [] },
    queue: { size: 0 },
    personality: { current_form: '绯雪态', description: '雪落无声，愿系铃中。', vectors: [], available_forms: [] },
    memory_stats: { total: 0, long_term: 0, short_term: 0, emotional: 0 },
  };
}

export async function fetchSystemMetrics() {
  const r = await req<any>(CORE, '/api/system/info');
  if (!r) return { cpu_percent: 0, memory_percent: 0, memory_used_gb: 0, memory_total_gb: 0, disk_percent: 0, disk_used_gb: 0, disk_total_gb: 0, uptime_seconds: 0 };
  return {
    cpu_percent: r.cpu_usage || r.cpu_percent || 0,
    memory_percent: r.memory_usage_percent || r.memory_percent || 0,
    memory_used_gb: r.memory_used_gb || 0,
    memory_total_gb: r.memory_total_gb || 0,
    disk_percent: r.disk_usage_percent || 0,
    disk_used_gb: r.disk_used_gb || 0,
    disk_total_gb: r.disk_total_gb || 0,
    network_bytes_sent: r.network_bytes_sent || 0,
    network_bytes_recv: r.network_bytes_recv || 0,
    uptime_seconds: r.uptime_seconds || 0,
    process_count: r.process_count || 0,
    timestamp: new Date().toISOString(),
  };
}

export async function fetchModels() {
  const r = await req<any>(CORE, '/api/status');
  if (r?.models?.length) return r.models;
  return [
    { key: 'deepseek_v4_flash', name: 'DeepSeek V4 Flash', model: 'deepseek-v4-flash', endpoint: 'api.deepseek.com', status: 'active' as const, type: 'chat' as const },
    { key: 'qwen_7b', name: 'Qwen 7B', model: 'Qwen2.5-7B', endpoint: 'api.siliconflow.cn', status: 'active' as const, type: 'chat' as const },
    { key: 'qwen_72b', name: 'Qwen 72B', model: 'Qwen2.5-72B', endpoint: 'api.siliconflow.cn', status: 'active' as const, type: 'chat' as const },
    { key: 'kimi_k2_6', name: 'Kimi K2.6', model: 'Kimi-K2.6', endpoint: 'api.siliconflow.cn', status: 'active' as const, type: 'vision' as const },
    { key: 'glm_45v', name: 'GLM-4.5V', model: 'glm-4.5v', endpoint: 'open.bigmodel.cn', status: 'active' as const, type: 'vision' as const },
    { key: 'internlm_7b', name: 'InternLM 7B', model: 'InternLM2.5-7B', endpoint: 'api.siliconflow.cn', status: 'active' as const, type: 'chat' as const },
    { key: 'r1_distill', name: 'R1 Distill 7B', model: 'R1-Distill-Qwen-7B', endpoint: 'api.siliconflow.cn', status: 'active' as const, type: 'chat' as const },
    { key: 'llama_3_1', name: 'Llama 3.1 8B', model: 'Llama-3.1-8B', endpoint: 'api.siliconflow.cn', status: 'active' as const, type: 'chat' as const },
    { key: 'gemma_2', name: 'Gemma 2 9B', model: 'gemma-2-9b-it', endpoint: 'api.siliconflow.cn', status: 'active' as const, type: 'chat' as const },
    { key: 'bge_large', name: 'BGE Large', model: 'bge-large-zh-v1.5', endpoint: 'api.siliconflow.cn', status: 'active' as const, type: 'embedding' as const },
    { key: 'qwen3_emb', name: 'Qwen3 Emb 8B', model: 'Qwen3-Embedding-8B', endpoint: 'api.siliconflow.cn', status: 'active' as const, type: 'embedding' as const },
    { key: 'ds_emb', name: 'DeepSeek Emb', model: 'deepseek-embedding', endpoint: 'api.deepseek.com', status: 'active' as const, type: 'embedding' as const },
  ];
}

export async function fetchAgents() {
  const r = await req<any>(CORE, '/api/agents');
  if (r?.agents?.length) return r.agents;
  return [
    { name: 'code_delivery_agent', tool_count: 1, tools: ['python_interpreter'], status: 'active' as const },
    { name: 'entertainment_agent', tool_count: 5, tools: ['horoscope', 'qq_like', 'send_poke', 'react_emoji', 'wenchang_dijun'], status: 'active' as const },
    { name: 'file_analysis_agent', tool_count: 4, tools: ['group_file_downloader', 'local_file_finder', 'qq_file_reader', 'qq_image_analyzer'], status: 'active' as const },
    { name: 'info_agent', tool_count: 4, tools: ['baiduhot', 'douyinhot', 'qq_level_query', 'weibohot'], status: 'active' as const },
    { name: 'web_agent', tool_count: 2, tools: ['crawl_webpage', 'web_search'], status: 'active' as const },
  ];
}

export async function fetchTools() { return req(CORE, '/api/tools'); }
export async function fetchEmotion() {
  const r = await req<any>(CORE, '/api/emotion');
  return r || { dominant_emotion: '温暖', intensity: 85, emotions: { '温暖': 85, '依恋': 70, '幸福': 60 }, inner_thought: '', attribution: '', reflection: '', relationship_impact: [] };
}
export async function fetchMemoryStats() {
  const r = await req<any>(CORE, '/api/memory/stats');
  return r ? { total: r.total || 0, users: r.users || 0, long_term: r.long_term || 0, short_term: r.short_term || 0, emotional: 0 } : { total: 0, users: 0, long_term: 0, short_term: 0, emotional: 0 };
}
export async function fetchPersonality() {
  const r = await req<any>(CORE, '/api/v1/personality/vectors');
  return r || { current_form: '绯雪态', description: '雪落无声，愿系铃中。', vectors: [], available_forms: [] };
}

// ---- Management API (:9800) ----

export async function fetchMgmtHealth() {
  return req<any>(MGMT, '/api/v1/health');
}

export async function fetchPlatforms() {
  const r = await req<any>(MGMT, '/api/v1/platforms');
  return r?.platforms || [];
}

export async function fetchPlatform(platformId: string) {
  return req<any>(MGMT, `/api/v1/platforms/${platformId}`);
}

export async function startPlatform(platformId: string) {
  return req<any>(MGMT, `/api/v1/platforms/${platformId}/start`, { method: 'POST' });
}

export async function stopPlatform(platformId: string) {
  return req<any>(MGMT, `/api/v1/platforms/${platformId}/stop`, { method: 'POST' });
}

export async function restartPlatform(platformId: string) {
  return req<any>(MGMT, `/api/v1/platforms/${platformId}/restart`, { method: 'POST' });
}

export async function fetchDaemonStatus() {
  return req<any>(MGMT, '/api/v1/daemon/status');
}

export async function fetchAuthStatus() {
  return req<any>(MGMT, '/api/v1/auth/status');
}

export async function fetchAuthRoles() {
  const r = await req<any>(MGMT, '/api/v1/auth/roles');
  return r?.roles || [];
}

export async function fetchAuthUsers() {
  const r = await req<any>(MGMT, '/api/v1/auth/users');
  return r?.users || [];
}

export async function fetchAuthUser(userId: string) {
  return req<any>(MGMT, `/api/v1/auth/users/${userId}`);
}

export async function grantRole(userId: string, platform: string, groups: string[], username?: string) {
  return req<any>(MGMT, `/api/v1/auth/users/${userId}/grant`, {
    method: 'POST',
    body: JSON.stringify({ platform, groups, username: username || userId }),
  });
}

export async function revokeRole(userId: string, groups?: string[]) {
  return req<any>(MGMT, `/api/v1/auth/users/${userId}/revoke`, {
    method: 'POST',
    body: JSON.stringify({ groups: groups || [] }),
  });
}

// ---- WebSocket ----

type WsCallback = (msg: any) => void;

class ManagementWebSocket {
  private ws: WebSocket | null = null;
  private callbacks: Set<WsCallback> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _connected = false;

  get connected() { return this._connected; }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) return;
    try {
      this.ws = new WebSocket(MGMT_WS);
      this.ws.onopen = () => {
        this._connected = true;
        this.notifyAll({ type: 'connection', status: 'connected' });
      };
      this.ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          this.notifyAll(msg);
        } catch { /* ignore */ }
      };
      this.ws.onclose = () => {
        this._connected = false;
        this.notifyAll({ type: 'connection', status: 'disconnected' });
        this.scheduleReconnect();
      };
      this.ws.onerror = () => { this.ws?.close(); };
    } catch {
      this.scheduleReconnect();
    }
  }

  disconnect() {
    if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null; }
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
    this._connected = false;
  }

  send(action: string, params: Record<string, any> = {}) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action, ...params }));
    }
  }

  subscribe(cb: WsCallback): () => void {
    this.callbacks.add(cb);
    return () => { this.callbacks.delete(cb); };
  }

  private notifyAll(msg: any) {
    this.callbacks.forEach(cb => { try { cb(msg); } catch { /* ignore */ } });
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 3000);
  }
}

export const mgmtWs = new ManagementWebSocket();

// ---- React Hooks ----

import { useState, useEffect, useCallback } from 'react';

export function useMiyaConnection() {
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    const check = async () => { setConnected(await fetchHealth()); };
    check();
    const t = setInterval(check, 5000);
    return () => clearInterval(t);
  }, []);
  return { connected };
}

export function useDashboard() {
  const [data, setData] = useState<any>(null);
  const refresh = useCallback(async () => { const d = await fetchDashboard(); if (d) setData(d); }, []);
  useEffect(() => { refresh(); const t = setInterval(refresh, 3000); return () => clearInterval(t); }, [refresh]);
  return { data, refresh };
}

export function useModels() {
  const [models, setModels] = useState<any[]>([]);
  const refresh = useCallback(async () => { const m = await fetchModels(); if (m?.length) setModels(m); }, []);
  useEffect(() => { refresh(); const t = setInterval(refresh, 10000); return () => clearInterval(t); }, [refresh]);
  return { models, refresh };
}

export function useAgents() {
  const [agents, setAgents] = useState<any[]>([]);
  const refresh = useCallback(async () => { const a = await fetchAgents(); if (a?.length) setAgents(a); }, []);
  useEffect(() => { refresh(); const t = setInterval(refresh, 15000); return () => clearInterval(t); }, [refresh]);
  return { agents, refresh };
}

export function useEmotion() {
  const [emotion, setEmotion] = useState<any>(null);
  const refresh = useCallback(async () => { const e = await fetchEmotion(); if (e) setEmotion(e); }, []);
  useEffect(() => { refresh(); const t = setInterval(refresh, 3000); return () => clearInterval(t); }, [refresh]);
  return { emotion, refresh };
}

export function useMemory() {
  const [stats, setStats] = useState({ total: 0, users: 0, long_term: 0, short_term: 0, emotional: 0 });
  const refresh = useCallback(async () => { const s = await fetchMemoryStats(); if (s) setStats(s); }, []);
  useEffect(() => { refresh(); const t = setInterval(refresh, 30000); return () => clearInterval(t); }, [refresh]);
  return { stats, refresh };
}

export function usePersonality() {
  const [personality, setPersonality] = useState<any>(null);
  const refresh = useCallback(async () => { const p = await fetchPersonality(); if (p) setPersonality(p); }, []);
  useEffect(() => { refresh(); const t = setInterval(refresh, 10000); return () => clearInterval(t); }, [refresh]);
  return { personality, refresh };
}

export function useSystemMetrics() {
  const [metrics, setMetrics] = useState({
    cpu_percent: 0, memory_percent: 0, memory_used_gb: 0, memory_total_gb: 0,
    disk_percent: 0, disk_used_gb: 0, disk_total_gb: 0,
    network_bytes_sent: 0, network_bytes_recv: 0,
    uptime_seconds: 0, process_count: 0, timestamp: '',
  });
  const refresh = useCallback(async () => {
    const m = await fetchSystemMetrics();
    if (m) setMetrics({
      cpu_percent: m.cpu_percent ?? 0,
      memory_percent: m.memory_percent ?? 0,
      memory_used_gb: m.memory_used_gb ?? 0,
      memory_total_gb: m.memory_total_gb ?? 0,
      disk_percent: m.disk_percent ?? 0,
      disk_used_gb: m.disk_used_gb ?? 0,
      disk_total_gb: m.disk_total_gb ?? 0,
      network_bytes_sent: m.network_bytes_sent ?? 0,
      network_bytes_recv: m.network_bytes_recv ?? 0,
      uptime_seconds: m.uptime_seconds ?? 0,
      process_count: m.process_count ?? 0,
      timestamp: m.timestamp ?? '',
    });
  }, []);
  useEffect(() => { refresh(); const t = setInterval(refresh, 3000); return () => clearInterval(t); }, [refresh]);
  return { metrics, refresh };
}

export function usePlatforms() {
  const [platforms, setPlatforms] = useState<any[]>([]);
  const [daemonStatus, setDaemonStatus] = useState<any>(null);
  const [wsConnected, setWsConnected] = useState(false);

  const refresh = useCallback(async () => {
    const [p, d] = await Promise.all([fetchPlatforms(), fetchDaemonStatus()]);
    if (p?.length) setPlatforms(p);
    if (d) setDaemonStatus(d);
  }, []);

  useEffect(() => {
    refresh();
    mgmtWs.connect();

    const unsub = mgmtWs.subscribe((msg: any) => {
      switch (msg.type) {
        case 'initial_state':
        case 'status_update':
          if (msg.platforms) setPlatforms(msg.platforms);
          if (msg.daemon) setDaemonStatus(msg.daemon);
          break;
        case 'platform_event':
          refresh();
          break;
        case 'connection':
          setWsConnected(msg.status === 'connected');
          if (msg.status === 'connected') refresh();
          break;
      }
    });

    const poll = setInterval(refresh, 15000);
    return () => { unsub(); clearInterval(poll); };
  }, [refresh]);

  const start = useCallback(async (id: string) => { await startPlatform(id); mgmtWs.send('start_platform', { platform_id: id }); }, []);
  const stop = useCallback(async (id: string) => { await stopPlatform(id); mgmtWs.send('stop_platform', { platform_id: id }); }, []);
  const restart = useCallback(async (id: string) => { await restartPlatform(id); mgmtWs.send('restart_platform', { platform_id: id }); }, []);

  return { platforms, daemonStatus, wsConnected, start, stop, restart, refresh };
}

export function useAuth() {
  const [users, setUsers] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [selectedUser, setSelectedUser] = useState<any>(null);

  const refresh = useCallback(async () => {
    const [u, r, s] = await Promise.all([fetchAuthUsers(), fetchAuthRoles(), fetchAuthStatus()]);
    if (u) setUsers(u);
    if (r) setRoles(r);
    if (s) setStats(s);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const viewUser = useCallback(async (userId: string) => {
    const u = await fetchAuthUser(userId);
    if (u) setSelectedUser(u);
  }, []);

  const grant = useCallback(async (userId: string, platform: string, groups: string[], username?: string) => {
    await grantRole(userId, platform, groups, username);
    refresh();
  }, [refresh]);

  const revoke = useCallback(async (userId: string, groups?: string[]) => {
    await revokeRole(userId, groups);
    refresh();
  }, [refresh]);

  return { users, roles, stats, selectedUser, viewUser, grant, revoke, refresh, clearUser: () => setSelectedUser(null) };
}

// ---- Health & Resources API ----

export async function fetchHealthReport() {
  try {
    const r = await fetch(`${CORE}/api/management/health`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return {
    status: 'unknown', issues: [],
    bot: { status: 'unknown' },
    system: { uptime: 0, memory_mb: 0, cpu_percent: 0, tool_calls_success: 0, tool_calls_failed: 0 },
    memory: { short_term: { count: 0 }, cognitive: { events: 0 }, top_memory: { count: 0 } },
  };
}

export async function fetchHealthMetrics() {
  try {
    const r = await fetch(`${CORE}/health/metrics`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return {
    cpu_percent: 0, memory_percent: 0, memory_used_mb: 0, memory_total_mb: 0,
    disk_usage_percent: 0, disk_free_gb: 0, disk_total_gb: 0,
    network_sent_mb: 0, network_recv_mb: 0,
    process_count: 0, thread_count: 0, open_files: 0, uptime: 0,
  };
}

export async function fetchHealthChecks() {
  try {
    const r = await fetch(`${CORE}/health/checks`, { headers: hdrs() });
    if (r.ok) return (await r.json()).checks || [];
  } catch { /* ignore */ }
  return [];
}

export async function fetchHealthHistory(limit = 10) {
  try {
    const r = await fetch(`${CORE}/health/history?limit=${limit}`, { headers: hdrs() });
    if (r.ok) return (await r.json()).history || [];
  } catch { /* ignore */ }
  return [];
}

export async function fetchResourceStats() {
  try {
    const r = await fetch(`${CORE}/resources/stats`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return {
    total_resources: 0, total_size_bytes: 0,
    by_type: {}, leaks_detected: 0,
    memory_info: { rss_mb: 0, vms_mb: 0, gc_objects: 0, gc_collected: 0, gc_uncollectable: 0, gc_threshold: [0, 0, 0] },
  };
}

export async function fetchResourceMemory() {
  try {
    const r = await fetch(`${CORE}/resources/memory`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return null;
}

export async function cleanupResources(forceGc = false) {
  try {
    const r = await fetch(`${CORE}/resources/cleanup${forceGc ? '?force_gc=1' : ''}`, { method: 'POST', headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return { message: '清理请求已发送' };
}

export async function terminalChat(message: string, sessionId?: string) {
  try {
    const r = await fetch(`${CORE}/api/terminal/chat`, {
      method: 'POST',
      headers: hdrs(),
      body: JSON.stringify({ message, session_id: sessionId || 'web-terminal', from_terminal: true }),
    });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return { response: '终端无响应', status: 'error', session_id: '' };
}

export async function fetchModelBridgeHealth() {
  try {
    const r = await fetch('http://localhost:8888/v1/health', { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return null;
}

export async function fetchBotManagementStats() {
  try {
    const r = await fetch(`${CORE}/api/management/stats`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return { uptime: 0, total_messages: 0, total_commands: 0, memory_mb: 0, cpu_percent: 0, tool_calls_success: 0, tool_calls_failed: 0 };
}

export async function fetchManagementLogs(lines = 100) {
  try {
    const r = await fetch(`${CORE}/api/management/logs?lines=${lines}`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return [];
}

// ---- Health Hook ----

export function useHealth() {
  const [report, setReport] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [checks, setChecks] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [botStats, setBotStats] = useState<any>(null);

  const refresh = useCallback(async () => {
    const [r, m, c, h, bs] = await Promise.all([
      fetchHealthReport(), fetchHealthMetrics(), fetchHealthChecks(),
      fetchHealthHistory(30), fetchBotManagementStats(),
    ]);
    if (r) setReport(r);
    if (m) setMetrics(m);
    if (c) setChecks(c);
    if (h) setHistory(h);
    if (bs) setBotStats(bs);
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 10000); return () => clearInterval(t); }, [refresh]);

  return { report, metrics, checks, history, botStats, refresh };
}

// ---- Resources Hook ----

export function useResources() {
  const [stats, setStats] = useState<any>(null);
  const [memory, setMemory] = useState<any>(null);

  const refresh = useCallback(async () => {
    const [s, m] = await Promise.all([fetchResourceStats(), fetchResourceMemory()]);
    if (s) setStats(s);
    if (m) setMemory(m);
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 15000); return () => clearInterval(t); }, [refresh]);

  const doCleanup = useCallback(async (forceGc = false) => {
    await cleanupResources(forceGc);
    setTimeout(refresh, 1000);
  }, [refresh]);

  return { stats, memory, refresh, cleanup: doCleanup };
}

// ======== Memory / Scheduler / Knowledge API + Hooks ========

export async function fetchMemoryList(limit = 100, query?: string) {
  try {
    const q = query ? `&query=${encodeURIComponent(query)}` : '';
    const r = await fetch(`${CORE}/api/memory/list?limit=${limit}${q}`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return { success: true, data: { items: [] }, total: 0 };
}

export async function fetchMemoryGraph(userId = 'default') {
  try {
    const r = await fetch(`${CORE}/api/plug/alkaid/ltm/graph?user_id=${encodeURIComponent(userId)}`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return { status: 'ok', data: { nodes: [], edges: [] } };
}

export async function fetchCronJobs() {
  try {
    const r = await fetch(`${CORE}/api/cron/jobs`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return { success: true, data: [], total: 0 };
}

export async function fetchPlugins() {
  try {
    const r = await fetch(`${CORE}/api/plugin/get`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return { success: true, data: [], total: 0 };
}

export async function fetchKnowledgeBases() {
  try {
    const r = await fetch(`${CORE}/api/knowledge_base/list`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return { success: true, data: [], total: 0 };
}

export async function fetchProviderList() {
  try {
    const r = await fetch(`${CORE}/api/provider/list`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return { providers: [] };
}

export async function fetchSkills() {
  try {
    const r = await fetch(`${CORE}/api/skills`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return { skills: [], total: 0 };
}

export async function fetchMCPList() {
  try {
    const r = await fetch(`${CORE}/api/mcp/list`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return { servers: [], total: 0 };
}

export async function fetchStats() {
  try {
    const r = await fetch(`${CORE}/api/stat/get`, { headers: hdrs() });
    if (r.ok) return await r.json();
  } catch { /* ignore */ }
  return { success: true, data: { total_conversations: 0, total_messages: 0, total_users: 0, active_providers: 0, total_providers: 0 } };
}

export function useMemorySystem() {
  const [memoryList, setMemoryList] = useState<any>(null);
  const [memoryGraph, setMemoryGraph] = useState<any>(null);
  const [query, setQuery] = useState('');

  const refresh = useCallback(async () => {
    const [list, graph] = await Promise.all([fetchMemoryList(50, query || undefined), fetchMemoryGraph('default')]);
    if (list) setMemoryList(list);
    if (graph) setMemoryGraph(graph);
  }, [query]);

  useEffect(() => { refresh(); const t = setInterval(refresh, 30000); return () => clearInterval(t); }, [refresh]);
  const search = useCallback((q: string) => { setQuery(q); }, []);
  return { memoryList, memoryGraph, refresh, search, query };
}

export function useScheduler() {
  const [cronJobs, setCronJobs] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const refresh = useCallback(async () => {
    const [jobs, st] = await Promise.all([fetchCronJobs(), fetchStats()]);
    if (jobs) setCronJobs(jobs);
    if (st) setStats(st);
  }, []);
  useEffect(() => { refresh(); const t = setInterval(refresh, 15000); return () => clearInterval(t); }, [refresh]);
  return { cronJobs, stats, refresh };
}

export function useKnowledge() {
  const [kb, setKb] = useState<any>(null);
  const [plugins, setPlugins] = useState<any>(null);
  const [providers, setProviders] = useState<any>(null);
  const [skills, setSkills] = useState<any>(null);
  const [mcpServers, setMcpServers] = useState<any>(null);
  const refresh = useCallback(async () => {
    const [k, p, pr, s, m] = await Promise.all([fetchKnowledgeBases(), fetchPlugins(), fetchProviderList(), fetchSkills(), fetchMCPList()]);
    if (k) setKb(k); if (p) setPlugins(p); if (pr) setProviders(pr); if (s) setSkills(s); if (m) setMcpServers(m);
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  return { kb, plugins, providers, skills, mcpServers, refresh };
}
