// ============================================================
// 弥娅运维中心 · MessageQueuePage — 消息队列监控 (对接后端)
// ============================================================
import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../utils';

const CORE = 'http://localhost:8000';

interface QueueStats {
  size: number;
  processing: boolean;
  model?: string;
  interval?: number;
  last_process_time_ms?: number;
}

interface PipelineEvent {
  id: string;
  timestamp: string;
  stage: string;
  user?: string;
  group?: string;
  message?: string;
  duration_ms?: number;
  detail?: string;
  model?: string;
}

const STAGES = [
  { key: 'receive', label: '接收', icon: '◇' },
  { key: 'perceive', label: '感知', icon: '◎' },
  { key: 'cognitive', label: '认知', icon: '◆' },
  { key: 'soul', label: '灵魂', icon: '♥' },
  { key: 'decision', label: '决策', icon: '▣' },
  { key: 'respond', label: '响应', icon: '◉' },
  { key: 'collab', label: '协作', icon: '≣' },
  { key: 'send', label: '发送', icon: '▷' },
];

const stageColors: Record<string, string> = {
  receive: 'text-aether-bright',
  perceive: 'text-resonance-bright',
  cognitive: 'text-starlight',
  soul: 'text-status-active',
  decision: 'text-aether',
  respond: 'text-resonance-bright',
  collab: 'text-starlight',
  send: 'text-text-secondary',
  enqueue: 'text-text-dim',
  dispatch: 'text-text-dim',
};

async function fetchQueueStats(): Promise<QueueStats | null> {
  try {
    const res = await fetch(`${CORE}/api/queue/stats`, {
      headers: { 'X-Undefined-API-Key': 'changeme' },
    });
    if (res.ok) return await res.json();
  } catch { /* ignore */ }
  return null;
}

async function fetchMiyaStatus(): Promise<any | null> {
  try {
    const res = await fetch(`${CORE}/api/status`, {
      headers: { 'X-Undefined-API-Key': 'changeme' },
    });
    if (res.ok) return await res.json();
  } catch { /* ignore */ }
  return null;
}

