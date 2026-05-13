// ============================================================
// 弥娅运维中心 · 配置中心页 — 配置文件查看 / 热编辑
// ============================================================
import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../utils';

interface ConfigItem {
  key: string;
  name: string;
  path: string;
  format: 'json' | 'yaml' | 'env' | 'other';
  editable: boolean;
  size?: string;
  description?: string;
}

const CONFIG_FILES: ConfigItem[] = [
  { key: 'env', name: '.env', path: 'config/.env', format: 'env', editable: true, description: '环境变量与 API 密钥' },
  { key: 'models', name: 'multi_model_config.json', path: 'config/multi_model_config.json', format: 'json', editable: true, description: '多模型配置与路由策略' },
  { key: 'permissions', name: 'permissions.json', path: 'config/permissions.json', format: 'json', editable: true, description: '权限配置' },
  { key: 'skills', name: 'skills.yaml', path: 'config/skills.yaml', format: 'yaml', editable: true, description: '技能配置' },
  { key: 'qq', name: 'qq_config.yaml', path: 'config/qq_config.yaml', format: 'yaml', editable: true, description: 'QQ 机器人配置' },
  { key: 'mcp', name: 'mcp.json', path: 'config/mcp.json', format: 'json', editable: true, description: 'MCP 服务器配置' },
  { key: 'endpoints', name: 'api_endpoints.json', path: 'config/api_endpoints.json', format: 'json', editable: true, description: '外部 API 端点配置' },
  { key: 'memory', name: 'memory_config.json', path: 'config/memory_config.json', format: 'json', editable: true, description: '记忆系统配置' },
  { key: 'constants', name: 'system_constants.json', path: 'config/system_constants.json', format: 'json', editable: true, description: '系统常量' },
  { key: 'personalities', name: 'personalities/*.yaml', path: 'config/personalities/', format: 'yaml', editable: true, description: '30+ 人格配置 (目录)', size: '30 files' },
];

