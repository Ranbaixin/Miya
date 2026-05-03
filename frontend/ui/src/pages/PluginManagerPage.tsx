import { useState } from 'react';
import { motion } from 'framer-motion';

const defaultPlugins = [
  { name: 'bing_search', description: '必应搜索', author: 'AstrBot', version: '1.2.0', enabled: true },
  { name: 'weather', description: '天气查询', author: 'AstrBot', version: '1.0.0', enabled: true },
  { name: 'translate', description: '翻译插件', author: 'AstrBot', version: '1.1.0', enabled: false },
  { name: 'riddle', description: '谜语问答', author: 'Community', version: '0.9.0', enabled: false },
];

const PluginManagerPage: React.FC = () => {
  const [plugins, setPlugins] = useState(defaultPlugins);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<'all' | 'enabled' | 'disabled'>('all');

  const filteredPlugins = plugins.filter(p => {
    const matchSearch = p.name.includes(searchQuery) || p.description.includes(searchQuery);
    if (filter === 'enabled') return matchSearch && p.enabled;
    if (filter === 'disabled') return matchSearch && !p.enabled;
    return matchSearch;
  });

  const handleToggle = (name: string) => {
    setPlugins(plugins.map(p => 
      p.name === name ? { ...p, enabled: !p.enabled } : p
    ));
  };

  const handleDelete = (name: string) => {
    if (confirm(`确定要卸载 ${name} 吗？`)) {
      setPlugins(plugins.filter(p => p.name !== name));
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div className="glass-panel p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="text-white font-medium">已安装插件</div>
          <div className="text-gray-400 text-sm">{plugins.length} 个插件</div>
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
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggle(plugin.name)}
                    className={`w-10 h-5 rounded-full transition-colors ${
                      plugin.enabled ? 'bg-cyan-500' : 'bg-gray-700'
                    }`}
                  >
                    <div className={`w-4 h-4 bg-white rounded-full transition-transform ${
                      plugin.enabled ? 'translate-x-5' : 'translate-x-0.5'
                    }`} 
                  />
                  </button>
                  <button
                    onClick={() => handleDelete(plugin.name)}
                    className="w-8 h-8 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/40 flex items-center justify-center"
                  >
                    ×
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {filteredPlugins.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            没有找到匹配的插件
          </div>
        )}
      </div>
    </div>
  );
};

export default PluginManagerPage;