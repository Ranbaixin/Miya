// ============================================================
// 弥娅系统类型定义 - 基于 NapcatQQ 后端日志结构
// ============================================================

export interface SystemInfo {
  os: string;
  arch: string;
  python: string;
  node: string;
  workdir: string;
  startup_time: string;
  uuid: string;
  version: string;
  cpu_usage: number;
  memory_total_gb: number;
  memory_used_gb: number;
  memory_usage_percent: number;
}

export interface QQConfig {
  onebot_url: string;
  bot_qq: string;
  super_admin: string;
  connected: boolean;
}

export interface ModelInfo {
  key: string;
  name: string;
  model: string;
  endpoint: string;
  status: 'active' | 'idle' | 'error';
  type: 'chat' | 'embedding' | 'vision';
  tokens_used?: number;
  latency_ms?: number;
}

export interface AgentInfo {
  name: string;
  tool_count: number;
  tools: string[];
  status: 'active' | 'idle';
}

export interface EmotionState {
  dominant_emotion: string;
  intensity: number;
  emotions: Record<string, number>;
  inner_thought: string;
  attribution: string;
  reflection: string;
  relationship_impact: { category: string; value: number }[];
}

export interface MessageQueueStats {
  model: string;
  size: number;
  interval: number;
  processing: boolean;
  last_process_time_ms: number;
}

export interface MessagePipelineEvent {
  id: string;
  timestamp: string;
  stage: 'receive' | 'enqueue' | 'dispatch' | 'analyze' | 'learning' | 'diteng' | 'perceive' | 'cognitive' | 'soul' | 'decision' | 'collab' | 'gestalt' | 'respond' | 'send';
  group?: string;
  user?: string;
  message?: string;
  duration_ms?: number;
  detail?: string;
  model?: string;
}

export interface MemoryStats {
  total: number;
  users: number;
  long_term: number;
  short_term: number;
  emotional: number;
}

export interface MemoryItem {
  uuid: string;
  content: string;
  type: string;
  created_at: string;
  user_id?: string;
}

export interface PersonalityState {
  current_form: string;
  form_name: string;
  description: string;
  vectors: { name: string; value: number; min: number; max: number }[];
  available_forms: string[];
}

export interface SubsystemStatus {
  mlink: boolean;
  memorynet: boolean;
  toolnet: boolean;
  webnet: boolean;
  qqnet: boolean;
  tts: boolean;
  scheduler: boolean;
  proactive: boolean;
}

export interface DashboardData {
  identity: { name: string; version: string; uuid: string; awake_time: string };
  system: SystemInfo;
  qq: QQConfig;
  models: ModelInfo[];
  agents: AgentInfo[];
  emotion: EmotionState;
  queue: MessageQueueStats;
  memory: MemoryStats;
  personality: PersonalityState;
  subsystems: SubsystemStatus;
  pipeline: MessagePipelineEvent[];
  timestamp: string;
}

export interface ToolDefinition {
  function: {
    name: string;
    description: string;
    parameters?: any;
  };
}

export interface PlatformInfo {
  platform_id: string;
  name: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  config: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  sender: string;
  content: string;
  time: string;
  type: 'user' | 'miya';
}

export interface CognitiveEvent {
  id: string;
  document: string;
  score: number;
  metadata: Record<string, any>;
}

export interface MCPServerInfo {
  name: string;
  enabled: boolean;
  status: 'running' | 'stopped' | 'error';
  command?: string;
  tools?: string[];
}
