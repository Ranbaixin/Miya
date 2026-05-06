// ============================================================
// 弥娅 Agent 网络 - Agent 与工具可视化
// ============================================================
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { fetchAgents, fetchTools } from '../services/miyaApi';
import type { AgentInfo, ToolDefinition } from '../types/index.d';

const AgentCard: React.FC<{ agent: AgentInfo }> = ({ agent }) => (
  <motion.div className="glass-panel p-3" whileHover={{ scale: 1.02, borderColor: 'rgba(59,130,246,0.4)' }}>
    <div className="flex items-center justify-between mb-2">
      <span className="text-sm font-bold text-blue-400">{agent.name}</span>
      <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 text-blue-400">
        {agent.tool_count} 工具
      </span>
    </div>
    <div className="flex flex-wrap gap-1">
      {agent.tools?.map((tool) => (
        <span key={tool} className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/5 border border-cyan-500/10 text-cyan-400/70">
          {tool}
        </span>
      ))}
    </div>
    {agent.status && (
      <div className="mt-2 text-[10px] text-gray-600">
        状态: <span className={agent.status === 'active' ? 'text-green-400' : 'text-gray-500'}>{agent.status}</span>
      </div>
    )}
  </motion.div>
);

const ToolItem: React.FC<{ tool: ToolDefinition }> = ({ tool }) => (
  <div className="flex items-center gap-2 px-2 py-1.5 border-b border-cyan-900/10 hover:bg-cyan-500/5 transition-colors">
    <span className="text-[10px] text-cyan-400 font-mono font-bold min-w-[140px] max-w-[200px] truncate">{tool.function?.name}</span>
    <span className="text-[10px] text-gray-400 flex-1 truncate">{tool.function?.description}</span>
    {tool.function?.parameters?.required && (
      <span className="text-[9px] text-yellow-600">
        参数: {tool.function.parameters.required.join(', ')}
      </span>
    )}
  </div>
);

const AgentNetworkPage: React.FC = () => {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const refresh = async () => {
      const [a, t] = await Promise.all([fetchAgents(), fetchTools()]);
      if (a?.length) setAgents(a as any);
      if (t?.tools?.length) setTools(t.tools);
    };
    refresh();
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
  }, []);

  // 后备数据
  const fallbackAgents: AgentInfo[] = [
    { name: 'code_delivery_agent', tool_count: 1, tools: ['python_interpreter'], status: 'active' },
    { name: 'entertainment_agent', tool_count: 5, tools: ['horoscope', 'qq_like', 'send_poke', 'react_emoji', 'wenchang_dijun'], status: 'active' },
    { name: 'file_analysis_agent', tool_count: 4, tools: ['group_file_downloader', 'local_file_finder', 'qq_file_reader', 'qq_image_analyzer'], status: 'active' },
    { name: 'info_agent', tool_count: 4, tools: ['baiduhot', 'douyinhot', 'qq_level_query', 'weibohot'], status: 'active' },
    { name: 'web_agent', tool_count: 2, tools: ['crawl_webpage', 'web_search'], status: 'active' },
  ];

  const displayAgents = agents.length > 0 ? agents : fallbackAgents;
  const totalTools = displayAgents.reduce((sum, a) => sum + a.tool_count, 0);
  const filteredTools = searchTerm
    ? tools.filter(t => t.function?.name?.toLowerCase().includes(searchTerm.toLowerCase()) || t.function?.description?.toLowerCase().includes(searchTerm.toLowerCase()))
    : tools;

  return (
    <div className="p-3 overflow-auto h-full space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">▣ Agent 网络</div>
          <div className="text-xs text-gray-600 mt-0.5">
            {displayAgents.length} Agent · {totalTools} 工具 · 已注册 {tools.length || 69} 工具
          </div>
        </div>
        <input
          type="text"
          placeholder="搜索工具..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-48 bg-gray-900/50 border border-cyan-900/30 text-xs text-gray-300 rounded px-2 py-1 outline-none focus:border-cyan-500/50"
        />
      </div>

      {/* Agent 卡片网格 */}
      <div className="grid grid-cols-5 gap-2">
        {displayAgents.map((agent) => (
          <AgentCard key={agent.name} agent={agent} />
        ))}
      </div>

      {/* 工具列表 */}
      <div>
        <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-1.5">
          ⚙ 工具注册表 ({filteredTools.length || 69})
        </div>
        <div className="glass-panel max-h-[400px] overflow-y-auto">
          {filteredTools.length > 0 ? (
            filteredTools.map((tool, i) => (
              <ToolItem key={tool.function?.name || i} tool={tool} />
            ))
          ) : tools.length === 0 ? (
            <div className="p-3 text-xs text-gray-600">工具数据将从后端加载（当前共 69 个工具已注册）</div>
          ) : (
            <div className="p-3 text-xs text-gray-600">无匹配工具</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentNetworkPage;
