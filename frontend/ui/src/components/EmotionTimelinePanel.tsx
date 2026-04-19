import { motion } from 'framer-motion';
import { useState } from 'react';

interface EmotionHistory {
  time: string;
  emotion: string;
  intensity: number;
}

const EmotionTimelinePanel: React.FC = () => {
  const [history] = useState<EmotionHistory[]>([
    { time: '15:31', emotion: '依恋', intensity: 85 },
    { time: '15:29', emotion: '保护欲', intensity: 75 },
    { time: '15:28', emotion: '羞耻', intensity: 75 },
    { time: '15:20', emotion: '释然', intensity: 65 },
    { time: '15:18', emotion: '保护欲', intensity: 85 },
  ]);

  return (
    <div className="glass-panel p-4">
      <div className="text-cyan-400 text-xs mb-3">情感时间线</div>
      <div className="space-y-2">
        {history.map((item, i) => (
          <motion.div
            key={i}
            className="flex items-center gap-2"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <span className="text-cyan-600 text-xs w-10">{item.time}</span>
            <div className="flex-1 h-1.5 rounded-full bg-cyan-900/30 overflow-hidden">
              <motion.div
                className="h-full rounded-full progress-bar-fill"
                initial={{ width: 0 }}
                animate={{ width: `${item.intensity}%` }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
              />
            </div>
            <span className="text-gray-300 text-xs w-16">{item.emotion}</span>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default EmotionTimelinePanel;