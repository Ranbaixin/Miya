import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePluginMarket, usePlugins, miyaAPI } from '../services/miyaApi';
import type { PluginInfo } from '../services/miyaApi';

const PluginMarketPage: React.FC = () => {
  const { plugins, loading, refresh } = usePluginMarket();
  const { refresh: refreshInstalled } = usePlugins();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPlugin, setSelectedPlugin] = useState<PluginInfo | null>(null);
  const [installing, setInstalling] = useState<string | null>(null);
  const [installMessage, setInstallMessage] = useState<string | null>(null);
  const [installSuccess, setInstallSuccess] = useState<boolean | null>(null);

  const handleSearch = useCallback(() => {
    refresh(searchQuery);
  }, [refresh, searchQuery]);

  const handleInstall = async (plugin: PluginInfo) => {
    setInstalling(plugin.name);
    setInstallMessage(null);
    setInstallSuccess(null);
    try {
      const result = await miyaAPI.installPlugin(plugin.name);
      if (result?.success) {
        setInstallSuccess(true);
        setInstallMessage(result.message || `插件 ${plugin.name} 安装成功`);
        refreshInstalled();
      } else {
        setInstallSuccess(false);
        setInstallMessage(result?.message || '安装失败，请检查后端服务');
      }
    } catch {
      setInstallSuccess(false);
      setInstallMessage('安装请求失败，请确认后端服务正在运行');
    }
    setInstalling(null);
  };

  const handleCloseModal = () => {
    setSelectedPlugin(null);
    setInstallMessage(null);
    setInstallSuccess(null);
  };

  const getCategoryColor = (category?: string) => { switch (category) {
    case 'utils': return 'text-cyan-400';
    case 'media': return 'text-pink-400';
    case 'social': return 'text-purple-400';
    case 'life': return 'text-green-400';
    case 'knowledge': return 'text-yellow-400';
    case 'memory': return 'text-blue-400';
    default: return 'text-gray-400';
  }};

  return (
    <div className="p-4 overflow-auto h-full space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-cyan-400 text-sm font-medium">插件市场</div>
        <motion.button
          className="px-3 py-1 text-xs rounded bg-cyan-500/20 text-cyan-400"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => refresh()}
        >
          刷新
        </motion.button>
      </div>

      <div className="flex items-center gap-2">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="搜索插件..."
          className="flex-1 px-3 py-2 text-sm bg-gray-800/50 border border-gray-700 rounded text-white placeholder-gray-500 focus:border-cyan-500 focus:outline-none"
        />
        <motion.button
          className="px-4 py-2 text-sm rounded bg-cyan-500/20 text-cyan-400"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleSearch}
        >
          搜索
        </motion.button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {plugins.map((plugin) => (
          <motion.div
            key={plugin.name}
            className="glass-panel p-4 cursor-pointer"
            whileHover={{ scale: 1.02 }}
            onClick={() => setSelectedPlugin(plugin)}
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded bg-gray-700/50 flex items-center justify-center text-lg">
                {plugin.icon_url ? (
                  <img src={plugin.icon_url} alt={plugin.name} className="w-8 h-8" />
                ) : (
                  '🔌'
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-white font-medium truncate">{plugin.name}</div>
                <div className="text-gray-500 text-xs truncate">{plugin.author}</div>
                <div className={`text-xs ${getCategoryColor(plugin.category)}`}>
                  {plugin.category || '未分类'}
                </div>
              </div>
            </div>

            <div className="text-gray-400 text-xs line-clamp-2 mt-2">
              {plugin.description || '暂无描述'}
            </div>

            <div className="flex items-center gap-2 mt-3 text-xs text-gray-500">
              <span>v{plugin.version}</span>
            </div>
          </motion.div>
        ))}
      </div>

      {plugins.length === 0 && !loading && (
        <div className="text-center text-gray-500 py-8">
          <div className="text-2xl mb-2">🔌</div>
          <div>暂无插件</div>
          <div className="text-sm mt-1">试试搜索其他关键词？</div>
        </div>
      )}

      <AnimatePresence>
        {selectedPlugin && (
          <motion.div
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleCloseModal}
          >
            <motion.div
              className="glass-panel p-6 w-full max-w-md mx-4"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded bg-gray-700/50 flex items-center justify-center text-2xl">
                  {selectedPlugin.icon_url ? (
                    <img src={selectedPlugin.icon_url} alt={selectedPlugin.name} />
                  ) : (
                    '🔌'
                  )}
                </div>
                <div>
                  <div className="text-white font-medium">{selectedPlugin.name}</div>
                  <div className="text-gray-400 text-sm">
                    by {selectedPlugin.author}
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400 text-sm">版本</span>
                  <span className="text-cyan-400">v{selectedPlugin.version}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-gray-400 text-sm">分类</span>
                  <span className={getCategoryColor(selectedPlugin.category)}>
                    {selectedPlugin.category || '未分类'}
                  </span>
                </div>

                <div className="pt-2 border-t border-gray-700">
                  <div className="text-gray-400 text-sm mb-1">描述</div>
                  <div className="text-white text-sm">
                    {selectedPlugin.description || '暂无描述'}
                  </div>
                </div>
              </div>

              {installMessage && (
                <div className={`mt-3 p-2 rounded text-sm text-center ${
                  installSuccess ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                }`}>
                  {installMessage}
                </div>
              )}

              <div className="flex items-center gap-2 mt-6">
                <motion.button
                  className="flex-1 px-4 py-2 text-sm rounded bg-gray-500/20 text-gray-400"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleCloseModal}
                >
                  关闭
                </motion.button>
                <motion.button
                  className={`flex-1 px-4 py-2 text-sm rounded bg-green-500/20 ${
                    installing === selectedPlugin.name ? 'text-yellow-400' : 'text-green-400'
                  } ${installSuccess ? 'opacity-50 cursor-not-allowed' : ''}`}
                  whileHover={installSuccess ? {} : { scale: 1.02 }}
                  whileTap={installSuccess ? {} : { scale: 0.98 }}
                  onClick={() => handleInstall(selectedPlugin)}
                  disabled={installing === selectedPlugin.name || installSuccess === true}
                >
                  {installing === selectedPlugin.name
                    ? '安装中...'
                    : installSuccess
                    ? '已安装'
                    : '安装'}
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {loading && (
        <div className="fixed bottom-4 right-4 text-cyan-400 text-sm">
          加载中...
        </div>
      )}
    </div>
  );
};

export default PluginMarketPage;