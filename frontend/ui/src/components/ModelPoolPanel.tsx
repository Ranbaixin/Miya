import { useState } from 'react';
import { motion } from 'framer-motion';
import Panel from './Panel';

interface ModelInfo {
  name: string;
  provider: string;
  status: 'active' | 'idle' | 'error';
  tokens: number;
}

const ModelPoolPanel: React.FC = () => {
  const [currentActive, setCurrentActive] = useState('deepseek-chat');
  
  const models: ModelInfo[] = [
    { name: 'deepseek-chat', provider: 'DeepSeek', status: 'active', tokens: 12450 },
    { name: 'deepseek-reasoner', provider: 'DeepSeek', status: 'idle', tokens: 3200 },
    { name: 'Qwen2.5-72B', provider: 'SiliconFlow', status: 'idle', tokens: 8900 },
    { name: 'Kimi-K2.6', provider: 'SiliconFlow', status: 'idle', tokens: 2100 },
    { name: 'Llama-3.1-8B', provider: 'SiliconFlow', status: 'idle', tokens: 1500 },
    { name: 'bge-large-zh', provider: 'SiliconFlow', status: 'idle', tokens: 0 },
  ];

  const statusColors = {
    active: 'bg-green-500',
    idle: 'bg-gray-500',
    error: 'bg-red-500',
  };

  return (
    <Panel title="模型池 (13)">
      <div className="space-y-2">
        <div className="flex items-center justify-between text-[10px]">
          <span className="text-gray-500">当前模型</span>
          <span className="text-cyan-400 font-mono">{currentActive}</span>
        </div>

        <div className="space-y-1">
          {models.map((model) => (
            <motion.div
              key={model.name}
              className={`p-2 rounded cursor-pointer transition-colors ${
                model.name === currentActive ? 'bg-cyan-500/20 border border-cyan-500/30' : 'bg-black/20'
              }`}
              whileHover={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
              onClick={() => setCurrentActive(model.name)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-1.5 h-1.5 rounded-full ${statusColors[model.status]}`} />
                  <span className="text-[10px] text-gray-300 truncate max-w-[100px]">{model.name}</span>
                </div>
                <div className="text-[9px] text-gray-500">{model.provider}</div>
              </div>
              {model.tokens > 0 && (
                <div className="mt-1 h-1 bg-gray-800 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-cyan-500 to-purple-500"
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(model.tokens / 200, 100)}%` }}
                  />
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </Panel>
  );
};

export default ModelPoolPanel;