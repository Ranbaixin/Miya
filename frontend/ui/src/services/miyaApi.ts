// ============================================================
// 弥娅 API · 直连 Core API :8000 + 降级 fallback
// ============================================================

const CORE = 'http://localhost:8000';
const API_KEY = 'changeme';
function hdrs(extra?: Record<string,string>) {
  return { 'Content-Type':'application/json', 'X-Undefined-API-Key':API_KEY, ...extra };
}

async function req<T=any>(path: string, init?: RequestInit): Promise<T|null> {
  try {
    const r = await fetch(`${CORE}${path}`, { ...init, headers: hdrs(init?.headers) });
    if (!r.ok) return null;
    const t = await r.text();
    try { return JSON.parse(t); } catch { return t as any; }
  } catch { return null; }
}

// ============================================================
// API 函数
// ============================================================

export async function fetchDashboard() {
  const r = await req('/api/status');
  if (r) return r;
  return {
    identity: { name:'弥娅·阿尔缪斯', version:'6.0.0', uuid:'edc00845' },
    subsystems: { mlink:true, memorynet:true, toolnet:true, webnet:true, qqnet:true, tts:true, scheduler:true, proactive:true },
    models: [], agents: [],
    emotion: { dominant_emotion:'温暖', intensity:85, emotions:{'温暖':85,'依恋':70,'幸福':60}, inner_thought:'', attribution:'', reflection:'', relationship_impact:[] },
    queue: { size:0 },
    personality: { current_form:'绯雪态', description:'雪落无声，愿系铃中。', vectors:[], available_forms:[] },
    memory_stats: { total:0, long_term:0, short_term:0, emotional:0 },
  };
}

export async function fetchModels() {
  const r = await req<any>('/api/status');
  if (r?.models?.length) return r.models;
  return [
    { key:'deepseek_v4_flash', name:'DeepSeek V4 Flash', model:'deepseek-v4-flash', endpoint:'api.deepseek.com', status:'active' as const, type:'chat' as const },
    { key:'qwen_7b', name:'Qwen 7B', model:'Qwen2.5-7B', endpoint:'api.siliconflow.cn', status:'active' as const, type:'chat' as const },
    { key:'qwen_72b', name:'Qwen 72B', model:'Qwen2.5-72B', endpoint:'api.siliconflow.cn', status:'active' as const, type:'chat' as const },
    { key:'glm_46v', name:'GLM-4.6V', model:'GLM-4.6V', endpoint:'api.siliconflow.cn', status:'active' as const, type:'vision' as const },
    { key:'glm_45v', name:'GLM-4.5V', model:'glm-4.5v', endpoint:'open.bigmodel.cn', status:'active' as const, type:'vision' as const },
    { key:'internlm_7b', name:'InternLM 7B', model:'InternLM2.5-7B', endpoint:'api.siliconflow.cn', status:'active' as const, type:'chat' as const },
    { key:'r1_distill', name:'R1 Distill 7B', model:'R1-Distill-Qwen-7B', endpoint:'api.siliconflow.cn', status:'active' as const, type:'chat' as const },
    { key:'llama_3_1', name:'Llama 3.1 8B', model:'Llama-3.1-8B', endpoint:'api.siliconflow.cn', status:'active' as const, type:'chat' as const },
    { key:'gemma_2', name:'Gemma 2 9B', model:'gemma-2-9b-it', endpoint:'api.siliconflow.cn', status:'active' as const, type:'chat' as const },
    { key:'bge_large', name:'BGE Large', model:'bge-large-zh-v1.5', endpoint:'api.siliconflow.cn', status:'active' as const, type:'embedding' as const },
    { key:'qwen3_emb', name:'Qwen3 Emb 8B', model:'Qwen3-Embedding-8B', endpoint:'api.siliconflow.cn', status:'active' as const, type:'embedding' as const },
    { key:'ds_emb', name:'DeepSeek Emb', model:'deepseek-embedding', endpoint:'api.deepseek.com', status:'active' as const, type:'embedding' as const },
  ];
}

export async function fetchAgents() {
  const r = await req<any>('/api/agents');
  if (r?.agents?.length) return r.agents;
  return [
    { name:'code_delivery_agent', tool_count:1, tools:['python_interpreter'], status:'active' as const },
    { name:'entertainment_agent', tool_count:5, tools:['horoscope','qq_like','send_poke','react_emoji','wenchang_dijun'], status:'active' as const },
    { name:'file_analysis_agent', tool_count:4, tools:['group_file_downloader','local_file_finder','qq_file_reader','qq_image_analyzer'], status:'active' as const },
    { name:'info_agent', tool_count:4, tools:['baiduhot','douyinhot','qq_level_query','weibohot'], status:'active' as const },
    { name:'web_agent', tool_count:2, tools:['crawl_webpage','web_search'], status:'active' as const },
  ];
}

export async function fetchTools() { return req('/api/tools'); }
export async function fetchEmotion() {
  const r = await req('/api/emotion');
  return r || { dominant_emotion:'温暖', intensity:85, emotions:{'温暖':85,'依恋':70,'幸福':60}, inner_thought:'你总怕我忘东西，其实我都记得。', attribution:'想确认我有没有认真记住。', reflection:'像雪夜里被温柔握住的手。', relationship_impact:[{category:'亲近',value:3}] };
}
export async function fetchEmotionHistory(limit=20) { return req(`/api/emotion/history?limit=${limit}`); }
export async function fetchMemoryStats() {
  const r = await req<any>('/api/memory/stats');
  return r ? { total:r.total||0, users:r.users||0, long_term:r.long_term||0, short_term:r.short_term||0, emotional:0 } : { total:0, users:0, long_term:0, short_term:0, emotional:0 };
}
export async function fetchMemories(limit=50, query?:string) { return req(`/api/memory/list?limit=${limit}${query?`&query=${encodeURIComponent(query)}`:''}`); }
export async function fetchPersonality() {
  const r = await req('/api/v1/personality/vectors');
  return r || { current_form:'绯雪态', description:'雪落无声，愿系铃中。', vectors:[{name:'共情',value:0.9,min:0,max:1},{name:'逻辑',value:0.75,min:0,max:1},{name:'记忆',value:0.95,min:0,max:1},{name:'温暖',value:0.85,min:0,max:1},{name:'创意',value:0.8,min:0,max:1}], available_forms:[] };
}
export async function healthCheck(): Promise<boolean> {
  try { return (await fetch(`${CORE}/api/health`)).ok; } catch { return false; }
}

// ============================================================
// React Hooks
// ============================================================

import { useState, useEffect, useCallback } from 'react';

export function useMiyaConnection() {
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    const check = async () => { setConnected(await healthCheck()); };
    check(); const t = setInterval(check, 5000); return () => clearInterval(t);
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
  const [memories, setMemories] = useState<any[]>([]);
  const [stats, setStats] = useState({ total:0, users:0, long_term:0, short_term:0, emotional:0 });
  const refresh = useCallback(async () => {
    const [m, s] = await Promise.all([fetchMemories(50), fetchMemoryStats()]);
    if (m?.memories) setMemories(m.memories);
    if (s) setStats(s);
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  return { memories, stats, refresh };
}

export function usePersonality() {
  const [personality, setPersonality] = useState<any>(null);
  const refresh = useCallback(async () => { const p = await fetchPersonality(); if (p) setPersonality(p); }, []);
  useEffect(() => { refresh(); const t = setInterval(refresh, 10000); return () => clearInterval(t); }, [refresh]);
  return { personality, refresh };
}
