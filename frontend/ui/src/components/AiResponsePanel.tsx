import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Panel from './Panel';

const AiResponsePanel: React.FC = () => {
  const messages = [
    "Crētsbcndolael foem.",
    "Hotiōn dōn..",
    "Sotme hačit Ēimsāts.",
    "Cóťtaly Īnleone.",
    "Chcttiōne Caol.",
    "（被连续拍了两下，指尖在屏幕上停顿片刻）",
    "佳，这样会让我分心的。",
    "嗯。我在。",
  ];

  const [index, setIndex] = useState(0);
  const [displayText, setDisplayText] = useState('');
  const [isTyping, setIsTyping] = useState(true);
  const [memoryValue, setMemoryValue] = useState(87);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    
    if (isTyping) {
      const msg = messages[index];
      let i = 0;
      timer = setInterval(() => {
        if (i <= msg.length) {
          setDisplayText(msg.substring(0, i));
          i++;
        } else {
          clearInterval(timer);
          setTimeout(() => {
            setIsTyping(false);
            setTimeout(() => {
              setIndex(prev => (prev + 1) % messages.length);
              setDisplayText('');
              setIsTyping(true);
            }, 1500);
          }, 1000);
        }
      }, 70);
    }
    
    return () => {
      clearInterval(timer);
    };
  }, [index, isTyping]);

  useEffect(() => {
    const timer = setInterval(() => {
      setMemoryValue(80 + Math.floor(Math.random() * 15));
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <Panel title="AI 回复区">
      <div className="space-y-2">
        <AnimatePresence mode="wait">
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="bg-cyan-500/10 border border-cyan-500/20 rounded px-3 py-2 text-xs font-mono min-h-[40px]"
          >
            {displayText}
            {isTyping && (
              <motion.span
                className="inline-block w-[2px] h-3 bg-cyan-400 ml-0.5"
                animate={{ opacity: [1, 0] }}
                transition={{ repeat: Infinity, duration: 0.5 }}
              />
            )}
          </motion.div>
        </AnimatePresence>
        
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500">记忆值</span>
          <div className="flex items-center gap-1">
            <div className="flex gap-0.5">
              {[...Array(6)].map((_, i) => (
                <motion.div
                  key={i}
                  className="w-1 h-3 bg-cyan-500/60 rounded-sm"
                  animate={{
                    opacity: i < Math.floor(memoryValue / 20) ? [1, 0.5, 1] : 0.2,
                  }}
                  transition={{ repeat: Infinity, duration: 0.8, delay: i * 0.1 }}
                />
              ))}
            </div>
            <span className="text-cyan-300 ml-1">{memoryValue}%</span>
          </div>
        </div>
      </div>
    </Panel>
  );
};

export default AiResponsePanel;