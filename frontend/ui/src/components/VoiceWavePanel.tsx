import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import Panel from './Panel';

const VoiceWavePanel: React.FC = () => {
  const [bars, setBars] = useState<number[]>(Array(16).fill(20));
  const [isActive] = useState(true);

  const updateBars = useCallback(() => {
    if (!isActive) {
      setBars(Array(16).fill(10));
      return;
    }
    setBars(prev => prev.map((_, i) => {
      const center = 7;
      const distance = Math.abs(i - center);
      const baseHeight = 60 - distance * 6;
      const variation = Math.random() * 40;
      return Math.max(8, Math.min(95, baseHeight + variation));
    }));
  }, [isActive]);

  useEffect(() => {
    const interval = setInterval(updateBars, 100);
    return () => clearInterval(interval);
  }, [updateBars]);

  return (
    <Panel title="语音律动">
      <div className="relative h-16 flex items-end justify-center gap-[2px]">
        {bars.map((h, i) => (
          <motion.div
            key={i}
            className="w-1.5 rounded-t-full"
            animate={{ height: `${h}%` }}
            transition={{ duration: 0.08, ease: 'linear' }}
            style={{
              background: i >= 6 && i <= 9 
                ? 'linear-gradient(to top, rgba(0,255,255,0.9), rgba(168,85,247,0.6))'
                : 'linear-gradient(to top, rgba(0,255,255,0.7), rgba(0,255,255,0.3))',
              boxShadow: i >= 6 && i <= 9 
                ? '0 0 8px rgba(0,255,255,0.5)' 
                : 'none',
            }}
          />
        ))}
        <div className="absolute -bottom-1 left-0 right-0 flex justify-center">
          <span className="text-[8px] text-cyan-100/40">
            {isActive ? '● 监听中' : '○ 待机'}
          </span>
        </div>
      </div>
    </Panel>
  );
};

export default VoiceWavePanel;