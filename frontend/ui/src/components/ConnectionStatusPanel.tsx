import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useMiyaStatus } from '../services/miyaApi';

interface ConnectionItemProps {
  label: string;
  status: 'online' | 'offline' | 'connecting' | 'connected' | 'running' | 'stopped' | 'error';
  color: string;
  text: string;
  pulse: boolean;
}

interface ConnectionStatusPanelProps {
  items?: ConnectionItemProps[];
}

const ConnectionStatusPanel: React.FC<ConnectionStatusPanelProps> = ({ items }) => {
  const { meta, connected, error } = useMiyaStatus();
  const [lastHeartbeat, setLastHeartbeat] = useState(Date.now());

  useEffect(() => {
    if (connected) {
      setLastHeartbeat(Date.now());
    }
  }, [connected]);

  const defaultItems: ConnectionItemProps[] = [
    { 
      label: 'Runtime API', 
      status: connected ? 'running' : 'stopped', 
      color: connected ? 'bg-green-500' : 'bg-red-500', 
      text: connected ? '运行中' : '已停止', 
      pulse: connected 
    },
    { 
      label: 'WebSocket', 
      status: connected ? 'connected' : 'offline', 
      color: connected ? 'bg-green-500' : 'bg-red-500', 
      text: connected ? '已连接' : '未连接', 
      pulse: connected 
    },
    { 
      label: '认知服务', 
      status: connected ? 'running' : 'stopped', 
      color: connected ? 'bg-green-500' : 'bg-red-500', 
      text: connected ? '运行中' : '已停止', 
      pulse: connected 
    },
  ];

  const displayItems = items || defaultItems;
  const allOnline = displayItems.every(item => 
    item.status === 'online' || item.status === 'connected' || item.status === 'running'
  );

  const timeSinceHeartbeat = Math.floor((Date.now() - lastHeartbeat) / 1000);

  return (
    <div className="glass-panel p-4 space-y-3">
      <div className="text-cyan-400 text-xs flex items-center gap-2">
        <motion.span
          className="w-2 h-2 rounded-full"
          animate={{
            backgroundColor: allOnline ? ['#22c55e', '#22c55e', '#22c55e'] : ['#ef4444', '#ef4444', '#ef4444'],
            boxShadow: allOnline ? ['0 0 4px #22c55e', '0 0 8px #22c55e', '0 0 4px #22c55e'] : ['0 0 4px #ef4444', '0 0 8px #ef4444', '0 0 4px #ef4444']
          }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
        连接状态
        <span className="text-gray-600">|</span>
        <motion.span
          className={`text-xs ${allOnline ? 'text-green-400' : 'text-red-400'}`}
          animate={allOnline ? { opacity: [1, 0.5, 1] } : {}}
          transition={{ duration: 1, repeat: Infinity }}
        >
          {allOnline ? '正常' : '异常'}
        </motion.span>
      </div>

      {meta && (
        <div className="text-[10px] text-gray-500 mb-2 p-1 bg-black/10 rounded">
          <div className="flex items-center gap-2">
            <span>Runtime:</span>
            <span className="text-cyan-400">{meta.host}:{meta.port}</span>
            <span className={`px-1 rounded ${meta.enabled ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
              {meta.enabled ? '启用' : '禁用'}
            </span>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {displayItems.map((item) => (
          <div key={item.label} className="flex items-center justify-between p-2 bg-black/20 rounded">
            <div className="flex items-center gap-2">
              <motion.div
                className={`w-2.5 h-2.5 rounded-full ${item.color}`}
                animate={item.pulse ? { scale: [1, 1.3, 1], opacity: [1, 0.7, 1] } : {}}
                transition={{ duration: 1.5, repeat: Infinity }}
              />
              <span className="text-sm text-gray-300">{item.label}</span>
            </div>
            <span className={`text-xs ${item.color} brightness-150`}>{item.text}</span>
          </div>
        ))}
      </div>

      <div className="pt-2 border-t border-cyan-500/10">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500">心跳</span>
          <div className="flex items-center gap-1">
            <motion.div
              className="w-1.5 h-1.5 rounded-full bg-green-500"
              animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
            />
            <span className="text-gray-600">
              {connected ? `${timeSinceHeartbeat}s前` : '--'}
            </span>
          </div>
        </div>
      </div>

      {error && (
        <div className="text-[10px] text-red-400 p-2 bg-red-500/10 rounded">
          {error}
        </div>
      )}
    </div>
  );
};

export default ConnectionStatusPanel;