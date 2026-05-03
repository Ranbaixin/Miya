import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { miyaAPI, useMiyaMemory } from '../services/miyaApi';

interface EmotionData {
  current: {
    joy: number;
    sadness: number;
    anger: number;
    fear: number;
    surprise: number;
    disgust: number;
  };
  dominant: string;
  intensity: number;
}

const emotions = [
  { name: 'joy', color: '#ffd700', label: '喜悦', icon: '😊' },
  { name: 'sadness', color: '#4169e1', label: '悲伤', icon: '😢' },
  { name: 'anger', color: '#ff4500', label: '愤怒', icon: '😠' },
  { name: 'fear', color: '#9932cc', label: '恐惧', icon: '😨' },
  { name: 'surprise', color: '#00ced1', label: '惊喜', icon: '😲' },
  { name: 'disgust', color: '#32cd32', label: '厌恶', icon: '🤢' },
];

const SoulPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [emotionData, setEmotionData] = useState<EmotionData>({
    current: { joy: 0.5, sadness: 0.2, anger: 0.1, fear: 0.1, surprise: 0.3, disgust: 0.05 },
    dominant: 'joy',
    intensity: 0.5,
  });

  const [emotionHistory, setEmotionHistory] = useState<Array<{emotion: string; intensity: number; time: string}>>([
    { emotion: 'joy', intensity: 0.5, time: '14:30' },
    { emotion: 'joy', intensity: 0.6, time: '14:25' },
    { emotion: 'surprise', intensity: 0.3, time: '14:20' },
    { emotion: 'joy', intensity: 0.4, time: '14:15' },
  ]);

  useEffect(() => {
    const loadEmotion = async () => {
      try {
        const data = await miyaAPI.getEmotionPool();
        if (data) {
          setEmotionData({
            current: data.current || data,
            dominant: data.dominant || 'joy',
            intensity: data.intensity || 0.5,
          });
        }
      } catch (e) {
        console.log('加载情绪数据失败，使用默认');
      } finally {
        setLoading(false);
      }
    };
    loadEmotion();
    const interval = setInterval(loadEmotion, 5000);
    return () => clearInterval(interval);
  }, []);

  const currentEmotionData = emotions.find(e => e.name === emotionData.dominant) || emotions[0];

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
        <div className="flex items-center gap-3 mb-4">
          <span className="text-3xl">{currentEmotionData.icon}</span>
          <div>
            <div className="text-white font-medium text-lg">{currentEmotionData.label}</div>
            <div className="text-gray-400 text-sm">当前情绪状态</div>
          </div>
        </div>

        <div className="mb-4">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">情绪强度</span>
            <span className="text-cyan-400">{(emotionData.intensity * 100).toFixed(0)}%</span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ backgroundColor: currentEmotionData.color }}
              initial={{ width: 0 }}
              animate={{ width: `${emotionData.intensity * 100}%` }}
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {Object.entries(emotionData.current).map(([key, value]) => (
            <span
              key={key}
              className="px-2 py-1 bg-gray-800/50 rounded-full text-xs text-gray-300"
            >
              {emotions.find(e => e.name === key)?.label || key}: {(value as number * 100).toFixed(0)}%
            </span>
          ))}
        </div>
      </div>

      <div className="glass-panel p-4">
        <div className="text-white font-medium mb-3">情绪池</div>
        <div className="grid grid-cols-3 gap-3">
          {emotions.map(emotion => {
            const value = (emotionData.current as Record<string, number>)[emotion.name] || 0;
            return (
              <motion.button
                key={emotion.name}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`p-3 rounded-lg text-center transition-all ${
                  emotionData.dominant === emotion.name
                    ? 'bg-gray-700/50 border-2'
                    : 'bg-gray-800/30 border border-gray-700/30 hover:border-gray-600'
                }`}
                style={{
                  borderColor: emotionData.dominant === emotion.name ? emotion.color : undefined,
                }}
              >
                <div className="text-xl mb-1">{emotion.icon}</div>
                <div className="text-xs text-gray-400">{emotion.label}</div>
                <div className="text-xs text-cyan-400">{(value * 100).toFixed(0)}%</div>
              </motion.button>
            );
          })}
        </div>
      </div>

      <div className="glass-panel p-4">
        <div className="text-white font-medium mb-3">情绪轨迹</div>
        <div className="space-y-2">
          {emotionHistory.map((h, i) => {
            const e = emotions.find(em => em.name === h.emotion) || emotions[0];
            return (
              <div key={i} className="flex items-center gap-2">
                <span className="text-sm text-gray-500 w-12">{h.time}</span>
                <div
                  className="h-3 rounded-full"
                  style={{
                    width: `${h.intensity * 100}%`,
                    backgroundColor: e.color,
                    opacity: 0.3 + h.intensity * 0.7,
                  }}
                />
                <span className="text-xs text-gray-400">{e.label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default SoulPage;