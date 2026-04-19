import { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000';

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
  id: string;
  content: string;
  tags: string[];
  timestamp: string;
  importance: number;
}

export interface ModelInfo {
  name: string;
  provider: string;
  status: 'active' | 'idle' | 'error';
  tokens: number;
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

class MiyaAPI {
  private baseUrl: string;
  private listeners: Map<string, Set<Function>> = new Map();

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async healthCheck(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/api/health`);
      return res.ok;
    } catch {
      return false;
    }
  }

  async getStatus() {
    try {
      const res = await fetch(`${this.baseUrl}/api/status`);
      return await res.json();
    } catch (e) {
      console.error('获取状态失败:', e);
      return null;
    }
  }

  async getSystemStatus() {
    try {
      const res = await fetch(`${this.baseUrl}/api/system/status`);
      if (res.ok) return await res.json();
    } catch {}
    return null;
  }

  async getEmotion(): Promise<EmotionState | null> {
    try {
      const res = await fetch(`${this.baseUrl}/api/emotion`);
      return await res.json();
    } catch {
      return null;
    }
  }

  async sendChat(message: string, sessionId?: string) {
    const res = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        session_id: sessionId || `web_${Date.now()}`,
        platform: 'web'
      })
    });
    return await res.json();
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
  const [status, setStatus] = useState<any>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const fetch = async () => {
      const ok = await miyaAPI.healthCheck();
      setConnected(ok);
      if (ok) {
        const s = await miyaAPI.getStatus();
        setStatus(s);
      }
    };
    fetch();
    const interval = setInterval(fetch, 3000);
    return () => clearInterval(interval);
  }, []);

  return { status, connected };
}

export function useMiyaEmotion() {
  const [emotion, setEmotion] = useState<EmotionState | null>(null);

  useEffect(() => {
    const fetch = async () => {
      const e = await miyaAPI.getEmotion();
      if (e) setEmotion(e);
    };
    fetch();
    const interval = setInterval(fetch, 2000);
    return () => clearInterval(interval);
  }, []);

  return emotion;
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
        content: resp.response,
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