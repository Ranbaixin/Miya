// ============================================================
// 弥娅 模型矩阵 · ModelPoolPage — AI 模型共鸣者展示
//   灵感: 鸣潮共鸣者卡片网格
// ============================================================
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { fetchModels } from '../services/miyaApi';
import type { ModelInfo } from '../types/index.d';

type FilterAttr = 'all' | 'aether' | 'resonance' | 'starlight';

const ModelCard: React.FC<{ model: ModelInfo; index: number }> = ({ model, index }) => {
  const attr: { type: FilterAttr; label: string; icon: string } =
    model.type === 'chat' ? { type: 'aether', label: '对话·CHAT', icon: '◆' } :
    model.type === 'embedding' ? { type: 'resonance', label: '嵌入·EMBED', icon: '◇' } :
    { type: 'starlight', label: '视觉·VISION', icon: '✦' };

  const statusAc = model.status === 'active' ? 'active' : model.status === 'error' ? 'error' : 'idle';

  return (
    <motion.div
      className="resonator-card p-3.5 cursor-pointer group"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -2 }}
    >
      <div className="corner-decor corner-tl" />
      <div className="corner-decor corner-tr" />

      <div className="flex items-center justify-between mb-2">
        <span className={`attr-badge attr-${attr.type}`}>
          <span>{attr.icon}</span> {attr.label}
        </span>
        <span className={`attr-badge attr-${statusAc}`}>
          <div className={`pulse-dot ${model.status === 'active' ? 'on' : model.status === 'error' ? 'pulse-dot warn' : 'off'}`} />
          {model.status}
        </span>
      </div>

      <div className="font-display font-bold text-base text-text-primary mb-1 group-hover:text-aether transition-colors truncate">
        {model.name || model.key}
      </div>
      <div className="text-[10px] text-text-secondary truncate mb-2.5">{model.model}</div>

      <div className="resonance-bar mb-2">
        <div
          className="resonance-bar-fill"
          style={{ width: model.status === 'active' ? '100%' : model.status === 'error' ? '15%' : '35%' }}
        />
      </div>

      <div className="flex items-center justify-between text-[10px]">
        <span className="text-text-dim truncate max-w-[130px]" title={model.endpoint}>{model.endpoint}</span>
        <div className="flex gap-1">
          {model.tokens_used !== undefined && (
            <span className="text-aether font-mono">{model.tokens_used.toLocaleString()} tok</span>
          )}
          {model.latency_ms !== undefined && (
            <span className="text-starlight font-mono ml-1.5">{model.latency_ms}ms</span>
          )}
        </div>
      </div>
    </motion.div>
  );
};

