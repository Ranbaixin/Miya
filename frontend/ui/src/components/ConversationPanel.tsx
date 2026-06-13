import { useState } from 'react';
import { motion } from 'framer-motion';
import Panel from './Panel';

interface ChatMessage {
  id: string;
  sender: string;
  content: string;
  time: string;
  type: 'user' | 'miya';
}

const ConversationPanel: React.FC = () => {
  const [messages] = useState<ChatMessage[]>([
    { id: '1', sender: '然鑫', content: '/形态 bianka', time: '20:06', type: 'user' },
    { id: '2', sender: '弥娅', content: '已切换到形态: bianka', time: '20:06', type: 'miya' },
    { id: '3', sender: '然鑫', content: '（拍了拍你）', time: '20:06', type: 'user' },
    { id: '4', sender: '弥娅', content: '（被连续拍了两下，指尖在屏幕上停顿片刻）然鑫，这样会让我分心的。', time: '20:06', type: 'miya' },
    { id: '5', sender: '然鑫', content: '资本帝王好难打喵', time: '20:10', type: 'user' },
    { id: '6', sender: '咕', content: '那就不能白嫖原画集了喵', time: '20:11', type: 'user' },
  ]);

  return (
    <Panel title="对话历史">
      <div className="space-y-1 max-h-40 overflow-y-auto">
        {messages.map((msg, idx) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
            className={`p-1.5 rounded text-[10px] ${
              msg.type === 'miya'
                ? 'bg-cyan-500/10 border-l-2 border-cyan-500'
                : 'bg-purple-500/10 border-l-2 border-purple-500'
            }`}
          >
            <div className="flex items-center gap-1 mb-0.5">
              <span className={msg.type === 'miya' ? 'text-cyan-400' : 'text-purple-400'}>
                {msg.sender}
              </span>
              <span className="text-gray-600 text-[9px]">{msg.time}</span>
            </div>
            <div className="text-gray-300 line-clamp-2">{msg.content}</div>
          </motion.div>
        ))}
      </div>
    </Panel>
  );
};

export default ConversationPanel;