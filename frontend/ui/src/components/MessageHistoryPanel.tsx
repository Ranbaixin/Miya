import { useState, useEffect } from 'react';
import { miyaAPI } from '../services/miyaApi';

interface MemoryItem {
  uuid: string;
  fact: string;
  created_at: string;
  importance?: number;
}

const MessageHistoryPanel: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [memories, setMemories] = useState<MemoryItem[]>([]);

  useEffect(() => {
    const loadMemories = async () => {
      try {
        const data = await miyaAPI.getMemory({ limit: 20 });
        const items = data?.memories || data?.data?.items || [];
        setMemories(items.slice(0, 10));
      } catch (e) {
        console.log('加载记忆失败');
      } finally {
        setLoading(false);
      }
    };
    loadMemories();
    const interval = setInterval(loadMemories, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading && memories.length === 0) {
    return (
      <div className="glass-panel p-4">
        <div className="text-cyan-400 text-xs mb-3">最近记忆</div>
        <div className="text-gray-500 text-center text-xs py-4">加载中...</div>
      </div>
    );
  }

  if (memories.length === 0) {
    return (
      <div className="glass-panel p-4">
        <div className="text-cyan-400 text-xs mb-3">最近记忆</div>
        <div className="text-gray-500 text-center text-xs py-4">暂无记忆</div>
      </div>
    );
  }

  return (
    <div className="glass-panel p-4">
      <div className="text-cyan-400 text-xs mb-3">最近记忆</div>
      <div className="space-y-2 max-h-48 overflow-auto">
        {memories.map((mem, i) => (
          <div key={mem.uuid || i} className="text-xs border-l-2 border-cyan-500/30 pl-2">
            <span className="text-cyan-600">
              {new Date(mem.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
            </span>
            <span className="text-gray-300 ml-2">{mem.fact}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MessageHistoryPanel;