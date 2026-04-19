import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Panel from './Panel';

const ToolLogPanel: React.FC = () => {
  const [apiTime, setApiTime] = useState(65);
  const [dbTime, setDbTime] = useState(12);

  useEffect(() => {
    const timer = setInterval(() => {
      setApiTime(50 + Math.floor(Math.random() * 40));
      setDbTime(5 + Math.floor(Math.random() * 20));
    }, 1500);
    return () => clearInterval(timer);
  }, []);

  return (
    <Panel title="工具调用">
      <div className="space-y-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <motion.div 
              className="w-2 h-2 rounded-full bg-cyan-400"
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ repeat: Infinity, duration: 1 }}
            />
            <span className="text-xs text-gray-400">API 调用</span>
          </div>
          <div className="h-1.5 bg-gray-800/50 rounded-full overflow-hidden">
            <motion.div 
              className="h-full bg-gradient-to-r from-cyan-500 to-cyan-400 rounded-full"
              animate={{ width: `${apiTime}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <div className="text-right text-xs text-cyan-300 mt-0.5 font-mono">
            {apiTime}ms
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-1">
            <motion.div 
              className="w-2 h-2 rounded-full bg-purple-400"
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ repeat: Infinity, duration: 1.2 }}
            />
            <span className="text-xs text-gray-400">数据库</span>
          </div>
          <div className="h-1.5 bg-gray-800/50 rounded-full overflow-hidden">
            <motion.div 
              className="h-full bg-gradient-to-r from-purple-500 to-purple-400 rounded-full"
              animate={{ width: `${dbTime * 3}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <div className="text-right text-xs text-purple-300 mt-0.5 font-mono">
            {dbTime}ms
          </div>
        </div>
      </div>
    </Panel>
  );
};

export default ToolLogPanel;