// ============================================================
// 弥娅 模型池 - 所有 12 个 AI 模型状态监控
// ============================================================
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { fetchModels } from '../services/miyaApi';
import type { ModelInfo } from '../types/index.d';

const ModelCard: React.FC<{ model: ModelInfo }> = ({ model }) => {
  const statusColors: Record<string, string> = {
    active: 'border-green-500/30 bg-green-500/5',
    idle: 'border-gray-700/30 bg-gray-800/20',
    error: 'border-red-500/30 bg-red-500/5',
  };

  return (
    <motion.div
      className={`glass-panel p-3 ${statusColors[model.status] || statusColors.idle}`}
      whileHover={{ scale: 1.02, borderColor: 'rgba(6,182,212,0.4)' }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] text-gray-600 uppercase tracking-wider">{model.type || 'chat'}</span>
        <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${model.status === 'active' ? 'bg-green-500/20 border-green-500/40 text-green-400' : model.status === 'error' ? 'bg-red-500/20 border-red-500/40 text-red-400' : 'bg-gray-700/20 border-gray-700/40 text-gray-500'}`}>
          {model.status}
        </span>
      </div>
      <div className="text-sm font-bold text-cyan-400 mb-1 font-mono truncate">{model.name || model.key}</div>
      <div className="text-[10px] text-gray-500 truncate mb-2">{model.model}</div>
      <div className="flex items-center justify-between text-[10px]">
        <span className="text-gray-600 truncate max-w-[120px]" title={model.endpoint}>{model.endpoint}</span>
        {model.tokens_used !== undefined && (
          <span className="text-purple-400 font-mono">{model.tokens_used.toLocaleString()} tok</span>
        )}
        {model.latency_ms !== undefined && (
          <span className="text-yellow-400 font-mono">{model.latency_ms}ms</span>
        )}
      </div>
    </motion.div>
  );
};

const ModelPoolPage: React.FC = () => {
  const [models, setModels] = useState<ModelInfo[]>([]);

  useEffect(() => {
    const refresh = async () => {
      const m = await fetchModels();
      if (m?.length) setModels(m as any);
    };
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, []);

  const activeCount = models.filter(m => m.status === 'active').length;
  const chatModels = models.filter(m => m.type === 'chat');
  const embeddingModels = models.filter(m => m.type === 'embedding');
  const visionModels = models.filter(m => m.type === 'vision');

  // 后备数据 - 从日志中提取的真实模型列表
  const fallbackModels: ModelInfo[] = [
    { key: 'deepseek_v4_flash_official', name: 'DeepSeek V4 Flash', model: 'deepseek-v4-flash', endpoint: 'https://api.deepseek.com/v1', status: 'active', type: 'chat' },
    { key: 'qwen_7b', name: 'Qwen 7B', model: 'Qwen/Qwen2.5-7B-Instruct', endpoint: 'https://api.siliconflow.cn/v1', status: 'active', type: 'chat' },
    { key: 'qwen_72b', name: 'Qwen 72B', model: 'Qwen/Qwen2.5-72B-Instruct', endpoint: 'https://api.siliconflow.cn/v1', status: 'active', type: 'chat' },
    { key: 'zhipu_glm_46v_flash', name: 'GLM-4.6V', model: 'zai-org/GLM-4.6V', endpoint: 'https://api.siliconflow.cn/v1', status: 'active', type: 'vision' },
    { key: 'siliconflow_qwen_vl', name: 'GLM-4.5V', model: 'glm-4.5v', endpoint: 'https://open.bigmodel.cn/api/paas/v4', status: 'active', type: 'vision' },
    { key: 'internlm_7b', name: 'InternLM 7B', model: 'internlm/internlm2_5-7b-chat', endpoint: 'https://api.siliconflow.cn/v1', status: 'active', type: 'chat' },
    { key: 'deepseek_r1_distill_7b', name: 'DeepSeek R1 Distill', model: 'deepseek-ai/DeepSeek-R1-Distill-Qwen-7B', endpoint: 'https://api.siliconflow.cn/v1', status: 'active', type: 'chat' },
    { key: 'llama_3_1_8b', name: 'Llama 3.1 8B', model: 'meta-llama/Llama-3.1-8B-Instruct', endpoint: 'https://api.siliconflow.cn/v1', status: 'active', type: 'chat' },
    { key: 'gemma_2_9b', name: 'Gemma 2 9B', model: 'google/gemma-2-9b-it', endpoint: 'https://api.siliconflow.cn/v1', status: 'active', type: 'chat' },
    { key: 'siliconflow_bge_large', name: 'BGE Large', model: 'BAAI/bge-large-zh-v1.5', endpoint: 'https://api.siliconflow.cn/v1', status: 'active', type: 'embedding' },
    { key: 'qwen3_embedding_8b', name: 'Qwen3 Embedding', model: 'Qwen/Qwen3-Embedding-8B', endpoint: 'https://api.siliconflow.cn/v1', status: 'active', type: 'embedding' },
    { key: 'deepseek_embedding', name: 'DeepSeek Embedding', model: 'deepseek-embedding', endpoint: 'https://api.deepseek.com/v1', status: 'active', type: 'embedding' },
  ];

  const displayModels = models.length > 0 ? models : fallbackModels;

  return (
    <div className="p-3 overflow-auto h-full space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">◆ 模型池</div>
          <div className="text-xs text-gray-600 mt-0.5">
            {activeCount} 活跃 / {displayModels.length} 总计
          </div>
        </div>
        <div className="flex gap-3 text-[10px] text-gray-600">
          <span className="text-cyan-400">💬 对话: {chatModels.length || displayModels.filter(m => m.type === 'chat').length}</span>
          <span className="text-purple-400">🔢 嵌入: {embeddingModels.length || displayModels.filter(m => m.type === 'embedding').length}</span>
          <span className="text-yellow-400">👁 视觉: {visionModels.length || displayModels.filter(m => m.type === 'vision').length}</span>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2">
        {displayModels.map((m) => (
          <ModelCard key={m.key} model={m} />
        ))}
      </div>

      {/* 默认模型标注 */}
      <div className="glass-panel p-3 text-[10px]">
        <div className="text-gray-500 mb-1">默认模型</div>
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 font-bold">deepseek-v4-flash</span>
          <span className="text-gray-600">(DeepSeek API)</span>
        </div>
      </div>
    </div>
  );
};

export default ModelPoolPage;
