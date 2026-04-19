import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useSystemInfo, useMiyaStatus, type SystemInfo } from '../services/miyaApi';

interface RuntimeStats {
  startTime: string;
  runtime: number;
  messagesToday: number;
  messagesWeek: number;
  messagesMonth: number;
  toolCalls: number;
}

interface RuntimeInfoPanelProps {
  stats?: RuntimeStats;
}

const RuntimeInfoPanel: React.FC<RuntimeInfoPanelProps> = ({ stats: propStats }) => {
  const [stats, setStats] = useState<RuntimeStats>(propStats || {
    startTime: new Date().toISOString().slice(0, 19).replace('T', ' '),
    runtime: 0,
    messagesToday: 0,
    messagesWeek: 0,
    messagesMonth: 0,
    toolCalls: 0,
  });

  const { meta, connected, error } = useMiyaStatus();
  const systemInfo = useSystemInfo();

  useEffect(() => {
    if (propStats) {
      setStats(propStats);
      return;
    }

    const interval = setInterval(() => {
      setStats(prev => ({
        ...prev,
        runtime: prev.runtime + 1,
        messagesToday: prev.messagesToday + (Math.random() > 0.7 ? 1 : 0),
      }));
    }, 2000);

    return () => clearInterval(interval);
  }, [propStats]);

  const formatDuration = (seconds: number): string => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const formatNumber = (n: number): string => {
    if (n >= 10000) return `${(n / 10000).toFixed(1)}w`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
    return n.toString();
  };

  return (
    <div className="glass-panel p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-cyan-400 text-xs flex items-center gap-2">
          <motion.span
            className="w-2 h-2 rounded-full"
            animate={{
              backgroundColor: connected ? ['#22c55e', '#22c55e', '#22c55e'] : ['#ef4444', '#ef4444', '#ef4444'],
              boxShadow: connected ? ['0 0 6px #22c55e', '0 0 10px #22c55e', '0 0 6px #22c55e'] : ['0 0 6px #ef4444', '0 0 10px #ef4444', '0 0 6px #ef4444']
            }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
          运行时
        </div>
        <div className="text-[10px]">
          {connected ? (
            <span className="text-green-400">已连接</span>
          ) : (
            <span className="text-red-400">{error || '未连接'}</span>
          )}
        </div>
      </div>

      <div className="text-center py-2">
        <motion.div
          className="text-3xl font-mono text-white tracking-wider"
          animate={{ 
            textShadow: [
              '0 0 10px rgba(6,182,212,0.5)', 
              '0 0 20px rgba(6,182,212,0.8)', 
              '0 0 10px rgba(6,182,212,0.5)'
            ] 
          }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          {formatDuration(stats.runtime)}
        </motion.div>
        <div className="text-xs text-gray-500 mt-1">运行时长</div>
      </div>

      {systemInfo && (
        <div className="grid grid-cols-2 gap-2 text-[10px]">
          <div className="bg-black/20 rounded p-2">
            <div className="text-cyan-400 font-mono">{systemInfo.cpu_usage_percent?.toFixed(1) || '--'}%</div>
            <div className="text-gray-600">CPU</div>
          </div>
          <div className="bg-black/20 rounded p-2">
            <div className="text-purple-400 font-mono">{systemInfo.memory_usage_percent?.toFixed(1) || '--'}%</div>
            <div className="text-gray-600">内存</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-2">
        <div className="bg-black/20 rounded p-2 text-center">
          <motion.div
            className="text-lg text-cyan-400 font-bold"
            key={stats.messagesToday}
            initial={{ scale: 1.1 }}
            animate={{ scale: 1 }}
          >
            {formatNumber(stats.messagesToday)}
          </motion.div>
          <div className="text-[10px] text-gray-500">今日</div>
        </div>
        <div className="bg-black/20 rounded p-2 text-center">
          <div className="text-lg text-purple-400 font-bold">{formatNumber(stats.messagesWeek)}</div>
          <div className="text-[10px] text-gray-500">本周</div>
        </div>
        <div className="bg-black/20 rounded p-2 text-center">
          <div className="text-lg text-yellow-400 font-bold">{formatNumber(stats.messagesMonth)}</div>
          <div className="text-[10px] text-gray-500">本月</div>
        </div>
      </div>

      <div className="space-y-2 pt-2 border-t border-cyan-500/10">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">工具调用</span>
          <span className="text-sm text-cyan-400 font-mono">{formatNumber(stats.toolCalls)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">启动时间</span>
          <span className="text-xs text-gray-400">{stats.startTime}</span>
        </div>
        {systemInfo && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Python</span>
            <span className="text-xs text-gray-400">{systemInfo.python_version?.split('.')[0]}.{systemInfo.python_version?.split('.')[1]}</span>
          </div>
        )}
      </div>

      <div className="flex flex-wrap justify-center gap-1">
        {['启动', '运行', '响应', '记忆'].map((label, i) => (
          <motion.div
            key={label}
            className="flex items-center gap-1 px-2 py-1 rounded-full bg-black/20"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <motion.div
              className="w-1.5 h-1.5 rounded-full bg-cyan-500"
              animate={{ scale: [1, 1.3, 1], opacity: [1, 0.5, 1] }}
              transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
            />
            <span className="text-[10px] text-gray-500">{label}</span>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default RuntimeInfoPanel;