const ModelPoolPage: React.FC = () => {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [filter, setFilter] = useState<FilterAttr>('all');

  useEffect(() => {
    const refresh = async () => {
      const m = await fetchModels();
      if (m?.length) setModels(m as any);
    };
    refresh();
    const t = setInterval(refresh, 10000);
    return () => clearInterval(t);
  }, []);

  const fallbackModels: ModelInfo[] = [
    { key: 'deepseek_v4_flash', name: 'DeepSeek V4 Flash', model: 'deepseek-v4-flash', endpoint: 'api.deepseek.com', status: 'active', type: 'chat' },
    { key: 'qwen_7b', name: 'Qwen 7B', model: 'Qwen2.5-7B', endpoint: 'api.siliconflow.cn', status: 'active', type: 'chat' },
    { key: 'qwen_72b', name: 'Qwen 72B', model: 'Qwen2.5-72B', endpoint: 'api.siliconflow.cn', status: 'active', type: 'chat' },
    { key: 'glm_46v', name: 'GLM-4.6V', model: 'GLM-4.6V', endpoint: 'api.siliconflow.cn', status: 'active', type: 'vision' },
    { key: 'glm_45v', name: 'GLM-4.5V', model: 'glm-4.5v', endpoint: 'open.bigmodel.cn', status: 'active', type: 'vision' },
    { key: 'internlm_7b', name: 'InternLM 7B', model: 'InternLM2.5-7B', endpoint: 'api.siliconflow.cn', status: 'active', type: 'chat' },
    { key: 'r1_distill', name: 'R1 Distill 7B', model: 'R1-Distill-Qwen-7B', endpoint: 'api.siliconflow.cn', status: 'active', type: 'chat' },
    { key: 'llama_3_1', name: 'Llama 3.1 8B', model: 'Llama-3.1-8B', endpoint: 'api.siliconflow.cn', status: 'active', type: 'chat' },
    { key: 'gemma_2', name: 'Gemma 2 9B', model: 'gemma-2-9b-it', endpoint: 'api.siliconflow.cn', status: 'active', type: 'chat' },
    { key: 'bge_large', name: 'BGE Large', model: 'bge-large-zh-v1.5', endpoint: 'api.siliconflow.cn', status: 'active', type: 'embedding' },
    { key: 'qwen3_emb', name: 'Qwen3 Emb 8B', model: 'Qwen3-Embedding-8B', endpoint: 'api.siliconflow.cn', status: 'active', type: 'embedding' },
    { key: 'ds_emb', name: 'DeepSeek Emb', model: 'deepseek-embedding', endpoint: 'api.deepseek.com', status: 'active', type: 'embedding' },
  ];

  const displayModels = models.length > 0 ? models : fallbackModels;

  const attrMap: Record<string, FilterAttr> = {
    chat: 'aether',
    embedding: 'resonance',
    vision: 'starlight',
  };

  const filtered = filter === 'all' ? displayModels : displayModels.filter((m: any) => attrMap[m.type] === filter);

  const filters: { id: FilterAttr; icon: string; label: string; count: number }[] = [
    { id: 'all', icon: '◈', label: '全部', count: displayModels.length },
    { id: 'aether', icon: '◆', label: '对话', count: displayModels.filter((m: any) => m.type === 'chat').length },
    { id: 'resonance', icon: '◇', label: '嵌入', count: displayModels.filter((m: any) => m.type === 'embedding').length },
    { id: 'starlight', icon: '✦', label: '视觉', count: displayModels.filter((m: any) => m.type === 'vision').length },
  ];

  const activeCount = displayModels.filter(m => m.status === 'active').length;

  return (
    <div className="p-4 overflow-auto h-full space-y-3">
      {/* 标题 */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[10px] text-text-dim uppercase tracking-[0.2em]">◆ 模型矩阵</div>
          <div className="text-xs text-text-secondary mt-0.5">
            <span className="text-aether">{activeCount}</span> 共鸣 / <span className="text-text-primary">{displayModels.length}</span> 总计
          </div>
        </div>
      </div>

      {/* 属性筛选 */}
      <div className="flex gap-1.5 flex-wrap">
        {filters.map(f => (
          <motion.button
            key={f.id}
            className={`px-3 py-1.5 rounded-lg text-[11px] border transition-all ${
              filter === f.id
                ? 'bg-aether/10 border-aether/25 text-aether-bright'
                : 'bg-void-surface/50 border-border-glass text-text-secondary hover:text-text-primary hover:border-aether/15'
            }`}
            onClick={() => setFilter(f.id)}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.96 }}
          >
            <span className="mr-1">{f.icon}</span>
            {f.label}
            <span className="ml-1.5 text-[9px] opacity-50">{f.count}</span>
          </motion.button>
        ))}
      </div>

      {/* 卡片网格 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {filtered.map((m, i) => (
          <ModelCard key={m.key} model={m as any} index={i} />
        ))}
      </div>

      {/* 默认模型 */}
      <div className="glass-panel p-3 text-[10px]">
        <div className="text-text-dim mb-1">默认共鸣核心</div>
        <div className="flex items-center gap-2">
          <span className="text-aether font-bold">deepseek-v4-flash</span>
          <span className="text-text-dim">(DeepSeek API)</span>
        </div>
      </div>
    </div>
  );
};

export default ModelPoolPage;
