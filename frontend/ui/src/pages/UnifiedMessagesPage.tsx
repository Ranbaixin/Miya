import { useState, useEffect } from 'react';
import { miyaAPI } from '../services/miyaApi';

interface UnifiedMessage {
  id: string;
  platform: string;
  platform_name: string;
  content: string;
  sender: string;
  sender_id: string;
  group_id?: string;
  group_name?: string;
  timestamp: string;
  type: 'text' | 'image' | 'file' | 'system';
}

const PLATFORM_ICONS: Record<string, string> = {
  qqofficial: '🐧',
  aiocqhttp: '🐧',
  webchat: '🌐',
  telegram: '✈️',
  discord: '🎮',
  default: '💬',
};

const PLATFORM_COLORS: Record<string, string> = {
  qqofficial: 'bg-green-600',
  aiocqhttp: 'bg-green-600',
  webchat: 'bg-blue-600',
  telegram: 'bg-blue-500',
  discord: 'bg-indigo-600',
  default: 'bg-gray-600',
};

const UnifiedMessagesPage: React.FC = () => {
  const [messages, setMessages] = useState<UnifiedMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all');
  const [platforms, setPlatforms] = useState<string[]>([]);

  useEffect(() => {
    loadMessages();
    const interval = setInterval(loadMessages, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    loadPlatforms();
  }, []);

  const loadPlatforms = async () => {
    try {
      const res = await miyaAPI.getPlatformStats();
      if (res?.platforms) {
        const online = res.platforms
          .filter((p: any) => p.status === 'running' || p.status === 'online')
          .map((p: any) => p.id);
        setPlatforms(['all', ...online]);
      }
    } catch (e) {
      console.log('获取平台失败');
    }
  };

  const loadMessages = async () => {
    try {
      const messagesData: UnifiedMessage[] = [];

      try {
        const sessions = await miyaAPI.getChatSessions();
        if (sessions?.data) {
          for (const session of sessions.data) {
            messagesData.push({
              id: session.session_id,
              platform: 'webchat',
              platform_name: '网页聊天',
              content: `会话: ${session.display_name}`,
              sender: '系统',
              sender_id: 'system',
              timestamp: session.created_at,
              type: 'system',
            });
          }
        }
      } catch (e) {
        console.log('加载聊天会话失败');
      }

      setMessages(messagesData.sort((a, b) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      ).slice(0, 50));
    } catch (e) {
      console.log('加载消息失败');
    } finally {
      setLoading(false);
    }
  };

  const filteredMessages = selectedPlatform === 'all'
    ? messages
    : messages.filter(m => m.platform === selectedPlatform);

  const getPlatformIcon = (platform: string) => {
    return PLATFORM_ICONS[platform] || PLATFORM_ICONS.default;
  };

  const getPlatformColor = (platform: string) => {
    return PLATFORM_COLORS[platform] || PLATFORM_COLORS.default;
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return date.toLocaleDateString('zh-CN');
  };

  return (
    <div className="p-4 overflow-auto h-full space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-cyan-400 text-sm font-medium">统一消息流</div>
        <div className="flex items-center gap-2">
          <select
            value={selectedPlatform}
            onChange={(e) => setSelectedPlatform(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300"
          >
            {platforms.map(p => (
              <option key={p} value={p}>
                {p === 'all' ? '全部平台' : (PLATFORM_ICONS[p] || '💬') + ' ' + p}
              </option>
            ))}
          </select>
          <button
            onClick={loadMessages}
            className="text-cyan-400 text-xs hover:text-cyan-300"
          >
            刷新
          </button>
        </div>
      </div>

      <div className="text-xs text-gray-500 mb-2">
        聚合来自所有已连接平台的消息 ({filteredMessages.length} 条)
      </div>

      {loading && messages.length === 0 ? (
        <div className="text-gray-500 text-center text-xs py-8">
          加载中...
        </div>
      ) : filteredMessages.length === 0 ? (
        <div className="glass-panel p-4 text-center">
          <div className="text-gray-500 text-xs">暂无消息</div>
          <div className="text-gray-600 text-xs mt-2">
            消息将在这里聚合显示
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredMessages.map((msg) => (
            <div
              key={msg.id}
              className="glass-panel p-3 flex gap-3"
            >
              <div className={`w-8 h-8 rounded-full ${getPlatformColor(msg.platform)} flex items-center justify-center text-white text-xs`}>
                {getPlatformIcon(msg.platform)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-gray-400">{msg.sender}</span>
                  <span className="text-gray-600">•</span>
                  <span className="text-cyan-400">{msg.platform_name}</span>
                  <span className="text-gray-600">•</span>
                  <span className="text-gray-500">{formatTime(msg.timestamp)}</span>
                </div>
                <div className="text-gray-300 text-sm mt-1 truncate">
                  {msg.content}
                </div>
                {msg.group_name && (
                  <div className="text-gray-500 text-xs mt-1">
                    来自群: {msg.group_name}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default UnifiedMessagesPage;