import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePlatforms } from '../services/miyaApi';
import type { PlatformInfo } from '../services/miyaApi';

const PLATFORM_ICONS: Record<string, string> = {
  qqofficial: '🐧',
  qqofficial_webhook: '🐧',
  aiocqhttp: '🐧',
  telegram: '✈️',
  discord: '🎮',
  slack: '💼',
  lark: '📮',
  dingtalk: '📌',
  wecom: '💼',
  wecom_ai_bot: '🤖',
  weixin_oc: '💬',
  weixin_official_account: '📰',
  line: '📱',
  kook: '👾',
  mattermost: '💬',
  misskey: '⭐',
  satori: '🔌',
  webchat: '🌐',
};

const PLATFORM_NAMES: Record<string, string> = {
  qqofficial: 'QQ 官方机器人',
  qqofficial_webhook: 'QQ 官方 Webhook',
  aiocqhttp: 'OneBot (NapCat)',
  telegram: 'Telegram',
  discord: 'Discord',
  slack: 'Slack',
  lark: '飞书',
  dingtalk: '钉钉',
  wecom: '企业微信',
  wecom_ai_bot: '企业微信 AI Bot',
  weixin_oc: '微信开放平台',
  weixin_official_account: '微信公众号',
  line: 'LINE',
  kook: 'KOOK',
  mattermost: 'Mattermost',
  misskey: 'Misskey',
  satori: 'Satori',
  webchat: '网页聊天',
};

