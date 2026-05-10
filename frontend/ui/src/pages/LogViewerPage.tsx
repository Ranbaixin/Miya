// ============================================================
// 弥娅 日志 · LogViewerPage — 实时日志
// ============================================================
import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface LogEntry {
  id: number;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG';
  module: string;
  message: string;
  thinking?: string;
}

const LEVEL_COLORS: Record<string, string> = {
  INFO: 'text-aether-bright',
  WARN: 'text-starlight',
  ERROR: 'text-status-error',
  DEBUG: 'text-text-secondary',
};

function generateMockLog(): LogEntry {
  const modules = ['MLink', 'MemNet', 'Hub', 'Soul', 'ToolNet', 'Cognitive', 'DecisionHub', 'Gestalt'];
  const levels: LogEntry['level'][] = ['INFO', 'INFO', 'INFO', 'WARN', 'ERROR'];

  const messages: Record<string, string[]> = {
    MLink: ['QQ消息 -> group | 1523878699(佳)', '群: 1092980378(索多玛)', '连接成功！', '弥娅 QQ 机器人已启动'],
    MemNet: ['[记忆] 写入短期记忆完成', '[记忆] 检索到 3 条相关记忆（MMR去重后）'],
    Hub: ['[决策中枢] 选择响应策略', '[消息队列] 已启动模型处理: model=default'],
    Soul: ['♥ 情绪分析 温暖(85%)', '✦ 内心独白更新完成', '♥ 关系影响(熟悉) 亲近+3'],
    ToolNet: ['[工具] 执行: web_search', '[工具] 执行完成', '[工具] 已注册 16 个 Agent 工具'],
    Cognitive: ['[认知] 关键词提取完成', '[认知] 当前话题分析完成'],
    DecisionHub: ['[决策] 消息分析完成', '[决策] 调度决策 -> Agent网络'],
    Gestalt: ['[格式塔] 工具执行完成', '[格式塔] Agent协调完成'],
  };

  const module = modules[Math.floor(Math.random() * modules.length)];
  const level = levels[Math.floor(Math.random() * levels.length)];
  const msg = messages[module]?.[Math.floor(Math.random() * (messages[module]?.length || 1))] || '系统正常运行';

  const now = new Date();
  const ts = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}.${now.getMilliseconds().toString().padStart(3, '0')}`;

  return { id: Date.now() + Math.random() * 1000, timestamp: ts, level, module, message: msg };
}

const LogViewerPage: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState('');
  const [levelFilter, setLevelFilter] = useState('ALL');
  const [autoScroll, setAutoScroll] = useState(true);
  const [paused, setPaused] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (paused) return;
    const interval = setInterval(() => {
      setLogs((prev) => {
        const next = [...prev, generateMockLog()];
        return next.length > 500 ? next.slice(-300) : next;
      });
    }, 800);
    return () => clearInterval(interval);
  }, [paused]);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter((l) => {
    if (levelFilter !== 'ALL' && l.level !== levelFilter) return false;
    if (filter && !l.message.toLowerCase().includes(filter.toLowerCase()) && !l.module.toLowerCase().includes(filter.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex flex-col h-full">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border-glass bg-void-panel/80 shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-text-dim uppercase tracking-wider">▷ 日志查看器</span>
          <span className="text-[10px] text-text-dim">{filteredLogs.length} / {logs.length} 条</span>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="过滤..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-32 bg-void-surface border border-border-glass rounded px-2 py-1 text-xs text-text-primary placeholder-text-dim outline-none focus:border-aether/30 transition-colors"
          />
          {['ALL', 'INFO', 'WARN', 'ERROR', 'DEBUG'].map(l => (
            <motion.button
              key={l}
              onClick={() => setLevelFilter(l)}
              className={`text-[10px] px-2 py-1 rounded border transition-colors ${
                levelFilter === l
                  ? 'bg-aether/10 border-aether/25 text-aether-bright'
                  : 'bg-void-surface/50 border-border-glass text-text-secondary hover:text-text-primary'
              }`}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {l}
            </motion.button>
          ))}
          <button
            onClick={() => setPaused(!paused)}
            className={`text-[10px] px-2 py-1 rounded border transition-colors ${paused ? 'bg-starlight/10 border-starlight/25 text-starlight' : 'bg-status-active/5 border-status-active/20 text-status-active'}`}
          >
            {paused ? '▶ 继续' : '⏸ 暂停'}
          </button>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`text-[10px] px-2 py-1 rounded border transition-colors ${autoScroll ? 'bg-aether/10 border-aether/25 text-aether-bright' : 'bg-void-surface/50 border-border-glass text-text-dim'}`}
          >
            ↓ 自动
          </button>
          <button
            onClick={() => setLogs([])}
            className="text-[10px] px-2 py-1 rounded border border-status-error/20 bg-status-error/5 text-status-error transition-colors"
          >
            ✕ 清除
          </button>
        </div>
      </div>

      {/* 日志列表 */}
      <div ref={containerRef} className="flex-1 overflow-y-auto font-mono text-[11px] p-1">
        <AnimatePresence initial={false}>
          {filteredLogs.map((log) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className={`px-3 py-1 border-b border-aether/5 hover:bg-aether/3 cursor-pointer transition-colors ${expandedId === log.id ? 'bg-aether/5' : ''}`}
              onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
            >
              <div className="flex items-center gap-2">
                <span className="text-text-dim shrink-0 w-[90px] text-[10px]">{log.timestamp}</span>
                <span className={`${LEVEL_COLORS[log.level]} shrink-0 w-11 text-[10px] font-bold`}>{log.level}</span>
                <span className="text-resonance-bright shrink-0 w-22 truncate text-[10px]">{log.module}</span>
                <span className="text-text-primary text-[10px] break-all">{log.message}</span>
              </div>
              {expandedId === log.id && log.thinking && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="ml-[200px] mt-1 mb-1 px-3 py-2 border-l-2 border-aether/30 bg-aether/3 rounded-r text-[10px] text-text-secondary"
                >
                  <span className="text-aether text-[9px]">◇ 思考过程</span>
                  <div className="mt-1 text-text-primary">{log.thinking}</div>
                </motion.div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        {filteredLogs.length === 0 && (
          <div className="flex items-center justify-center h-full text-text-dim">
            {logs.length === 0 ? '等待日志...' : '无匹配日志'}
          </div>
        )}
      </div>

      {/* 底部 */}
      <div className="h-6 bg-void-panel/90 border-t border-border-glass flex items-center justify-between px-3 text-[9px] text-text-dim shrink-0">
        <span>{paused ? '⏸ 已暂停' : '● 收集中'} | {filteredLogs.length} 条显示</span>
        <span>MIYA Abyssal Star · v7.0 Log Monitor</span>
      </div>
    </div>
  );
};

export default LogViewerPage;
