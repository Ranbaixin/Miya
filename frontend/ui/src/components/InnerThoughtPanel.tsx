import { motion, AnimatePresence } from 'framer-motion';

interface InnerThoughtPanelProps {
  inner_thought: string;
  attribution: string;
  reflection: string;
  visible?: boolean;
}

const InnerThoughtPanel: React.FC<InnerThoughtPanelProps> = ({
  inner_thought,
  attribution,
  reflection,
  visible = true
}) => {
  if (!visible) return null;

  return (
    <div className="bg-black/40 backdrop-blur-sm rounded-xl p-4 border border-white/10">
      <div className="text-xs text-gray-400 mb-3">✦ 内心独白</div>
      
      <AnimatePresence mode="wait">
        <motion.div
          key={inner_thought}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
          className="text-sm text-gray-200 italic mb-4"
        >
          "{inner_thought}"
        </motion.div>
      </AnimatePresence>

      <div className="space-y-2 text-xs">
        <div className="flex items-start gap-2">
          <span className="text-purple-400">→</span>
          <span className="text-gray-400">{attribution}</span>
        </div>
        
        <div className="flex items-start gap-2">
          <span className="text-pink-400">→</span>
          <span className="text-gray-400">{reflection}</span>
        </div>
      </div>
    </div>
  );
};

export default InnerThoughtPanel;