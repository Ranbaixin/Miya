// ============================================================
// 弥娅 Agent 网络 · AgentNetworkPage — Agent 共鸣者
// ============================================================
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { fetchAgents, fetchTools } from '../services/miyaApi';
import type { AgentInfo } from '../types/index.d';

const AgentCard: React.FC<{ agent: AgentInfo; index: number }> = ({ agent, index }) => {
  return (
    <motion.div
      className="resonator-card p-3.5 cursor-pointer group"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -2 }}
    >
      <div className="corner-decor corner-tl" />
      <div className="corner-decor corner-tr" />

      <div className="flex items-center justify-between mb-2">
        <span className={`attr-badge attr-${agent.status === 'active' ? 'active' : 'idle'}`}>
          <div className={`pulse-dot ${agent.status === 'active' ? 'on' : 'off'}`} />
          {agent.status === 'active' ? 'ACTIVE' : 'IDLE'}
        </span>
        <span className="attr-badge attr-resonance">
          <span>⚙</span> {agent.tool_count} 工具
        </span>
      </div>

      <div className="font-display font-bold text-base text-text-primary mb-1 group-hover:text-resonance-bright transition-colors">
        {agent.name}
      </div>

      <div className="flex flex-wrap gap-1 mb-2.5">
        {agent.tools.map(t => (
          <span key={t} className="text-[9px] px-1.5 py-0.5 rounded bg-resonance/5 border border-resonance/10 text-text-secondary">
            {t}
          </span>
        ))}
      </div>

      <div className="resonance-bar">
        <div className="resonance-bar-fill"
          style={{ width: agent.status === 'active' ? '100%' : '25%' }}
        />
      </div>

      <div className="mt-2 flex items-center justify-between text-[10px]">
        <span className="text-text-dim">{agent.name.replace(/_/g, ' ')}</span>
        <span className="text-resonance-bright font-mono">Lv.{agent.tool_count}</span>
      </div>
    </motion.div>
  );
};

const AgentNetworkPage: React.FC = () => {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [tools, setTools] = useState<string[]>([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    const refresh = async () => {
      const [a, t] = await Promise.all([fetchAgents(), fetchTools()]);
      if (a?.length) setAgents(a as any);
      if (t?.tools) setTools(t.tools);
    };
    refresh();
    const i = setInterval(refresh, 15000);
    return () => clearInterval(i);
  }, []);

  const activeCount = agents.filter(a => a.status === 'active').length;
  const totalTools = agents.reduce((s, a) => s + a.tool_count, 0);

  const filteredTools = search
    ? tools.filter(t => t.toLowerCase().includes(search.toLowerCase()))
    : tools;

  return (
    <div className="p-4 overflow-auto h-full space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[10px] text-text-dim uppercase tracking-[0.2em]">▣ Agent 网络</div>
          <div className="text-xs text-text-secondary mt-0.5">
            <span className="text-resonance-bright">{activeCount}</span> 活跃 / <span className="text-text-primary">{agents.length}</span> Agent · <span className="text-starlight">{totalTools}</span> 工具
          </div>
        </div>
        <input
          type="text"
          placeholder="搜索工具..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-void-surface border border-border-glass rounded-lg px-3 py-1.5 text-xs text-text-primary placeholder-text-dim outline-none focus:border-aether/30 transition-colors w-48"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {agents.map((agent, i) => (
          <AgentCard key={agent.name} agent={agent} index={i} />
        ))}
      </div>

      {tools.length > 0 && (
        <motion.div className="glass-panel p-3.5" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <div className="text-[10px] text-text-dim uppercase tracking-wider mb-2">⚙ 可用工具</div>
          <div className="flex flex-wrap gap-1.5">
            {filteredTools.map(t => (
              <motion.span
                key={t}
                className="text-[10px] px-2 py-1 rounded bg-aether/5 border border-aether/10 text-text-secondary hover:text-aether-bright hover:border-aether/25 cursor-default transition-colors"
                whileHover={{ scale: 1.05 }}
              >
                {t}
              </motion.span>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default AgentNetworkPage;
