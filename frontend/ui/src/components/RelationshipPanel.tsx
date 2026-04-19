import { motion } from 'framer-motion';

interface RelationshipPanelProps {
  relationship: {
    love: number;
    attachment: number;
    crush: number;
  };
}

const RelationshipPanel: React.FC<RelationshipPanelProps> = ({ relationship }) => {
  const stats = [
    { key: 'love', label: '爱意', emoji: '❤️', value: relationship.love },
    { key: 'attachment', label: '依恋', emoji: '💕', value: relationship.attachment },
    { key: 'crush', label: '心动', emoji: '💗', value: relationship.crush },
  ];

  return (
    <div className="bg-black/40 backdrop-blur-sm rounded-xl p-4 border border-white/10">
      <div className="text-xs text-gray-400 mb-3">♥ 关系数值</div>
      
      <div className="grid grid-cols-3 gap-2">
        {stats.map((stat) => (
          <div key={stat.key} className="text-center">
            <motion.div
              className="text-lg mb-1"
              animate={{
                scale: [1, 1.1, 1],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            >
              {stat.emoji}
            </motion.div>
            <div className="text-xs text-gray-400">{stat.label}</div>
            <div className="text-sm font-bold text-white">
              {stat.value}
            </div>
            <div className="w-full progress-bar-track rounded-full h-1 mt-1">
              <motion.div
                className="h-full rounded-full progress-bar-fill"
                initial={{ width: 0 }}
                animate={{ width: `${stat.value}%` }}
                transition={{ duration: 1, delay: 0.2 }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RelationshipPanel;