import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import DataRing from '../components/DataRing';
import { useMiyaTools, miyaAPI, type ToolDefinition } from '../services/miyaApi';

interface ToolCall {
  id: string;
  tool_name: string;
  params: Record<string, any>;
  result: string;
  time: string;
  status: 'success' | 'error';
}

const ToolsPage: React.FC = () => {
  const { tools, loading, refresh } = useMiyaTools();
  const [selectedTool, setSelectedTool] = useState<ToolDefinition | null>(null);
  const [params, setParams] = useState('');
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [history, setHistory] = useState<ToolCall[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const defaultTools: ToolDefinition[] = [
    { function: { name: 'weather', description: '查询天气', parameters: { type: 'object', properties: { city: { type: 'string', description: '城市名称' } }, required: ['city'] } } },
    { function: { name: 'search', description: '网络搜索', parameters: { type: 'object', properties: { query: { type: 'string', description: '搜索关键词' } }, required: ['query'] } } },
    { function: { name: 'wikipedia', description: '百科查询', parameters: { type: 'object', properties: { query: { type: 'string', description: '查询内容' } } } } },
    { function: { name: 'translate', description: '翻译', parameters: { type: 'object', properties: { text: { type: 'string', description: '待翻译文本' }, target_lang: { type: 'string', description: '目标语言' } } } } },
    { function: { name: 'memory_add', description: '添加记忆', parameters: { type: 'object', properties: { fact: { type: 'string', description: '记忆内容' } }, required: ['fact'] } } },
    { function: { name: 'memory_delete', description: '删除记忆', parameters: { type: 'object', properties: { memory_uuid: { type: 'string', description: '记忆UUID' } }, required: ['memory_uuid'] } } },
    { function: { name: 'arXiv_search', description: 'arXiv搜索', parameters: { type: 'object', properties: { query: { type: 'string', description: '搜索词' }, max_results: { type: 'number', description: '最大结果数' } } } } },
    { function: { name: 'weather_query', description: '天气查询', parameters: { type: 'object', properties: { city: { type: 'string', description: '城市' }, days: { type: 'number', description: '天数' } } } } },
    { function: { name: 'web_fetch', description: '网页抓取', parameters: { type: 'object', properties: { url: { type: 'string', description: 'URL地址' } }, select: { type: 'string', description: '选择器' } } } },
    { function: { name: 'code_exec', description: '代码执行', parameters: { type: 'object', properties: { code: { type: 'string', description: 'Python代码' }, timeout: { type: 'number', description: '超时时间' } } } } },
  ];

  const displayTools = tools.length > 0 ? tools : defaultTools;
  
  const toolCallCounts: Record<string, number> = {};
  history.forEach(call => {
    toolCallCounts[call.tool_name] = (toolCallCounts[call.tool_name] || 0) + 1;
  });

  const filteredTools = displayTools.filter(tool => {
    const name = tool.function.name;
    if (searchQuery && !name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  const getToolType = (name: string): string => {
    const utility = ['weather', 'search', 'translate', 'web_fetch', 'code_exec'];
    const memory = ['memory_add', 'memory_delete', 'memory_search'];
    const knowledge = ['wikipedia', 'arXiv_search', 'arXiv_sender'];
    const vision = ['image_analysis', 'image_gen'];
    const ai = ['sentiment', 'naga_code_analysis'];
    
    if (utility.includes(name)) return 'utility';
    if (memory.includes(name)) return 'memory';
    if (knowledge.includes(name)) return 'knowledge';
    if (vision.includes(name)) return 'vision';
    if (ai.includes(name)) return 'ai';
    return 'developer';
  };

  const getToolColor = (type: string): string => {
    switch (type) {
      case 'utility': return 'rgba(0, 212, 255, 0.3)';
      case 'knowledge': return 'rgba(168, 85, 247, 0.3)';
      case 'developer': return 'rgba(255, 193, 7, 0.3)';
      case 'vision': return 'rgba(34, 197, 94, 0.3)';
      case 'memory': return 'rgba(244, 114, 182, 0.3)';
      case 'ai': return 'rgba(59, 130, 246, 0.3)';
      default: return 'rgba(158, 158, 158, 0.3)';
    }
  };

  const handleExecute = async () => {
    if (!selectedTool) return;
    setExecuting(true);
    setResult(null);
    
    let parsedParams = {};
    try {
      if (params.trim()) {
        parsedParams = JSON.parse(params);
      }
    } catch {
      setResult('参数格式错误，请输入有效的 JSON');
      setExecuting(false);
      return;
    }

    try {
      const res = await miyaAPI.invokeTool(selectedTool.function.name, parsedParams);
      const now = new Date();
      const timeStr = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}`;
      
      const call: ToolCall = {
        id: `call_${Date.now()}`,
        tool_name: selectedTool.function.name,
        params: parsedParams,
        result: JSON.stringify(res),
        time: timeStr,
        status: res?.error ? 'error' : 'success',
      };
      setHistory(prev => [call, ...prev.slice(0, 49)]);
      setResult(JSON.stringify(res, null, 2));
    } catch (e: any) {
      setResult(`执行失败: ${e.message}`);
    }
    
    setExecuting(false);
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-cyan-400 text-sm font-bold">工具中心</div>
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索工具..."
            className="px-2 py-1 text-xs bg-black/20 rounded text-gray-300 outline-none placeholder-gray-600 w-32"
          />
          <button
            onClick={() => refresh()}
            className="px-2 py-1 text-xs rounded bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 transition-colors"
          >
            刷新
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="glass-panel p-4">
          <div className="text-white text-xs font-medium mb-3">可用工具 ({displayTools.length})</div>
          {loading ? (
            <div className="text-center text-xs text-gray-500 py-8">加载中...</div>
          ) : (
            <div className="grid grid-cols-2 gap-3 max-h-[60vh] overflow-y-auto pr-2">
              {filteredTools.map((tool) => {
                const name = tool.function.name;
                const type = getToolType(name);
                const count = toolCallCounts[name] || 0;
                return (
                  <motion.div
                    key={name}
                    onClick={() => setSelectedTool(tool)}
                    className={`p-3 rounded-lg cursor-pointer transition-all border ${
                      selectedTool?.function.name === name 
                        ? 'border-cyan-400 bg-cyan-500/10' 
                        : 'border-transparent bg-black/20 hover:border-purple-500/30'
                    }`}
                    whileHover={{ scale: 1.02 }}
                  >
                    <DataRing 
                      value={count} 
                      label={name} 
                      color={getToolColor(type)}
                      size={70}
                    />
                    <div className="mt-2 text-[10px] text-center text-gray-400 line-clamp-1">
                      {tool.function.description || name}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="glass-panel p-4">
            <div className="text-white text-xs font-bold mb-3">工具执行</div>
            {selectedTool ? (
              <div className="space-y-3">
                <div className="text-sm text-cyan-400 font-medium">{selectedTool.function.name}</div>
                <div className="text-[10px] text-gray-500">{selectedTool.function.description}</div>
                
                {selectedTool.function.parameters && (
                  <div className="text-[10px] text-gray-500 mt-2">
                    参数: {Object.keys(selectedTool.function.parameters.properties || {}).join(', ')}
                  </div>
                )}
                
                <textarea
                  value={params}
                  onChange={(e) => setParams(e.target.value)}
                  placeholder='{"key": "value"}'
                  className="w-full h-24 bg-black/20 rounded p-2 text-xs text-gray-300 outline-none resize-none placeholder-gray-600"
                />
                <button
                  onClick={handleExecute}
                  disabled={executing}
                  className="w-full py-2 rounded bg-gradient-to-r from-cyan-500/30 to-purple-500/30 text-cyan-400 hover:from-cyan-500/40 hover:to-purple-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-xs"
                >
                  {executing ? '执行中...' : '执行工具'}
                </button>
                
                {result && (
                  <div className="p-2 bg-black/30 rounded text-[10px] text-gray-300 max-h-40 overflow-y-auto whitespace-pre-wrap">
                    {result}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-sm text-gray-500 py-8 text-center">请选择一个工具</div>
            )}
          </div>

          <div className="glass-panel p-4">
            <div className="text-white text-xs font-bold mb-3">调用历史 ({history.length})</div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {history.length > 0 ? (
                history.slice(0, 20).map((call) => (
                  <motion.div 
                    key={call.id} 
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="text-[10px] p-2 rounded bg-black/10 border-l-2"
                    style={{ borderLeftColor: call.status === 'success' ? '#06b6d4' : '#ef4444' }}
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-cyan-400 font-medium">{call.tool_name}</span>
                      <span className="text-gray-600">{call.time}</span>
                    </div>
                    <div className="text-gray-500 truncate mt-0.5">{call.result.slice(0, 100)}</div>
                  </motion.div>
                ))
              ) : (
                <div className="text-xs text-gray-600 text-center py-4">暂无调用历史</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ToolsPage;