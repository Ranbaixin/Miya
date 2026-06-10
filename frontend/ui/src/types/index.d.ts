// ============================================================
// 弥娅运维中心 · 类型定义 — MIYA Ops Center v8.0
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

export interface SystemMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  network_bytes_sent: number;
  network_bytes_recv: number;
  uptime_seconds: number;
  process_count: number;
  timestamp: string;
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
  stage: string;
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

// ---- Management API (port 9800) ----

export interface PlatformInfo {
  platform_id: string;
  name: string;
  status: 'online' | 'offline' | 'error' | 'starting' | 'stopping';
  type?: string;
  uptime_seconds?: number;
  config?: Record<string, any>;
}

export interface DaemonStatus {
  started: boolean;
  start_time: string;
  uptime_seconds: number;
  platforms: {
    total: number;
    online: number;
    offline: number;
  };
  version?: string;
}

export interface ManagementHealth {
  status: string;
  timestamp: string;
  started: boolean;
  start_time?: string;
  uptime_seconds?: number;
  platforms?: { total: number; online: number; offline: number };
}

export interface AuthStats {
  total_users: number;
  total_roles: number;
  total_permissions: number;
  superadmin_count?: number;
}

export interface AuthUser {
  user_id: string;
  groups: string[];
  permissions: string[];
  is_superadmin: boolean;
  role_level: number;
  platform?: string;
  username?: string;
}

export interface AuthRole {
  id: string;
  name: string;
  permissions: string[];
  level: number;
}

// ---- WebSocket Events ----

export interface WsInitialState {
  type: 'initial_state';
  timestamp: string;
  platforms: PlatformInfo[];
  daemon: DaemonStatus;
}

export interface WsPlatformEvent {
  type: 'platform_event';
  timestamp: string;
  platform_id: string;
  status: string;
  action?: string;
  success?: boolean;
}

export interface WsActionResult {
  type: 'action_result';
  action: string;
  success: boolean;
  platform_id?: string;
}

export interface WsStatusUpdate {
  type: 'status_update';
  platforms: PlatformInfo[];
  daemon: DaemonStatus;
}

export type WsMessage = WsInitialState | WsPlatformEvent | WsActionResult | WsStatusUpdate | { type: string; message?: string; [key: string]: any };

// ---- Log Entry ----

export interface LogEntry {
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL';
  module: string;
  message: string;
  traceback?: string;
}

// ---- Config -

export interface ConfigFile {
  path: string;
  name: string;
  size_bytes: number;
  modified_at: string;
  content?: string;
  format: 'json' | 'yaml' | 'env' | 'other';
  editable: boolean;
}

// ---- Alert / Monitoring -

export interface AlertInfo {
  alert_id: string;
  rule_id: string;
  metric_name: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  status: 'active' | 'resolved' | 'acknowledged';
  message: string;
  triggered_at: string;
  resolved_at?: string;
  details?: Record<string, any>;
}

export interface MetricSnapshot {
  name: string;
  count: number;
  stats: {
    min: number;
    max: number;
    avg: number;
    median: number;
    stddev: number;
    latest?: number;
  };
}

export interface AlertRule {
  rule_id: string;
  name: string;
  metric_name: string;
  condition: string;
  threshold: number;
  severity: string;
  enabled: boolean;
  description: string;
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
