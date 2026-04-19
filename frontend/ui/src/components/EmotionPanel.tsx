import { motion } from 'framer-motion';
import type { PersonalityData, RelationshipData } from '../hooks/useMiyaQQData';

interface EmotionPanelProps {
  data: {
    personality: {
      emotion: PersonalityData['emotion'];
      relationship: RelationshipData;
    };
    getEmotionColor: (emotion: string) => string;
  };
}

const EmotionPanel: React.FC<EmotionPanelProps> = ({ data }) => {
  const { personality, getEmotionColor } = data;
  const { emotion } = personality;

  return (
    <div className="bg-black/40 backdrop-blur-sm rounded-xl p-4 border border-white/10">
      <div className="text-xs text-gray-400 mb-2">当前情绪</div>
      
      <motion.div
        className="text-2xl font-bold mb-2"
        style={{ color: getEmotionColor(emotion.dominant_emotion) }}
        animate={{
          scale: [1, 1.05, 1],
          opacity: [0.8, 1, 0.8]
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      >
        {emotion.dominant_emotion}
      </motion.div>

      <div className="w-full progress-bar-track rounded-full h-2 mb-3">
        <motion.div
          className="h-full rounded-full progress-bar-fill"
          initial={{ width: 0 }}
          animate={{ width: `${emotion.intensity}%` }}
          transition={{ duration: 1 }}
        />
      </div>

      <div className="text-xs text-gray-400">
        {emotion.intensity}%
      </div>

      <div className="flex flex-wrap gap-1 mt-3">
        {emotion.emotion_tags.map((tag: string, i: number) => (
          <span
            key={i}
            className="text-xs px-2 py-0.5 rounded-full bg-white/10 text-gray-300"
          >
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
};

export default EmotionPanel;