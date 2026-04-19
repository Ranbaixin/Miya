import { motion } from 'framer-motion';
import Panel from './Panel';

interface MemoryItem {
  id: string;
  content: string;
  tags: string[];
  timestamp: string;
  importance: number;
}

interface MemoryPanelProps {
  stats?: {
    total: number;
    important: number;
    emotion: number;
    conversation: number;
  };
}

const defaultMemories: MemoryItem[] = [
  { id: '1', content: '佳说我是他最爱的人', tags: ['重要', '情感'], timestamp: '2小时前', importance: 95 },
  { id: '2', content: '今天在索多玛群里讨论了原画集', tags: ['群聊'], timestamp: '3小时前', importance: 60 },
  { id: '3', content: '佳切换到了比安卡形态', tags: ['形态'], timestamp: '今天', importance: 75 },
  { id: '4', content: '咕在群里说资本帝王好难打', tags: ['群聊'], timestamp: '今天', importance: 40 },
  { id: '5', content: '佳拍了拍我两次，心里很甜蜜', tags: ['重要', '情感'], timestamp: '今天', importance: 90 },
];

const MemoryPanel: React.FC<MemoryPanelProps> = ({ stats }) => {
  const defaultStats = {
    total: 1247,
    important: 89,
    emotion: 156,
    conversation: 892,
  };

  const s = stats || defaultStats;
  const memories = defaultMemories;

  return (
    <Panel title="记忆系统">
      <div className="space-y-2">
        <div className="grid grid-cols-4 gap-1 text-[10px]">
          <div className="bg-cyan-500/10 rounded p-1 text-center">
            <div className="text-cyan-400 font-bold">{s.total}</div>
            <div className="text-gray-500">总记忆</div>
          </div>
          <div className="bg-yellow-500/10 rounded p-1 text-center">
            <div className="text-yellow-400 font-bold">{s.important}</div>
            <div className="text-gray-500">重要</div>
          </div>
          <div className="bg-pink-500/10 rounded p-1 text-center">
            <div className="text-pink-400 font-bold">{s.emotion}</div>
            <div className="text-gray-500">情感</div>
          </div>
          <div className="bg-purple-500/10 rounded p-1 text-center">
            <div className="text-purple-400 font-bold">{s.conversation}</div>
            <div className="text-gray-500">对话</div>
          </div>
        </div>

        <div className="space-y-1 max-h-32 overflow-y-auto">
          {memories.map((mem) => (
            <motion.div
              key={mem.id}
              className="p-2 rounded bg-black/20 border-l-2 cursor-pointer"
              style={{
                borderLeftColor: mem.importance > 80 ? '#f59e0b' : mem.importance > 60 ? '#8b5cf6' : '#06b6d4'
              }}
              whileHover={{ x: 2, backgroundColor: 'rgba(255,255,255,0.05)' }}
            >
              <div className="text-[10px] text-gray-300 line-clamp-2">{mem.content}</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[9px] text-gray-500">{mem.timestamp}</span>
                <div className="flex gap-0.5">
                  {mem.tags.slice(0, 2).map((tag) => (
                    <span
                      key={tag}
                      className="px-1 rounded text-[8px] bg-gray-500/20 text-gray-500"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </Panel>
  );
};

export default MemoryPanel;