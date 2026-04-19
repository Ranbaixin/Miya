import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface SystemStats {
  cpu: number;
  memory: number;
  network: number;
  apiLatency: number;
  dbStatus: 'connected' | 'disconnected' | 'connecting';
}

interface SystemMonitorPanelProps {
  stats?: SystemStats;
}

const SystemMonitorPanel: React.FC<SystemMonitorPanelProps> = ({ stats: propStats }) => {
  const [stats, setStats] = useState<SystemStats>(propStats || {
    cpu: 23,
    memory: 45,
    network: 12,
    apiLatency: 45,
    dbStatus: 'connected',
  });

  const [history, setHistory] = useState<number[]>([]);

  useEffect(() => {
    if (propStats) {
      setStats(propStats);
      return;
    }
    
    const interval = setInterval(() => {
      setStats(prev => ({
        cpu: prev.cpu + (Math.random() - 0.5) * 10,
        memory: prev.memory + (Math.random() - 0.5) * 5,
        network: Math.max(0, prev.network + (Math.random() - 0.5) * 8),
        apiLatency: Math.max(10, prev.apiLatency + (Math.random() - 0.5) * 20),
        dbStatus: 'connected',
      }));
      
      setHistory(h => [...h.slice(-30), Math.random() * 100]);
    }, 2000);
    
    return () => clearInterval(interval);
  }, [propStats]);

  const getBarColor = (value: number, max: number = 100) => {
    const percent = value / max;
    if (percent > 0.8) return '#ef4444';
    if (percent > 0.6) return '#f59e0b';
    return '#06b6d4';
  };

  const MetricBar: React.FC<{ label: string; value: number; max?: number; unit: string; color?: string }> = ({
    label, value, max = 100, unit, color
  }) => (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-400">{label}</span>
        <span className="text-white font-mono">{value.toFixed(1)}{unit}</span>
      </div>
      <div className="h-1.5 bg-black/30 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color || getBarColor(value, max) }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, (value / max) * 100)}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
    </div>
  );

  const StatusIndicator: React.FC<{ status: 'connected' | 'disconnected' | 'connecting'; label: string }> = ({
    status, label
  }) => (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${
        status === 'connected' ? 'bg-green-500 animate-pulse' :
        status === 'connecting' ? 'bg-yellow-500 animate-pulse' :
        'bg-red-500'
      }`} />
      <span className="text-xs text-gray-400">{label}</span>
    </div>
  );

  return (
    <div className="glass-panel p-4 space-y-4">
      <div className="text-cyan-400 text-xs flex items-center gap-2">
        <span>◆</span> 系统监控
        <span className="text-gray-600">|</span>
        <StatusIndicator status={stats.dbStatus} label={stats.dbStatus === 'connected' ? 'DB' : '断开'} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <MetricBar label="CPU" value={stats.cpu} unit="%" />
        <MetricBar label="内存" value={stats.memory} unit="%" />
        <MetricBar label="网络" value={stats.network} unit="KB/s" color="#8b5cf6" />
        <MetricBar label="API延迟" value={stats.apiLatency} unit="ms" color="#ec4899" />
      </div>

      <div className="pt-2 border-t border-cyan-500/10">
        <div className="text-xs text-gray-500 mb-2">负载趋势</div>
        <div className="h-12 flex items-end gap-0.5">
          {history.length > 0 ? (
            history.slice(-20).map((v, i) => (
              <motion.div
                key={i}
                className="flex-1 rounded-t"
                style={{
                  backgroundColor: getBarColor(v),
                  opacity: 0.6 + (i / 20) * 0.4,
                }}
                initial={{ height: 0 }}
                animate={{ height: `${v}%` }}
                transition={{ duration: 0.3 }}
              />
            ))
          ) : (
            Array.from({ length: 20 }).map((_, i) => (
              <div
                key={i}
                className="flex-1 bg-cyan-500/30 rounded-t"
                style={{ height: `${20 + Math.random() * 60}%` }}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default SystemMonitorPanel;