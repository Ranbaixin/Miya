import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Panel from './Panel';

interface EmotionData {
  trust: number;
  anxiety: number;
  joy: number;
  sadness: number;
  dominant: string;
  intensity: number;
}

const emotionConfig: Record<string, { color: string; glow: string; icon: string }> = {
  '心动': { color: 'bg-rose-400', glow: 'rgba(255,100,150,0.5)', icon: '💕' },
  '甜蜜': { color: 'bg-pink-300', glow: 'rgba(255,182,193,0.5)', icon: '✨' },
  '依恋': { color: 'bg-purple-400', glow: 'rgba(147,112,219,0.5)', icon: '💜' },
  '温暖': { color: 'bg-amber-400', glow: 'rgba(255,200,100,0.5)', icon: '☀️' },
  '平静': { color: 'bg-cyan-400', glow: 'rgba(0,255,255,0.5)', icon: '🌊' },
  '焦虑': { color: 'bg-orange-400', glow: 'rgba(255,165,0,0.5)', icon: '⚡' },
  '悲伤': { color: 'bg-blue-400', glow: 'rgba(100,149,237,0.5)', icon: '💧' },
  '愉悦': { color: 'bg-yellow-400', glow: 'rgba(255,255,100,0.5)', icon: '🎵' },
};

const PsychologicalPanel: React.FC = () => {
  const [emotions, setEmotions] = useState<EmotionData>({
    trust: 68,
    anxiety: 32,
    joy: 75,
    sadness: 15,
    dominant: '愉悦',
    intensity: 75,
  });

  const config = emotionConfig[emotions.dominant] || emotionConfig['平静'];

  useEffect(() => {
    const timer = setInterval(() => {
      const dominantOptions = ['心动', '甜蜜', '依恋', '温暖', '平静', '愉悦'];
      const randomDominant = dominantOptions[Math.floor(Math.random() * dominantOptions.length)];
      
      setEmotions({
        trust: Math.min(100, Math.max(0, 68 + (Math.random() - 0.5) * 10)),
        anxiety: Math.min(100, Math.max(0, 32 + (Math.random() - 0.5) * 8)),
        joy: Math.min(100, Math.max(0, 75 + (Math.random() - 0.5) * 12)),
        sadness: Math.min(100, Math.max(0, 15 + (Math.random() - 0.5) * 5)),
        dominant: randomDominant,
        intensity: Math.floor(Math.random() * 40 + 60),
      });
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  const emotionList = [
    { key: 'trust', label: '信任', color: 'bg-cyan-400', value: emotions.trust },
    { key: 'anxiety', label: '焦虑', color: 'bg-purple-400', value: emotions.anxiety },
    { key: 'joy', label: '愉悦', color: 'bg-yellow-400', value: emotions.joy },
    { key: 'sadness', label: '悲伤', color: 'bg-blue-400', value: emotions.sadness },
  ];

  return (
    <Panel title="心理历程">
      <div className="flex flex-col items-center">
        <div className="relative w-20 h-20 mb-3">
          <AnimatePresence mode="wait">
            <motion.div
              key={emotions.dominant}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 1.2, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0 rounded-full"
              style={{
                background: `radial-gradient(circle, ${config.glow} 0%, transparent 70%)`,
                boxShadow: `0 0 20px ${config.glow}`,
              }}
            />
          </AnimatePresence>
          
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-cyan-400/30"
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ repeat: Infinity, duration: 2 }}
          />
          <motion.div
            className="absolute inset-2 rounded-full border-2 border-cyan-400/50"
            animate={{ scale: [1, 1.05, 1] }}
            transition={{ repeat: Infinity, duration: 2, delay: 0.3 }}
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <motion.div
              className="w-12 h-12 rounded-full bg-gradient-to-br from-cyan-500/20 to-purple-500/20"
              animate={{ 
                boxShadow: [
                  `0 0 15px ${config.glow}`,
                  `0 0 30px ${config.glow}`,
                  `0 0 15px ${config.glow}`,
                ]
              }}
              transition={{ repeat: Infinity, duration: 2 }}
            />
          </div>
          <div className="absolute inset-0 flex items-center justify-center">
            <motion.span 
              className="text-lg"
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ repeat: Infinity, duration: 1.5 }}
            >
              {config.icon}
            </motion.span>
          </div>
        </div>
        
        <AnimatePresence mode="wait">
          <motion.div
            key={emotions.dominant}
            initial={{ y: -10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 10, opacity: 0 }}
            className="text-center mb-2"
          >
            <motion.span
              className="text-cyan-300 text-sm font-bold"
              style={{ color: config.glow.replace('0.5', '1') }}
            >
              {emotions.dominant}
            </motion.span>
            <motion.span
              className="text-gray-500 text-xs ml-2"
              animate={{ opacity: [0.5, 1, 0.5] }}
            >
              {emotions.intensity}%
            </motion.span>
          </motion.div>
        </AnimatePresence>
        
        <div className="w-full space-y-2">
          {emotionList.map((emotion) => (
            <div key={emotion.key} className="flex items-center gap-2">
              <span className="w-10 text-xs text-gray-400">{emotion.label}</span>
              <div className="flex-1 h-1.5 bg-gray-800/50 rounded-full overflow-hidden">
                <motion.div
                  className={`h-full ${emotion.color} rounded-full`}
                  initial={{ width: 0 }}
                  animate={{ width: `${emotion.value}%` }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                />
              </div>
              <span className="w-8 text-right text-xs text-cyan-300">
                {Math.round(emotion.value)}%
              </span>
            </div>
          ))}
        </div>

        <motion.div
          className="absolute -bottom-1 left-1/2 -translate-x-1/2"
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.3, 0.6, 0.3],
          }}
          transition={{ repeat: Infinity, duration: 2 }}
        >
          <svg width="40" height="20" viewBox="0 0 40 20" fill="none">
            <path
              d="M20 18L8 8C4 4 4 0 8 0C12 0 16 4 20 8C24 4 28 0 32 0C36 0 36 4 32 8L20 18Z"
              fill={config.glow}
              opacity="0.3"
            />
          </svg>
        </motion.div>
      </div>
    </Panel>
  );
};

export default PsychologicalPanel;