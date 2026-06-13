import { useState } from 'react';
import DataRing from '../components/DataRing';
import type { LogEntry } from '../hooks/useMiyaQQData';

interface LogsPageProps {
  logs?: LogEntry[];
  onRefresh?: (level?: string) => void;
}

const defaultLogs: LogEntry[] = [
  { level: 'INFO', message: '系统启动', timestamp: '2024-04-19 12:34:56' },
  { level: 'INFO', message: '连接 QQ 成功', timestamp: '2024-04-19 12:34:57' },
  { level: 'INFO', message: 'ToolNet 初始化完成，加载 69 个工具', timestamp: '2024-04-19 12:34:58' },
  { level: 'WARN', message: '认知记忆服务未连接，使用本地存储', timestamp: '2024-04-19 12:35:01' },
  { level: 'INFO', message: 'Memory engine ready', timestamp: '2024-04-19 12:35:02' },
  { level: 'INFO', message: '收到消息: 然鑫 说"今天过得怎么样?"', timestamp: '2024-04-19 14:22:15' },
  { level: 'INFO', message: '情感分析: 温暖 +85', timestamp: '2024-04-19 14:22:16' },
  { level: 'INFO', message: 'memory_search 调用成功', timestamp: '2024-04-19 14:22:18' },
  { level: 'ERROR', message: '工具执行超时: weather', timestamp: '2024-04-19 15:30:22' },
  { level: 'INFO', message: '天气查询重试成功', timestamp: '2024-04-19 15:30:25' },
  { level: 'DEBUG', message: 'Relationship: love=90, attachment=85, crush=78', timestamp: '2024-04-19 15:45:00' },
];

const levelColors: Record<string, string> = {
  DEBUG: 'text-gray-500',
  INFO: 'text-cyan-400',
  WARN: 'text-yellow-400',
  ERROR: 'text-red-400',
};

const levelBg: Record<string, string> = {
  DEBUG: 'bg-gray-500/10',
  INFO: 'bg-cyan-500/10',
  WARN: 'bg-yellow-500/10',
  ERROR: 'bg-red-500/10',
};

const LogsPage: React.FC<LogsPageProps> = ({ logs = defaultLogs, onRefresh }) => {
  const [filter, setFilter] = useState<string>('ALL');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const filteredLogs = filter === 'ALL' 
    ? logs 
    : logs.filter(log => log.level === filter);

  const counts = {
    ALL: logs.length,
    DEBUG: logs.filter(l => l.level === 'DEBUG').length,
    INFO: logs.filter(l => l.level === 'INFO').length,
    WARN: logs.filter(l => l.level === 'WARN').length,
    ERROR: logs.filter(l => l.level === 'ERROR').length,
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {['ALL', 'DEBUG', 'INFO', 'WARN', 'ERROR'].map(level => (
            <button
              key={level}
              onClick={() => setFilter(level)}
              className={`px-3 py-1 rounded text-xs ${
                filter === level
                  ? 'bg-cyan-500/30 text-cyan-400'
                  : 'bg-black/20 text-gray-500 hover:text-gray-300'
              }`}
            >
              {level} ({counts[level as keyof typeof counts]})
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-gray-500">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-3 h-3 accent-cyan-500"
            />
            自动刷新
          </label>
          <button
            onClick={() => onRefresh?.(filter === 'ALL' ? undefined : filter)}
            className="px-3 py-1 rounded text-xs bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30"
          >
            刷新
          </button>
        </div>
      </div>

      <div className="glass-panel p-2 font-mono text-xs space-y-0.5 max-h-[calc(100vh-200px)] overflow-y-auto">
        {filteredLogs.slice(0, 500).map((log, i) => (
          <div key={i} className={`p-1 rounded ${levelBg[log.level] || ''}`}>
            <span className="text-gray-600">[{log.timestamp}]</span>{' '}
            <span className={levelColors[log.level] || 'text-gray-400'}>[{log.level}]</span>{' '}
            <span className="text-gray-300">{log.message}</span>
          </div>
        ))}
      </div>

       <div className="grid grid-cols-4 gap-4">
         <DataRing 
           value={counts.INFO} 
           label="INFO" 
           color="rgba(0, 188, 212, 0.3)"
           size={80}
         />
         <DataRing 
           value={counts.WARN} 
           label="WARN" 
           color="rgba(255, 193, 7, 0.3)"
           size={80}
         />
         <DataRing 
           value={counts.ERROR} 
           label="ERROR" 
           color="rgba(244, 67, 54, 0.3)"
           size={80}
         />
         <DataRing 
           value={counts.DEBUG} 
           label="DEBUG" 
           color="rgba(158, 158, 158, 0.3)"
           size={80}
         />
       </div>
    </div>
  );
};

export default LogsPage;