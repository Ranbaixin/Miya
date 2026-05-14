import { useState } from 'react';
import { motion } from 'framer-motion';
import { useMemorySystem, useMemory } from '../services/miyaApi';
import { cn } from '../utils';

const MemoryPage: React.FC = () => {
  const { memoryList, memoryGraph, refresh: refreshMemory, search } = useMemorySystem();
  const { stats: memStats, refresh: refreshStats } = useMemory();
  const [searchInput, setSearchInput] = useState('');
  const [tab, setTab] = useState<'list' | 'graph'>('list');
  const items = Array.isArray(memoryList?.data?.items) ? memoryList.data.items : [];
  const graphNodes = memoryGraph?.data?.nodes || [];
  const graphEdges = memoryGraph?.data?.edges || [];
  const memLevels = [
    { key: 'dialogue', label: '对话', color: '#00e5ff' },
    { key: 'short_term', label: '短期', color: '#7c4dff' },
    { key: 'long_term', label: '长期', color: '#ffab40' },
    { key: 'semantic', label: '语义', color: '#ec4899' },
    { key: 'knowledge', label: '知识', color: '#10b981' },
  ];
  const levelTag = (level: string) => {
    const l = memLevels.find(m => m.key === level);
    return <span className="text-[8px] px-1 py-0.5 rounded" style={{ background: `${l?.color || '#888'}15`, color: l?.color || '#888' }}>{l?.label || level}</span>;
  };
  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      <motion.div className="glass-panel p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-bold text-text-primary">◉ 记忆中心</span>
          <button className="text-[10px] text-aether hover:text-aether-bright" onClick={() => { refreshMemory(); refreshStats(); }}>↻ 刷新</button>
        </div>
        <div className="grid grid-cols-5 gap-3">
          <StatB label="总记忆" value={memStats?.total || 0} color="text-aether" />
          <StatB label="长期" value={memStats?.long_term || 0} color="text-starlight" />
          <StatB label="短期" value={memStats?.short_term || 0} color="text-resonance-bright" />
          <StatB label="用户" value={memStats?.users || 0} color="text-text-primary" />
          <StatB label="情感" value={memStats?.emotional || 0} color="text-status-active" />
        </div>
      </motion.div>
      <div className="flex items-center gap-1">
        {(['list', 'graph'] as const).map(k => (
          <button key={k} className={cn('px-3 py-1.5 text-[10px] rounded-lg transition-colors', tab === k ? 'bg-aether/10 text-aether border border-aether/20' : 'text-text-dim hover:text-text-primary')} onClick={() => setTab(k)}>
            {k === 'list' ? '▷ 记忆列表' : '◉ 认知图谱'}
          </button>
        ))}
      </div>
      {tab === 'list' ? (
        <>
          <div className="flex gap-2">
            <input className="flex-1 bg-void-deep/60 border border-border-glass rounded-lg px-3 py-1.5 text-[11px] text-text-primary outline-none focus:border-aether/30 placeholder:text-text-dim" placeholder="搜索记忆内容..." value={searchInput} onChange={e => setSearchInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && search(searchInput)} />
            <button className="px-3 py-1.5 text-[10px] rounded-lg bg-aether/10 text-aether border border-aether/20 hover:bg-aether/20" onClick={() => search(searchInput)}>搜索</button>
          </div>
          <div className="space-y-1">
            {items.length === 0 ? <div className="glass-panel p-8 text-center text-text-dim text-xs">暂无记忆数据</div> : items.map((item: any, i: number) => (
              <motion.div key={item.uuid || i} className="glass-panel p-2.5 flex items-start gap-3" initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.01 }} whileHover={{ borderColor: 'rgba(0,229,255,0.15)' }}>
                <div className="flex items-center gap-1.5 shrink-0">{levelTag(item.level || 'dialogue')}</div>
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] text-text-primary break-all leading-relaxed">{item.fact || item.content || '—'}</div>
                  <div className="flex items-center gap-2 mt-1 text-[9px] text-text-dim"><span>{item.created_at || ''}</span>{item.importance != null && <span className="text-starlight">重要性: {item.importance}</span>}{item.tags?.length > 0 && <span>标签: {item.tags.join(', ')}</span>}</div>
                </div>
              </motion.div>
            ))}
          </div>
          <div className="text-[9px] text-text-dim text-center">共 {memoryList?.total || items.length} 条记忆</div>
        </>
      ) : (
        <motion.div className="glass-panel p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="text-xs font-bold text-text-primary mb-3">◆ 认知图谱</div>
          {graphNodes.length === 0 ? <div className="text-center text-text-dim text-xs py-8">暂无图谱数据</div> : (
            <div className="space-y-1.5">{graphNodes.map((node: any, i: number) => { const nd = Array.isArray(node) ? node : [node]; const id = nd[0] || 'unknown'; const meta = nd[1] || {}; return <div key={i} className="flex items-center gap-2 py-1 border-b border-border-glass/30"><span className="w-1.5 h-1.5 rounded-full bg-aether/60" /><span className="text-[10px] text-text-primary truncate">{meta.name || id}</span><span className="text-[8px] text-text-dim px-1 py-0.5 rounded bg-void-deep/60">{meta._label || 'memory'}</span></div>; })}</div>
          )}
          {graphEdges.length > 0 && <div className="mt-3 text-[9px] text-text-dim">{graphEdges.length} 条关系连接</div>}
        </motion.div>
      )}
    </div>
  );
};

function StatB({ label, value, color }: { label: string; value: number; color: string }) {
  return <motion.div className="glass-panel p-3 text-center" initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} whileHover={{ scale: 1.03, borderColor: 'rgba(0,229,255,0.2)' }}><div className="text-[9px] text-text-dim mb-0.5">{label}</div><div className={cn('text-lg font-bold font-mono', color)}>{value}</div></motion.div>;
}

export default MemoryPage;
