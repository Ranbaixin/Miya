import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { miyaAPI } from '../services/miyaApi';
import type { KnowledgeBaseInfo } from '../services/miyaApi';

const KnowledgeBasePage: React.FC = () => {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBaseInfo[]>([]);
  const [selectedKB, setSelectedKB] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newKBName, setNewKBName] = useState('');
  const [newKBDesc, setNewKBDesc] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const loadKBs = useCallback(async () => {
    setLoading(true);
    const data = await miyaAPI.getKnowledgeBases();
    if (data) setKnowledgeBases(data);
    setLoading(false);
  }, []);

  useEffect(() => { loadKBs(); }, [loadKBs]);

  const handleCreate = async () => {
    if (!newKBName.trim()) return;
    setActionLoading(true);
    const result = await miyaAPI.createKnowledgeBase(newKBName, newKBDesc);
    if (result) {
      setKnowledgeBases(prev => [...prev, result]);
      setNewKBName('');
      setNewKBDesc('');
      setShowCreate(false);
    }
    setActionLoading(false);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除这个知识库吗？')) return;
    setKnowledgeBases(prev => prev.filter(kb => kb.id !== id));
  };

  return (
    <div className="p-4 space-y-4">
      <div className="glass-panel p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="text-white font-medium">知识库列表</div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadKBs}
              className="px-3 py-1 text-xs rounded bg-cyan-500/20 text-cyan-400"
            >
              刷新
            </button>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowCreate(!showCreate)}
              className="px-3 py-1 bg-cyan-500/30 border border-cyan-500/50 rounded-lg text-cyan-400 text-sm"
            >
              + 新建知识库
            </motion.button>
          </div>
        </div>

        {showCreate && (
          <div className="mb-4 p-3 bg-gray-800/30 rounded-lg space-y-2">
            <input
              type="text"
              placeholder="知识库名称"
              value={newKBName}
              onChange={(e) => setNewKBName(e.target.value)}
              className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
            />
            <input
              type="text"
              placeholder="描述（可选）"
              value={newKBDesc}
              onChange={(e) => setNewKBDesc(e.target.value)}
              className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
            />
            <div className="flex gap-2">
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={handleCreate}
                disabled={actionLoading}
                className="flex-1 py-2 bg-cyan-500/30 border border-cyan-500/50 rounded-lg text-cyan-400 text-sm disabled:opacity-50"
              >
                {actionLoading ? '创建中...' : '创建'}
              </motion.button>
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowCreate(false)}
                className="flex-1 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-400 text-sm"
              >
                取消
              </motion.button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="text-center py-8 text-gray-500">加载中...</div>
        ) : (
          <div className="space-y-2">
            {knowledgeBases.map(kb => (
              <motion.div
                key={kb.id}
                layout
                className={`p-3 bg-gray-800/30 rounded-lg cursor-pointer ${
                  selectedKB === kb.id ? 'border border-cyan-500/50' : ''
                }`}
                onClick={() => setSelectedKB(selectedKB === kb.id ? null : kb.id)}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-white font-medium">{kb.name}</div>
                    <div className="text-gray-400 text-sm">{kb.description}</div>
                    <div className="text-gray-500 text-xs mt-1">
                      {kb.document_count} 个文档 · {kb.updated_at?.slice(0, 10)}
                    </div>
                  </div>
                  <motion.button
                    whileTap={{ scale: 0.9 }}
                    onClick={(e) => { e.stopPropagation(); handleDelete(kb.id); }}
                    className="w-8 h-8 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/40 flex items-center justify-center"
                  >
                    ×
                  </motion.button>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {!loading && knowledgeBases.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            还没有知识库，点击"新建知识库"创建第一个
          </div>
        )}
      </div>

      {selectedKB && (
        <div className="glass-panel p-4">
          <div className="text-white font-medium mb-3">知识库详情</div>
          <div className="text-gray-400 text-sm">
            选择一个知识库后，可以在这里查看和编辑文档内容
          </div>
        </div>
      )}
    </div>
  );
};

export default KnowledgeBasePage;