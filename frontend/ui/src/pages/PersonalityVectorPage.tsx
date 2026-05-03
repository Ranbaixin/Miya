import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { miyaAPI } from '../services/miyaApi';

const vectorLabels = {
  logic: { name: '逻辑', color: '#00d4ff' },
  memory: { name: '记忆', color: '#ff6b9d' },
  warmth: { name: '温暖', color: '#ffd93d' },
  empathy: { name: '共情', color: '#c56cf0' },
  resilience: { name: '韧性', color: '#6bcb77' },
  creativity: { name: '创造', color: '#ff8c42' },
};

type VectorKey = keyof typeof vectorLabels;

const PersonalityVectorPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [vectors, setVectors] = useState<Record<VectorKey, number>>({
    logic: 0.75,
    memory: 0.95,
    warmth: 0.85,
    empathy: 0.9,
    resilience: 0.8,
    creativity: 0.8,
  });

  const [selectedVector, setSelectedVector] = useState<VectorKey | null>(null);

  useEffect(() => {
    const loadPersonality = async () => {
      try {
        const data = await miyaAPI.getMiyaStatus();
        if (data?.personality?.vectors) {
          const v = data.personality.vectors;
          setVectors({
            logic: v.logic ?? 0.75,
            memory: v.memory ?? v.warmth ?? 0.95,  // 兼容两种格式
            warmth: v.warmth ?? 0.85,
            empathy: v.empathy ?? 0.9,
            resilience: v.resilience ?? 0.8,
            creativity: v.creativity ?? 0.8,
          });
        }
      } catch (e) {
        console.log('加载人格数据失败，使用默认');
      } finally {
        setLoading(false);
      }
    };
    loadPersonality();
    const interval = setInterval(loadPersonality, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleVectorClick = (key: VectorKey) => {
    setSelectedVector(selectedVector === key ? null : key);
  };

  if (loading) {
    return (
      <div className="p-4 space-y-4">
        <div className="glass-panel p-4 text-center">
          <div className="text-cyan-400">加载中...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      <div className="glass-panel p-4">
        <div className="text-white font-medium mb-4">人格向量雷达图</div>
        
        <div className="relative h-64 flex items-center justify-center">
          <svg viewBox="0 0 300 300" className="w-full h-full">
            {[0.25, 0.5, 0.75, 1].map((ratio, i) => (
              <g key={i}>
                <polygon
                  points={Array.from({ length: 6 }, (_, j) => {
                    const angle = (j * 60 - 90) * (Math.PI / 180);
                    const r = 120 * ratio;
                    const x = 150 + r * Math.cos(angle);
                    const y = 150 + r * Math.sin(angle);
                    return `${x},${y}`;
                  }).join(' ')}
                  fill="none"
                  stroke="rgba(255,255,255,0.1)"
                  strokeWidth="1"
                />
              </g>
            ))}
            
            {Object.entries(vectors).map(([key, value], i) => {
              const label = vectorLabels[key as VectorKey];
              const angle = (i * 60 - 90) * (Math.PI / 180);
              const r = 120 * value;
              const x = 150 + r * Math.cos(angle);
              const y = 150 + r * Math.sin(angle);
              
              const labelR = 140;
              const labelX = 150 + labelR * Math.cos(angle);
              const labelY = 150 + labelR * Math.sin(angle);
              
              return (
                <g key={key}>
                  <line
                    x1="150"
                    y1="150"
                    x2={x}
                    y2={y}
                    stroke={label.color}
                    strokeWidth="2"
                    opacity="0.5"
                  />
                  <circle cx={x} cy={y} r="6" fill={label.color} />
                  <text
                    x={labelX}
                    y={labelY}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="white"
                    fontSize="12"
                  >
                    {label.name}
                  </text>
                  <text
                    x={labelX}
                    y={labelY + 14}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill={label.color}
                    fontSize="10"
                  >
                    {(value * 100).toFixed(0)}%
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      <div className="glass-panel p-4">
        <div className="text-white font-medium mb-3">向量详情</div>
        <div className="space-y-3">
          {Object.entries(vectors).map(([key, value]) => {
            const label = vectorLabels[key as VectorKey];
            return (
              <motion.div
                key={key}
                className="cursor-pointer"
                onClick={() => handleVectorClick(key as VectorKey)}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-gray-300">{label.name}</span>
                  <span style={{ color: label.color }}>{(value * 100).toFixed(0)}%</span>
                </div>
                <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ backgroundColor: label.color }}
                    initial={{ width: 0 }}
                    animate={{ width: `${value * 100}%` }}
                  />
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      <div className="glass-panel p-4">
        <div className="text-white font-medium mb-3">人格特征</div>
        <div className="flex flex-wrap gap-2">
          {Object.entries(vectors).filter(([, v]) => v > 0.8).map(([key, value]) => (
            <span
              key={key}
              className="px-3 py-1 rounded-full text-xs"
              style={{
                backgroundColor: `${vectorLabels[key as VectorKey].color}30`,
                color: vectorLabels[key as VectorKey].color,
                border: `1px solid ${vectorLabels[key as VectorKey].color}50`,
              }}
            >
              {vectorLabels[key as VectorKey].name} +{(value * 100).toFixed(0)}%
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

export default PersonalityVectorPage;