// ============================================================
// 弥娅 消息流 · MessageQueuePage — 消息队列监控
// ============================================================
import { useState } from 'react';
import { motion } from 'framer-motion';
import type { MessagePipelineEvent } from '../types/index.d';

const MOCK_EVENTS: MessagePipelineEvent[] = [
  { id: '1', timestamp: new Date().toISOString(), stage: 'receive', user: '佳', message: '帮我看看今天的天气', group: '私聊' },
  { id: '2', timestamp: new Date().toISOString(), stage: 'perceive', duration_ms: 120, detail: '意图识别: 信息查询', model: 'perceive' },
  { id: '3', timestamp: new Date().toISOString(), stage: 'cognitive', duration_ms: 85, detail: '认知处理', model: 'deepseek-v4-flash' },
  { id: '4', timestamp: new Date().toISOString(), stage: 'soul', duration_ms: 45, detail: '情感分析: 积极', model: 'emotion' },
  { id: '5', timestamp: new Date().toISOString(), stage: 'decision', duration_ms: 60, detail: '调度决策', model: 'hub' },
  { id: '6', timestamp: new Date().toISOString(), stage: 'respond', duration_ms: 230, detail: '生成回复', model: 'deepseek-v4-flash' },
  { id: '7', timestamp: new Date().toISOString(), stage: 'send', duration_ms: 15, detail: '发送回复', group: '私聊' },
];

const stageColors: Record<string, string> = {
  receive: 'text-aether-bright',
  perceive: 'text-resonance-bright',
  cognitive: 'text-starlight',
  soul: 'text-status-active',
  decision: 'text-aether',
  respond: 'text-resonance-bright',
  send: 'text-text-secondary',
  enqueue: 'text-text-dim',
  dispatch: 'text-text-dim',
};

const MessageQueuePage: React.FC = () => {
  const [events] = useState<MessagePipelineEvent[]>(MOCK_EVENTS);

  return (
    <div className="p-4 overflow-auto h-full space-y-3">
      <div className="text-[10px] text-text-dim uppercase tracking-[0.2em]">≣ 消息流</div>

      {/* 流水线概览 */}
      <div className="glass-panel p-4">
        <div className="text-[10px] text-text-dim uppercase tracking-widest mb-3">消息处理流水线</div>
        <div className="flex items-center gap-1.5 overflow-x-auto pb-2">
          {['接收', '感知', '认知', '灵魂', '决策', '响应', '发送'].map((stage, i) => (
            <motion.div
              key={stage}
              className="flex items-center gap-2"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
            >
              <div className="w-3 h-3 rounded-full bg-aether/20 border border-aether/30 relative">
                <div className="absolute inset-0 rounded-full bg-aether/60 animate-pulse" />
              </div>
              <span className="text-[10px] text-text-secondary whitespace-nowrap">{stage}</span>
              {i < 6 && (
                <svg width="20" height="8" className="text-text-dim/20 shrink-0">
                  <line x1="0" y1="4" x2="18" y2="4" stroke="currentColor" strokeWidth="1" strokeDasharray="2,2" />
                </svg>
              )}
            </motion.div>
          ))}
        </div>
      </div>

      {/* 事件列表 */}
      <div className="space-y-1.5">
        <div className="text-[10px] text-text-dim uppercase tracking-widest ml-1">事件日志</div>
        {events.map((e, i) => {
          const time = new Date(e.timestamp).toLocaleTimeString('zh-CN', { hour12: false });
          return (
            <motion.div
              key={e.id}
              className="flex items-center gap-3 glass-panel py-2.5 px-3 text-[11px]"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 + i * 0.04 }}
            >
              <span className="text-text-dim font-mono text-[10px] w-16 shrink-0">{time}</span>
              <span className={`font-medium w-16 shrink-0 ${stageColors[e.stage] || 'text-text-secondary'}`}>
                {e.stage.toUpperCase()}
              </span>
              {e.user && (
                <span className="text-starlight shrink-0 w-10">{e.user}</span>
              )}
              <span className="text-text-secondary flex-1 truncate">
                {e.message || e.detail || ''}
              </span>
              {e.duration_ms && (
                <span className="text-text-dim font-mono text-[10px] shrink-0">{e.duration_ms}ms</span>
              )}
              {e.model && (
                <span className="text-aether text-[10px] shrink-0 max-w-[120px] truncate">{e.model}</span>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

export default MessageQueuePage;
