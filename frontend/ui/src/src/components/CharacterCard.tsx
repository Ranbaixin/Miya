import { useState } from 'react';
import { motion } from 'framer-motion';
import Panel from './Panel';

const CharacterCard: React.FC = () => {
  const [status] = useState('在线');
  const [morphology] = useState('比安卡态');

  return (
    <Panel title="AI 角色">
      <div className="relative w-full h-40 flex flex-col items-center justify-center">
        <div className="relative">
          <motion.div
            className="w-24 h-36 rounded-lg overflow-hidden"
            animate={{
              boxShadow: [
                '0 0 20px rgba(0,255,255,0.3)',
                '0 0 35px rgba(0,255,255,0.5)',
                '0 0 20px rgba(0,255,255,0.3)',
              ],
            }}
            transition={{ repeat: Infinity, duration: 3 }}
          >
            <div className="w-full h-full bg-gradient-to-br from-purple-600/30 to-blue-500/30 backdrop-blur-sm flex items-center justify-center">
              <span className="text-cyan-100/60 text-xs">AI 立绘</span>
            </div>
          </motion.div>
          
          <motion.div
            className="absolute inset-0 rounded-lg"
            animate={{ 
              borderColor: ['rgba(0,255,255,0.3)', 'rgba(0,255,255,0.7)', 'rgba(0,255,255,0.3)'],
              scale: [1, 1.02, 1],
            }}
            transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
            style={{ border: '2px solid' }}
          />
          
          <motion.div
            className="absolute -inset-2 rounded-lg"
            animate={{ opacity: [0.3, 0.6, 0.3] }}
            transition={{ repeat: Infinity, duration: 2 }}
            style={{
              background: 'linear-gradient(135deg, rgba(0,255,255,0.1), transparent, rgba(168,85,247,0.1))',
              filter: 'blur(8px)',
            }}
          />
        </div>
        
        <div className="mt-2 text-center">
          <div className="text-cyan-300 text-xs font-bold">{morphology}</div>
          <div className="flex items-center justify-center gap-1 mt-1">
            <motion.div
              className="w-1.5 h-1.5 rounded-full bg-cyan-400"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ repeat: Infinity, duration: 1.5 }}
            />
            <span className="text-[10px] text-gray-500">{status}</span>
          </div>
        </div>
      </div>
    </Panel>
  );
};

export default CharacterCard;