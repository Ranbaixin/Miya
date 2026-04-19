import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Panel from './Panel';

interface VectorPanelProps {
  vectors?: {
    name: string;
    value: number;
    min: number;
    max: number;
    color: string;
  }[];
  form?: string;
}

const VectorPanel: React.FC<VectorPanelProps> = ({ vectors: propVectors, form = 'normal' }) => {
  const defaultVectors = [
    { name: '逻辑', value: 0.75, min: 0.5, max: 1.0, color: '#06b6d4' },
    { name: '记忆', value: 0.95, min: 0.7, max: 1.0, color: '#8b5cf6' },
    { name: '温暖', value: 0.85, min: 0.3, max: 1.0, color: '#f59e0b' },
    { name: '共情', value: 0.90, min: 0.3, max: 1.0, color: '#ec4899' },
    { name: '韧性', value: 0.80, min: 0.3, max: 1.0, color: '#10b981' },
    { name: '创意', value: 0.80, min: 0.3, max: 1.0, color: '#f97316' },
  ];

  const [vectors, setVectors] = useState<VectorPanelProps['vectors']>(propVectors || defaultVectors);

  useEffect(() => {
    if (!propVectors) {
      const timer = setInterval(() => {
        setVectors(prev => prev?.map(v => ({
          ...v,
          value: Math.max(v.min, Math.min(v.max, v.value + (Math.random() - 0.5) * 0.02))
        })) || []);
      }, 3000);
      return () => clearInterval(timer);
    }
  }, [propVectors]);

  const title = '你';

  return (
    <Panel title="人格向量">
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-[10px]">
          <span className="text-gray-500">形态:</span>
          <span className="text-purple-400 px-2 py-0.5 rounded bg-purple-500/20">{form}</span>
          <span className="text-gray-500 ml-2">称呼:</span>
          <span className="text-cyan-400">{title}</span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {(vectors || defaultVectors).map((vec) => (
            <div key={vec.name} className="space-y-1">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-gray-400">{vec.name}</span>
                <span className="font-mono" style={{ color: vec.color }}>
                  {(vec.value * 100).toFixed(0)}%
                </span>
              </div>
              <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: vec.color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${(vec.value / vec.max) * 100}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
};

export default VectorPanel;