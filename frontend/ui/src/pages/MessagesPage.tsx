import { useState } from 'react';
import type { ChatMessage } from '../hooks/useMiyaQQData';

interface Message {
  id: string;
  type: 'private' | 'group';
  from: string;
  name: string;
  content: string;
  time: string;
}

interface MessagesPageProps {
  messages?: ChatMessage[];
}

const defaultMessages: Message[] = [
  { id: '1', type: 'private', from: '1523878699', name: '然鑫', content: '晚安', time: '23:55:06' },
  { id: '2', type: 'private', from: '1523878699', name: '然鑫', content: '新的一天开始了', time: '00:00:25' },
  { id: '3', type: 'group', from: '123456789', name: '索多玛', content: '有人打资本帝王吗', time: '14:30:22' },
  { id: '4', type: 'group', from: '987654321', name: '水群', content: '今天的天气不错', time: '15:45:10' },
  { id: '5', type: 'private', from: '1523878699', name: '然鑫', content: '今天工作好累', time: '18:20:33' },
  { id: '6', type: 'private', from: '1523878699', name: '然鑫', content: '早点休息', time: '18:20:45' },
];

const MessagesPage: React.FC<MessagesPageProps> = ({ 
  messages: propMessages
}) => {
  const [filter, setFilter] = useState<'all' | 'private' | 'group'>('all');
  const [search, setSearch] = useState('');
  const [selectedMsg, setSelectedMsg] = useState<string | null>(null);

  const messages = propMessages?.map(m => ({
    id: m.id,
    type: 'private' as const,
    from: m.role === 'user' ? '1523878699' : 'self',
    name: m.role === 'user' ? '然鑫' : '弥娅',
    content: m.content,
    time: m.time,
  })) || defaultMessages;

  let filtered = filter === 'all' ? messages : messages.filter(m => m.type === filter);
  
  if (search.trim()) {
    filtered = filtered.filter(m => 
      m.content.toLowerCase().includes(search.toLowerCase()) ||
      m.name.toLowerCase().includes(search.toLowerCase())
    );
  }

  const counts = {
    all: messages.length,
    private: messages.filter(m => m.type === 'private').length,
    group: messages.filter(m => m.type === 'group').length,
  };

  return (
    <div className="flex h-full p-4 gap-4">
      <div className="w-48 glass-panel p-3 space-y-3">
        <div className="text-white font-medium text-sm">消息筛选</div>
        <div className="space-y-1">
          {[
            { id: 'all', label: '全部', count: counts.all },
            { id: 'private', label: '私聊', count: counts.private },
            { id: 'group', label: '群聊', count: counts.group },
          ].map(item => (
            <button
              key={item.id}
              onClick={() => setFilter(item.id as 'all' | 'private' | 'group')}
              className={`w-full text-left px-3 py-2 rounded text-sm flex justify-between ${
                filter === item.id 
                  ? 'bg-cyan-500/20 text-cyan-400' 
                  : 'text-gray-400 hover:bg-white/5'
              }`}
            >
              <span>{item.label}</span>
              <span className="text-xs opacity-60">{item.count}</span>
            </button>
          ))}
        </div>

        <div className="pt-2 border-t border-cyan-500/20">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索消息..."
            className="w-full bg-black/20 rounded px-2 py-1 text-xs text-gray-300 outline-none"
          />
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="space-y-2">
          {filtered.length > 0 ? (
            filtered.map(msg => (
              <div 
                key={msg.id}
                onClick={() => setSelectedMsg(msg.id)}
                className={`glass-panel p-3 cursor-pointer transition-all ${
                  selectedMsg === msg.id ? 'border-cyan-500' : ''
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      msg.type === 'private' ? 'bg-cyan-500' : 'bg-purple-500'
                    }`} />
                    <span className="text-white font-medium text-sm">{msg.name}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-black/20 text-gray-500">
                      {msg.type === 'private' ? '私聊' : '群聊'}
                    </span>
                  </div>
                  <span className="text-cyan-600 text-xs">{msg.time}</span>
                </div>
                <div className="text-gray-300 text-sm line-clamp-2">{msg.content}</div>
              </div>
            ))
          ) : (
            <div className="glass-panel p-8 text-center text-gray-500">
              没有找到消息
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessagesPage;