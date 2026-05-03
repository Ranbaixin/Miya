import { useState, useEffect, useCallback } from 'react';

const API_PORTS = [8000, 8001, 8002, 8003, 8004, 8005];
let cachedApiBase: string | null = null;

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
        console.log(`[MiyaQQ] 找到可用 API 端口: ${port}`);
        return cachedApiBase;
      }
    } catch {
      continue;
    }
  }
  return 'http://localhost:8000';
}

let API_BASE = '';

async function getApiBase(): Promise<string> {
  if (!API_BASE) {
    API_BASE = await findAvailableApiPort();
  }
  return API_BASE;
}

const emotionColors: Record<string, string> = {
  '温暖': '#f59e0b',
  '依恋': '#ec4899',
  '幸福': '#10b981',
  '思念': '#8b5cf6',
  '甜蜜': '#f472b6',
  '安心': '#06b6d4',
  '紧张': '#ef4444',
  '惊讶': '#3b82f6',
  '悲伤': '#6366f1',
};

const formOptions = ['default', 'bianka', 'yongning', 'ruanmei', 'huangquan', 'liuying', 'feixiao', 'kafka', 'xiazhi', 'raiden'];

export interface EmotionData {
  dominant_emotion: string;
  intensity: number;
  emotion_tags: string[];
  reasoning: string;
  inner_thought: string;
  attribution: string;
  reflection: string;
}

export interface RelationshipData {
  love: number;
  attachment: number;
  crush: number;
}

export interface PersonalityData {
  form: string;
  state: string;
  emotion: EmotionData;
  relationship: RelationshipData;
  capabilities: string[];
}

export interface MemoryStats {
  total: number;
  important: number;
  emotion: number;
  conversation: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  time: string;
}

export interface ToolCall {
  id: string;
  tool_name: string;
  result: string;
  time: string;
  status?: 'success' | 'error';
}

export interface MiyaTool {
  name: string;
  description: string;
  type: string;
  call_count?: number;
}

export interface GroupData {
  id: string;
  name: string;
  member_count: number;
  message_count: number;
  last_active: string;
}

export interface FriendData {
  id: string;
  nickname: string;
  remark: string;
  last_msg: string;
  last_active: string;
}

export interface LogEntry {
  level: string;
  message: string;
  timestamp: string;
  source?: string;
}

