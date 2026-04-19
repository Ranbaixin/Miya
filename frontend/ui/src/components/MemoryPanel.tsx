import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useMiyaMemory, type MemoryItem } from '../services/miyaApi';

interface MemoryPanelProps {
  onAddMemory?: (content: string) => Promise<any>;
  onDeleteMemory?: (uuid: string) => Promise<any>;
}

const MemoryPanel: React.FC<MemoryPanelProps> = ({ 
  onAddMemory, 
  onDeleteMemory 
}) => {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newMemory, setNewMemory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const [selectedTab, setSelectedTab] = useState<'all' | 'important' | 'emotion'>('all');

  const { memories, loading, refresh, add, remove, stats } = useMiyaMemory();

  const defaultMemories: MemoryItem[] = [
    { uuid: '1', fact: '佳说我是他最爱的人', created_at: '2小时前' },
    { uuid: '2', fact: '今天在索多玛群里讨论了原画集', created_at: '3小时前' },
    { uuid: '3', fact: '佳切换到了比安卡形态', created_at: '今天' },
    { uuid: '4', fact: '咕在群里说资本帝王好难打', created_at: '今天' },
    { uuid: '5', fact: '佳拍了拍我两次，心里很甜蜜', created_at: '今天' },
  ];

  const displayMemories = memories.length > 0 ? memories : defaultMemories;

  const filteredMemories = displayMemories.filter(mem => {
    if (selectedTab === 'all') return true;
    if (searchQuery) {
      return mem.fact.toLowerCase().includes(searchQuery.toLowerCase());
    }
    return true;
  });

  const handleAddMemory = async () => {
    if (!newMemory.trim()) return;
    await add(newMemory);
    setNewMemory('');
    setShowAddModal(false);
  };

  const handleDeleteMemory = async (uuid: string) => {
    if (confirm('确定要删除这条记忆吗？')) {
      await remove(uuid);
    }
  };

  const getImportanceColor = (importance: number) => {
    if (importance > 80) return '#f59e0b';
    if (importance > 60) return '#8b5cf6';
    return '#06b6d4';
  };

  return (
    <div className="glass-panel p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="text-cyan-400 text-xs font-bold">记忆系统</div>
        <div className="flex gap-1">
          <button
            onClick={() => setShowAddModal(true)}
            className="px-2 py-0.5 text-xs rounded bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 transition-colors"
          >
            + 添加
          </button>
          <button
            onClick={() => setShowSearch(!showSearch)}
            className="px-2 py-0.5 text-xs rounded bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 transition-colors"
          >
            搜索
          </button>
          <button
            onClick={() => refresh()}
            className="px-2 py-0.5 text-xs rounded bg-gray-500/20 text-gray-400 hover:bg-gray-500/30 transition-colors"
          >
            刷新
          </button>
        </div>
      </div>

      {showSearch && (
        <div className="mb-2 p-2 bg-black/20 rounded">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索记忆..."
            className="w-full bg-transparent text-xs text-gray-300 outline-none placeholder-gray-600"
          />
        </div>
      )}

      <div className="flex gap-1 mb-2 text-[10px]">
        {(['all', 'important', 'emotion'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setSelectedTab(tab)}
            className={`flex-1 py-1 rounded text-center transition-colors ${
              selectedTab === tab 
                ? 'bg-cyan-500/30 text-cyan-400' 
                : 'bg-black/20 text-gray-500 hover:text-gray-400'
            }`}
          >
            {tab === 'all' ? '全部' : tab === 'important' ? '重要' : '情感'}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-4 gap-1 text-[10px] mb-2">
        <div className="bg-cyan-500/10 rounded p-1 text-center">
          <div className="text-cyan-400 font-bold">{stats.total || displayMemories.length}</div>
          <div className="text-gray-500">总记忆</div>
        </div>
        <div className="bg-yellow-500/10 rounded p-1 text-center">
          <div className="text-yellow-400 font-bold">{stats.important}</div>
          <div className="text-gray-500">重要</div>
        </div>
        <div className="bg-pink-500/10 rounded p-1 text-center">
          <div className="text-pink-400 font-bold">{stats.emotion}</div>
          <div className="text-gray-500">情感</div>
        </div>
        <div className="bg-purple-500/10 rounded p-1 text-center">
          <div className="text-purple-400 font-bold">{stats.conversation}</div>
          <div className="text-gray-500">对话</div>
        </div>
      </div>

      <div className="space-y-1 max-h-40 overflow-y-auto">
        {loading ? (
          <div className="text-center text-xs text-gray-500 py-4">加载中...</div>
        ) : filteredMemories.length === 0 ? (
          <div className="text-center text-xs text-gray-500 py-4">暂无记忆</div>
        ) : (
          filteredMemories.map((mem, idx) => (
            <motion.div
              key={mem.uuid}
              className="p-2 rounded bg-black/20 border-l-2 cursor-pointer group"
              style={{
                borderLeftColor: getImportanceColor(60 + idx * 10)
              }}
              whileHover={{ x: 2, backgroundColor: 'rgba(255,255,255,0.05)' }}
            >
              <div className="text-[10px] text-gray-300 line-clamp-2">{mem.fact}</div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-[9px] text-gray-500">{mem.created_at}</span>
                <button
                  onClick={() => handleDeleteMemory(mem.uuid)}
                  className="opacity-0 group-hover:opacity-100 text-[9px] text-red-400 hover:text-red-300 transition-opacity"
                >
                  删除
                </button>
              </div>
            </motion.div>
          ))
        )}
      </div>

      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <motion.div 
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="glass-panel p-4 w-80"
          >
            <div className="text-white text-sm mb-3 font-bold">添加新记忆</div>
            <textarea
              value={newMemory}
              onChange={(e) => setNewMemory(e.target.value)}
              placeholder="输入记忆内容..."
              className="w-full h-20 bg-black/20 rounded p-2 text-xs text-gray-300 outline-none resize-none placeholder-gray-600"
            />
            <div className="flex gap-2 mt-3">
              <button
                onClick={handleAddMemory}
                disabled={!newMemory.trim()}
                className="flex-1 py-1.5 text-xs rounded bg-cyan-500/30 text-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-cyan-500/40 transition-colors"
              >
                保存
              </button>
              <button
                onClick={() => setShowAddModal(false)}
                className="py-1.5 px-3 text-xs rounded bg-gray-500/20 text-gray-400 hover:bg-gray-500/30 transition-colors"
              >
                取消
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default MemoryPanel;