const PlatformPage: React.FC = () => {
  const { platforms, loading, refresh, stats, connect, disconnect } = usePlatforms();
  const [selectedPlatform, setSelectedPlatform] = useState<PlatformInfo | null>(null);
  const [showAddDialog, setShowAddDialog] = useState(false);

  const handleConnect = async (platform: PlatformInfo) => {
    if (platform.status === 'connected') {
      await disconnect(platform.platform_id);
    } else {
      await connect(platform.platform_id);
    }
    await refresh();
  };

  const getStatusColor = (status: PlatformInfo['status']) => {
    switch (status) {
      case 'connected':
        return 'text-green-400';
      case 'disconnected':
        return 'text-gray-400';
      case 'error':
        return 'text-red-400';
      default:
        return 'text-yellow-400';
    }
  };

  const getStatusDot = (status: PlatformInfo['status']) => {
    switch (status) {
      case 'connected':
        return 'bg-green-400';
      case 'disconnected':
        return 'bg-gray-500';
      case 'error':
        return 'bg-red-400';
      default:
        return 'bg-yellow-400';
    }
  };

  return (
    <div className="p-4 overflow-auto h-full space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-cyan-400 text-sm font-medium">平台管理</div>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-gray-400">
            总计 <span className="text-white">{stats.total}</span>
          </span>
          <span className="text-green-400">
            已连接 <span className="text-white">{stats.connected}</span>
          </span>
          <span className="text-cyan-400">
            已启用 <span className="text-white">{stats.enabled}</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {platforms.map((platform) => (
          <motion.div
            key={platform.platform_id}
            className="glass--panel p-4 cursor-pointer"
            whileHover={{ scale: 1.02 }}
            onClick={() => setSelectedPlatform(platform)}
          >
            <div className="flex items-start gap-3">
              <div className="text-2xl">
                {PLATFORM_ICONS[platform.platform_id] || '🌐'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-white font-medium truncate">
                    {PLATFORM_NAMES[platform.platform_id] || platform.platform_id}
                  </span>
                  <span className={`w-2 h-2 rounded-full ${getStatusDot(platform.status)}`} />
                </div>
                <div className={`text-xs ${getStatusColor(platform.status)}`}>
                  {platform.status === 'connected'
                    ? '已连接'
                    : platform.status === 'disconnected'
                    ? '未连接'
                    : platform.status === 'error'
                    ? '连接错误'
                    : '未知状态'}
                </div>
                <div className="text-gray-500 text-xs truncate mt-1">
                  {platform.platform_id}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 mt-3">
              <motion.button
                className={`px-3 py-1 text-xs rounded ${
                  platform.status === 'connected'
                    ? 'bg-red-500/20 text-red-400'
                    : 'bg-green-500/20 text-green-400'
                }`}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={(e) => {
                  e.stopPropagation();
                  handleConnect(platform);
                }}
              >
                {platform.status === 'connected' ? '断开' : '连接'}
              </motion.button>
              <motion.button
                className="px-3 py-1 text-xs rounded bg-cyan-500/20 text-cyan-400"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedPlatform(platform);
                }}
              >
                配置
              </motion.button>
            </div>
          </motion.div>
        ))}

        <motion.div
          className="glass-panel p-4 flex items-center justify-center cursor-pointer border-dashed border-2 border-gray-600"
          whileHover={{ scale: 1.02, borderColor: '#22d3ee' }}
          onClick={() => setShowAddDialog(true)}
        >
          <div className="text-center">
            <div className="text-3xl text-gray-500">+</div>
            <div className="text-gray-500 text-sm">添加平台</div>
          </div>
        </motion.div>
      </div>

      <AnimatePresence>
        {selectedPlatform && (
          <motion.div
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelectedPlatform(null)}
          >
            <motion.div
              className="glass-panel p-6 w-full max-w-md mx-4"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="text-3xl">
                  {PLATFORM_ICONS[selectedPlatform.platform_id] || '🌐'}
                </div>
                <div>
                  <div className="text-white font-medium">
                    {PLATFORM_NAMES[selectedPlatform.platform_id] ||
                      selectedPlatform.platform_id}
                  </div>
                  <div className="text-gray-400 text-sm">
                    {selectedPlatform.platform_id}
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400 text-sm">状态</span>
                  <span className={getStatusColor(selectedPlatform.status)}>
                    {selectedPlatform.status === 'connected'
                      ? '已连接'
                      : selectedPlatform.status === 'disconnected'
                      ? '未连接'
                      : '错误'}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-gray-400 text-sm">启用</span>
                  <span className={selectedPlatform.enabled ? 'text-green-400' : 'text-gray-500'}>
                    {selectedPlatform.enabled ? '是' : '否'}
                  </span>
                </div>

                {Object.entries(selectedPlatform.config || {}).map(
                  ([key, value]) => (
                    <div
                      key={key}
                      className="flex items-center justify-between"
                    >
                      <span className="text-gray-400 text-sm">{key}</span>
                      <span className="text-white text-sm truncate max-w-48">
                        {String(value).slice(0, 20)}
                        {String(value).length > 20 ? '...' : ''}
                      </span>
                    </div>
                  )
                )}
              </div>

              <div className="flex items-center gap-2 mt-6">
                <motion.button
                  className="flex-1 px-4 py-2 text-sm rounded bg-gray-500/20 text-gray-400"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setSelectedPlatform(null)}
                >
                  关闭
                </motion.button>
                <motion.button
                  className={`flex-1 px-4 py-2 text-sm rounded ${
                    selectedPlatform.status === 'connected'
                      ? 'bg-red-500/20 text-red-400'
                      : 'bg-green-500/20 text-green-400'
                  }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    handleConnect(selectedPlatform);
                    setSelectedPlatform(null);
                  }}
                >
                  {selectedPlatform.status === 'connected' ? '断开连接' : '连接'}
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}

        {showAddDialog && (
          <motion.div
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowAddDialog(false)}
          >
            <motion.div
              className="glass-panel p-6 w-full max-w-sm mx-4"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="text-white font-medium mb-4">添加平台</div>
              <div className="text-gray-400 text-sm mb-4">
                请在配置文件中添加平台配置后重启服务，或通过后端 API 添加
              </div>
              <div className="text-gray-500 text-xs mb-4">
                支持：QQ官方机器人、Telegram、Discord、企业微信等
              </div>
              <motion.button
                className="w-full px-4 py-2 text-sm rounded bg-cyan-500/20 text-cyan-400"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setShowAddDialog(false)}
              >
                知道了
              </motion.button>
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

export default PlatformPage;