const MessageQueuePage: React.FC = () => {
  const [queueStats, setQueueStats] = useState<QueueStats>({ size: 0, processing: false });
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [connected, setConnected] = useState(false);

  const fetchData = useCallback(async () => {
    const [stats, status] = await Promise.all([fetchQueueStats(), fetchMiyaStatus()]);
    if (stats) { setQueueStats(stats); setConnected(true); }
    if (status?.pipeline) {
      setEvents(status.pipeline.slice(0, 20));
    }
  }, []);

  useEffect(() => {
    fetchData();
    const t = setInterval(fetchData, 5000);
    return () => clearInterval(t);
  }, [fetchData]);

  // Fallback mock if no real data
  useEffect(() => {
    if (!connected) {
      const mocks: PipelineEvent[] = [
        { id: '1', timestamp: new Date().toISOString(), stage: 'receive', user: '然鑫', message: '帮我看看今天的天气', group: '私聊' },
        { id: '2', timestamp: new Date().toISOString(), stage: 'perceive', duration_ms: 120, detail: '意图识别: 信息查询', model: 'perceive' },
        { id: '3', timestamp: new Date().toISOString(), stage: 'cognitive', duration_ms: 85, detail: '认知处理', model: 'deepseek-v4-flash' },
        { id: '4', timestamp: new Date().toISOString(), stage: 'soul', duration_ms: 45, detail: '情感分析: 积极', model: 'emotion' },
        { id: '5', timestamp: new Date().toISOString(), stage: 'decision', duration_ms: 60, detail: '调度决策', model: 'hub' },
        { id: '6', timestamp: new Date().toISOString(), stage: 'collab', duration_ms: 50, detail: 'Agent 协调', model: 'agent_network' },
        { id: '7', timestamp: new Date().toISOString(), stage: 'respond', duration_ms: 230, detail: '生成回复', model: 'deepseek-v4-flash' },
        { id: '8', timestamp: new Date().toISOString(), stage: 'send', duration_ms: 15, detail: '发送回复', group: '私聊' },
      ];
      setEvents(mocks);
      setQueueStats({ size: 3, processing: true, model: 'deepseek-v4-flash', interval: 5, last_process_time_ms: 230 });
    }
  }, [connected]);

  const totalDuration = events.reduce((sum, e) => sum + (e.duration_ms || 0), 0);

  return (
    <div className="p-4 overflow-auto h-full space-y-4">
      {/* 队列概览卡片 */}
      <div className="grid grid-cols-4 gap-3">
        <StatsCard label="队列大小" value={String(queueStats.size)} unit="条" icon="≣" color="aether" />
        <StatsCard label="处理状态" value={queueStats.processing ? '处理中' : '空闲'} icon="◆" color={queueStats.processing ? 'active' : 'idle'} />
        <StatsCard label="当前模型" value={queueStats.model || '—'} icon="◉" color="resonance" />
        <StatsCard label="总耗时" value={`${totalDuration}ms`} icon="↻" color="starlight" />
      </div>

      {/* 流水线 */}
      <motion.div className="glass-panel p-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="text-xs font-bold text-text-primary mb-4 flex items-center justify-between">
          <span>◆ 消息处理流水线 · 8 阶段</span>
          <span className={cn('text-[10px]', connected ? 'text-status-active' : 'text-text-dim')}>
            {connected ? '▲ API' : '◇ Mock'}
          </span>
        </div>
        <div className="flex items-center gap-0.5 overflow-x-auto pb-2">
          {STAGES.map((stage, i) => {
            const ev = events.find(e => e.stage === stage.key);
            const active = !!ev;
            return (
              <div key={stage.key} className="flex items-center gap-0.5 flex-shrink-0">
                <motion.div
                  className={cn(
                    'flex flex-col items-center p-2 rounded-lg min-w-[56px] transition-colors',
                    active ? 'bg-aether/5 border border-aether/15' : 'bg-void-deep/30 border border-transparent'
                  )}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <span className={cn('text-lg mb-0.5', active ? 'text-aether' : 'text-text-dim')}>{stage.icon}</span>
                  <span className={cn('text-[10px] font-bold', active ? 'text-text-primary' : 'text-text-dim')}>{stage.label}</span>
                  <span className="text-[8px] text-text-dim mt-0.5">{stage.key}</span>
                  {active && ev?.duration_ms && (
                    <span className="text-[8px] text-aether mt-0.5 font-mono">{ev.duration_ms}ms</span>
                  )}
                </motion.div>
                {i < STAGES.length - 1 && (
                  <span className="text-text-dim/20 text-xs mx-0.5">→</span>
                )}
              </div>
            );
          })}
        </div>
      </motion.div>

      {/* 事件日志 */}
      <div>
        <div className="text-xs font-bold text-text-primary mb-2 ml-1">◆ 事件日志</div>
        <div className="space-y-1">
          {events.length === 0 ? (
            <div className="glass-panel p-8 text-center text-text-dim text-xs">等待消息流事件...</div>
          ) : (
            events.map((e, i) => {
              const time = e.timestamp ? new Date(e.timestamp).toLocaleTimeString('zh-CN', { hour12: false }) : '--:--:--';
              return (
                <motion.div
                  key={e.id || i}
                  className="flex items-center gap-3 glass-panel py-2 px-3 text-[11px]"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }}
                  whileHover={{ borderColor: 'rgba(0,229,255,0.2)' }}
                >
                  <span className="text-text-dim font-mono text-[10px] w-16 shrink-0">{time}</span>
                  <span className={cn('font-medium w-16 shrink-0 text-[10px]', stageColors[e.stage] || 'text-text-secondary')}>
                    {e.stage.toUpperCase()}
                  </span>
                  {e.user && <span className="text-starlight shrink-0 w-12 text-[10px] truncate">{e.user}</span>}
                  <span className="text-text-secondary flex-1 truncate text-[10px]">
                    {e.message || e.detail || '—'}
                  </span>
                  {e.duration_ms != null && (
                    <span className="text-text-dim font-mono text-[9px] shrink-0 w-14 text-right">{e.duration_ms}ms</span>
                  )}
                  {e.model && (
                    <span className="text-aether text-[9px] shrink-0 max-w-[120px] truncate">{e.model}</span>
                  )}
                  {e.group && (
                    <span className="text-text-dim text-[9px] shrink-0">{e.group}</span>
                  )}
                </motion.div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

function StatsCard({ label, value, unit, icon, color }: {
  label: string; value: string; unit?: string; icon: string; color: string;
}) {
  const colorMap: Record<string, string> = {
    aether: 'text-aether border-aether/20',
    resonance: 'text-resonance-bright border-resonance/20',
    starlight: 'text-starlight border-starlight/20',
    active: 'text-status-active border-status-active/20',
    idle: 'text-text-dim border-border-glass',
  };

  return (
    <motion.div
      className={cn('glass-panel p-3', colorMap[color] || colorMap.idle)}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02 }}
    >
      <div className="text-[10px] text-text-dim mb-1">{icon} {label}</div>
      <div className="flex items-baseline gap-1">
        <span className="text-lg font-bold font-mono">{value}</span>
        {unit && <span className="text-[10px] text-text-dim">{unit}</span>}
      </div>
    </motion.div>
  );
}

export default MessageQueuePage;