const ConfigCenterPage: React.FC = () => {
  const [selected, setSelected] = useState<ConfigItem | null>(null);
  const [content, setContent] = useState('');
  const [original, setOriginal] = useState('');
  const [edited, setEdited] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectFile = useCallback(async (item: ConfigItem) => {
    setSelected(item);
    setLoading(true);
    setError(null);
    setSaved(false);
    try {
      const res = await fetch(`http://localhost:8000/api/config/file?path=${encodeURIComponent(item.path)}`);
      if (res.ok) {
        const data = await res.json();
        const text = typeof data.content === 'string' ? data.content : JSON.stringify(data.content || data, null, 2);
        setContent(text);
        setOriginal(text);
        setEdited(false);
      } else if (item.format === 'env') {
        const text = '# .env 配置文件\n# 请在下方编辑环境变量\n\n# API Keys\nOPENAI_API_KEY=\nDEEPSEEK_API_KEY=\nSILICONFLOW_API_KEY=\n\n# 系统配置\nMIYA_ENV=development\nLOG_LEVEL=INFO\n';
        setContent(text);
        setOriginal(text);
        setEdited(false);
      } else {
        const text = item.format === 'json' ? '{\n  // 配置文件\n}' : '# 配置文件';
        setContent(text);
        setOriginal(text);
        setEdited(false);
      }
    } catch {
      const text = item.format === 'json' ? '{\n  // 无法加载配置文件\n}' : '# 无法加载配置文件';
      setContent(text);
      setOriginal(text);
      setEdited(false);
    } finally {
      setLoading(false);
    }
  }, []);

  const saveFile = useCallback(async () => {
    if (!selected) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/api/config/file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Undefined-API-Key': 'changeme' },
        body: JSON.stringify({ path: selected.path, content }),
      });
      if (res.ok) {
        setOriginal(content);
        setEdited(false);
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      } else {
        setError('保存失败: ' + (await res.text()));
      }
    } catch (e: any) {
      setError('保存失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, [selected, content]);

  const discardChanges = useCallback(() => {
    setContent(original);
    setEdited(false);
  }, [original]);

  const formatLabel = (f: string) => {
    switch (f) {
      case 'json': return <span className="text-[9px] px-1.5 py-0.5 rounded bg-aether/10 text-aether">JSON</span>;
      case 'yaml': return <span className="text-[9px] px-1.5 py-0.5 rounded bg-resonance/10 text-resonance-bright">YAML</span>;
      case 'env': return <span className="text-[9px] px-1.5 py-0.5 rounded bg-starlight/10 text-starlight">ENV</span>;
      default: return <span className="text-[9px] px-1.5 py-0.5 rounded bg-void-deep/60 text-text-dim">{f.toUpperCase()}</span>;
    }
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* ---- 文件列表侧边栏 ---- */}
      <div className="w-64 flex-shrink-0 border-r border-border-glass overflow-auto p-3 space-y-1">
        <div className="text-xs font-bold text-text-primary mb-3 px-1">◆ 配置文件</div>
        {CONFIG_FILES.map((item) => (
          <motion.button
            key={item.key}
            className={cn(
              'w-full text-left px-3 py-2 rounded-lg transition-all duration-150 text-xs',
              selected?.key === item.key
                ? 'bg-aether/10 border border-aether/20 text-aether'
                : 'hover:bg-void-surface/60 text-text-secondary hover:text-text-primary border border-transparent'
            )}
            onClick={() => selectFile(item)}
            whileHover={{ x: 2 }}
          >
            <div className="flex items-center gap-2">
              <span className="w-4 text-[10px]">{item.format === 'json' ? '{}' : item.format === 'yaml' ? '#' : item.format === 'env' ? '$' : '?'}</span>
              <span className="truncate">{item.name}</span>
            </div>
            {item.description && (
              <div className="text-[9px] text-text-dim ml-6 truncate">{item.description}</div>
            )}
          </motion.button>
        ))}
      </div>

      {/* ---- 编辑器主区域 ---- */}
      <div className="flex-1 flex flex-col min-w-0">
        <AnimatePresence mode="wait">
          {selected ? (
            <motion.div
              key={selected.key}
              className="flex-1 flex flex-col"
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.15 }}
            >
              {/* 工具栏 */}
              <div className="flex items-center justify-between px-4 py-2 border-b border-border-glass bg-void-panel/50">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-bold text-text-primary">{selected.name}</span>
                  {formatLabel(selected.format)}
                  {selected.size && <span className="text-[10px] text-text-dim">{selected.size}</span>}
                </div>
                <div className="flex items-center gap-2">
                  {saved && <span className="text-[10px] text-status-active">✓ 已保存</span>}
                  {error && <span className="text-[10px] text-status-error">{error}</span>}
                  {edited && (
                    <>
                      <button
                        className="px-2 py-1 text-[10px] rounded-lg bg-void-deep/60 text-text-dim hover:text-text-primary transition-colors"
                        onClick={discardChanges}
                      >
                        撤销
                      </button>
                      <button
                        className="px-3 py-1 text-[10px] rounded-lg bg-aether/10 text-aether border border-aether/20 hover:bg-aether/20 transition-all"
                        onClick={saveFile}
                        disabled={loading}
                      >
                        {loading ? '保存中...' : '保存'}
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* 编辑器 */}
              {loading && !content ? (
                <div className="flex-1 flex items-center justify-center">
                  <span className="text-text-dim animate-pulse">加载中...</span>
                </div>
              ) : (
                <textarea
                  className="flex-1 w-full bg-void-deep/40 text-text-primary text-xs font-mono p-4 resize-none outline-none focus:bg-void-deep/60 transition-colors scrollbar-thin"
                  value={content}
                  onChange={(e) => { setContent(e.target.value); setEdited(e.target.value !== original); }}
                  spellCheck={false}
                  placeholder={selected.format === 'json' ? '{\n  // JSON 配置\n}' : selected.format === 'yaml' ? '# YAML 配置\n' : '# 环境变量\n'}
                />
              )}
            </motion.div>
          ) : (
            <motion.div
              className="flex-1 flex items-center justify-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="text-center">
                <div className="text-3xl text-text-dim mb-3">⚙</div>
                <div className="text-sm text-text-secondary mb-1">配置中心</div>
                <div className="text-[10px] text-text-dim">从左侧选择配置文件进行查看和编辑</div>
                <div className="text-[9px] text-text-dim mt-2">修改后点击"保存"即可热更新</div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default ConfigCenterPage;
