import { useState } from 'react';
import { motion } from 'framer-motion';
import { usePlugins } from '../services/miyaApi';

const PluginManagerPage: React.FC = () => {
  const { plugins, loading, refresh, enable, disable, uninstall } = usePlugins();
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<'all' | 'enabled' | 'disabled'>('all');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const filteredPlugins = plugins.filter(p => {
    const matchSearch = p.name.includes(searchQuery) || p.description.includes(searchQuery);
    if (filter === 'enabled') return matchSearch && p.enabled;
    if (filter === 'disabled') return matchSearch && !p.enabled;
    return matchSearch;
  });

  const handleToggle = async (name: string, enabled: boolean) => {
    setActionLoading(name);
    try {
      if (enabled) {
        await disable(name);
      } else {
        await enable(name);
      }
      await refresh();
    } finally {
      setActionLoading(null);
    }
  };

  const handleUninstall = async (name: string) => {
    if (!confirm(`确定要卸载 ${name} 吗？`)) return;
    setActionLoading(name);
    try {
      await uninstall(name);
      await refresh();
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div className="glass-panel p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="text-white font-medium">已安装插件</div>
          <div className="flex items-center gap-3">
            <div className="text-gray-400 text-sm">{plugins.length} 个插件</div>
            <button
              onClick={() => refresh()}
              className="px-2 py-1 text-xs rounded bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30"
            >
              刷新
            </button>
          </div>
        </div>

        <div className="flex gap-2 mb-4">
          <input
            type="text"
            placeholder="搜索插件..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
          />
        </div>

        <div className="flex gap-2 mb-4">
          {(['all', 'enabled', 'disabled'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-full text-xs ${
                filter === f 
                  ? 'bg-cyan-500/30 text-cyan-400' 
                  : 'bg-gray-800/50 text-gray-400 hover:text-white'
              }`}
            >
              {f === 'all' ? '全部' : f === 'enabled' ? '已启用' : '已禁用'}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-center py-8 text-gray-500">加载中...</div>
        ) : (
          <div className="space-y-2">
            {filteredPlugins.map(plugin => (
              <motion.div
                key={plugin.name}
                layout
                className="p-3 bg-gray-800/30 rounded-lg"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="text-white font-medium">{plugin.name}</div>
                    <div className="text-gray-400 text-sm">{plugin.description}</div>
                    <div className="text-gray-500 text-xs mt-1">
                      {plugin.author} · v{plugin.version}
                      {plugin.installed_at && ` · ${plugin.installed_at.slice(0, 10)}`}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggle(plugin.name, plugin.enabled)}
                      disabled={actionLoading === plugin.name}
                      className={`w-10 h-5 rounded-full transition-colors ${
                        actionLoading === plugin.name ? 'opacity-50' : ''
                      } ${plugin.enabled ? 'bg-cyan-500' : 'bg-gray-700'}`}
                    >
                      <div className={`w-4 h-4 bg-white rounded-full transition-transform ${
                        plugin.enabled ? 'translate-x-5' : 'translate-x-0.5'
                      }`} />
                    </button>
                    <button
                      onClick={() => handleUninstall(plugin.name)}
                      disabled={actionLoading === plugin.name}
                      className="w-8 h-8 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/40 flex items-center justify-center disabled:opacity-50"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {!loading && filteredPlugins.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            {plugins.length === 0 
              ? '还没有安装任何插件，去插件市场看看吧~' 
              : '没有找到匹配的插件'}
          </div>
        )}
      </div>
    </div>
  );
};

export default PluginManagerPage;