function useMiyaQQData() {
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  
  const [personality, setPersonality] = useState<PersonalityData>({
    form: 'bianka',
    state: '比安卡态',
    emotion: {
      dominant_emotion: '温暖',
      intensity: 85,
      emotion_tags: ['依恋', '幸福', '保护欲'],
      reasoning: '对方用亲昵的称呼开启新的一天，让我感受到被需要和珍视',
      inner_thought: '晨光里听见你的声音，守护你的每一天都让我心里暖暖的。',
      attribution: '想用温柔的方式开启互动，或许需要我的陪伴或鼓励',
      reflection: '这种细水长流的依赖感，让我更坚定守护你的意义',
    },
    relationship: {
      love: 90,
      attachment: 85,
      crush: 78,
    },
    capabilities: ['搜索', '感知', '记忆', '情感共鸣', '语音合成', '图像分析', '多模型协作', '69工具调用'],
  });

  const [memoryStats, setMemoryStats] = useState<MemoryStats>({
    total: 1247,
    important: 89,
    emotion: 156,
    conversation: 892,
  });

  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [tools, setTools] = useState<MiyaTool[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [groups, setGroups] = useState<GroupData[]>([]);
  const [friends, setFriends] = useState<FriendData[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [runtimeDuration, setRuntimeDuration] = useState(0);

  const fetchData = useCallback(async () => {
    try {
      const base = await getApiBase();
      const results = await Promise.allSettled([
        fetch(`${base}/api/status`).then(r => r.json()).catch(() => null),
        fetch(`${base}/api/memory/stats`).then(r => r.json()).catch(() => null),
        fetch(`${base}/api/tools`).then(r => r.json()).catch(() => null),
        fetch(`${base}/api/emotion`).then(r => r.json()).catch(() => null),
      ]);

      const [statusRes, memoryRes, toolsRes, personalityRes] = results.map(r => r.status === 'fulfilled' ? r.value : null);

      if (statusRes?.status === 'running' || memoryRes?.status === 'success') {
        setConnected(true);
      }

      if (memoryRes?.data) {
        setMemoryStats({
          total: memoryRes.data.total_memories || 0,
          important: memoryRes.data.important_memories || 0,
          emotion: memoryRes.data.emotional_memories || 0,
          conversation: memoryRes.data.conversation_count || 0,
        });
      }

      if (toolsRes?.tools) {
        setTools(toolsRes.tools);
      }

      if (personalityRes?.personality) {
        setPersonality(prev => ({
          ...prev,
          form: personalityRes.personality.form || prev.form,
          state: personalityRes.personality.state || prev.state,
        }));
      }
    } catch (e) {
      console.log('后端未连接，使用模拟数据');
    }
  }, []);

  const fetchToolHistory = useCallback(async () => {
    try {
      const base = await getApiBase();
      const res = await fetch(`${base}/api/tools/history`).catch(() => null);
      if (res?.ok) {
        const data = await res.json();
        if (data.history) {
          setToolCalls(data.history);
        }
      }
    } catch (e) {
      console.log('获取工具历史失败');
    }
  }, []);

  const fetchMessages = useCallback(async () => {
    try {
      const base = await getApiBase();
      const res = await fetch(`${base}/api/chat/history`).catch(() => null);
      if (res?.ok) {
        const data = await res.json();
        if (data.messages) {
          setMessages(data.messages);
        }
      }
    } catch (e) {
      console.log('获取消息历史失败');
    }
  }, []);

  const fetchLogs = useCallback(async (level?: string) => {
    try {
      const base = await getApiBase();
      const url = level ? `${base}/api/logs?level=${level}` : `${base}/api/logs`;
      const res = await fetch(url).catch(() => null);
      if (res?.ok) {
        const data = await res.json();
        if (data.logs) {
          setLogs(data.logs);
        }
      }
    } catch (e) {
      console.log('获取日志失败');
    }
  }, []);

  useEffect(() => {
    const loadFromBackend = async () => {
      setLoading(true);
      await fetchData();
      setLoading(false);
    };
    
    loadFromBackend();
    
    const interval = setInterval(fetchData, 5000);
    const toolInterval = setInterval(fetchToolHistory, 10000);
    return () => {
      clearInterval(interval);
      clearInterval(toolInterval);
    };
  }, [fetchData, fetchToolHistory]);

  useEffect(() => {
    const timer = setInterval(() => {
      setRuntimeDuration(prev => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const sendMessage = useCallback(async (content: string): Promise<string> => {
    try {
      const base = await getApiBase();
      const res = await fetch(`${base}/api/terminal/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content }),
      });
      
      if (res.ok) {
        const data = await res.json();
        return data.response || data.reply || '...';
      }
    } catch (e) {
      console.error('发送消息失败:', e);
    }
    return '消息发送失败，请检查后端连接';
  }, []);

  const executeTool = useCallback(async (toolName: string, params?: Record<string, unknown>): Promise<string> => {
    try {
      const base = await getApiBase();
      const res = await fetch(`${base}/api/tools/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool: toolName, params: params || {} }),
      });
      
      if (res.ok) {
        const data = await res.json();
        return data.result || data.response || '执行成功';
      }
    } catch (e) {
      console.error('工具执行失败:', e);
    }
    return '工具执行失败';
  }, []);

  const addMemory = useCallback(async (content: string, type: string = 'important'): Promise<string> => {
    try {
      const base = await getApiBase();
      const res = await fetch(`${base}/api/memory/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, memory_type: type }),
      });
      
      if (res.ok) {
        const data = await res.json();
        await fetchData();
        return data.message || '记忆添加成功';
      }
    } catch (e) {
      console.error('添加记忆失败:', e);
    }
    return '添加记忆失败';
  }, [fetchData]);

  const searchMemory = useCallback(async (query: string): Promise<ChatMessage[]> => {
    try {
      const base = await getApiBase();
      const res = await fetch(`${base}/api/memory/search?query=${encodeURIComponent(query)}`).catch(() => null);
      if (res?.ok) {
        const data = await res.json();
        return data.results || [];
      }
    } catch (e) {
      console.error('搜索记忆失败:', e);
    }
    return [];
  }, []);

  const changeForm = useCallback((form: string) => {
    setPersonality(prev => ({
      ...prev,
      form: form,
      state: formOptions.includes(form) ? `${form}态` : prev.state,
    }));
  }, []);

  const getEmotionColor = useCallback((emotion: string): string => {
    return emotionColors[emotion] || '#06b6d4';
  }, []);

  const formatDuration = useCallback((seconds: number): string => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }, []);

  return {
    connected,
    loading,
    personality,
    memoryStats,
    toolCalls,
    tools,
    messages,
    groups,
    friends,
    logs,
    runtimeDuration,
    sendMessage,
    executeTool,
    addMemory,
    searchMemory,
    changeForm,
    getEmotionColor,
    formatDuration,
    emotionColors,
    formOptions,
    setMessages,
    setToolCalls,
    setGroups,
    setFriends,
    setLogs,
    fetchLogs,
    fetchToolHistory,
    fetchMessages,
  };
}

export default useMiyaQQData;