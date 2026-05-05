import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useMiyaChat, miyaAPI } from '../services/miyaApi';

interface Session {
  id: string;
  name: string;
  updated_at: string;
}

const ChatPage: React.FC = () => {
  const { messages, send, sending } = useMiyaChat();
  const [input, setInput] = useState('');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState('default');
  const [sessionsLoading, setSessionsLoading] = useState(false);

  useEffect(() => {
    const loadSessions = async () => {
      setSessionsLoading(true);
      const res = await miyaAPI.getChatSessions();
      if (res?.success && res.data) {
        setSessions(res.data);
      }
      setSessionsLoading(false);
    };
    loadSessions();
  }, []);

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    await send(input);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full">
      <div className="w-48 bg-gray-900/50 border-r border-gray-800 p-2 flex flex-col">
        <div className="text-gray-400 text-xs mb-2 px-2">会话列表</div>
        <div className="flex-1 overflow-y-auto">
          {sessionsLoading ? (
            <div className="text-gray-500 text-xs text-center py-4">加载中...</div>
          ) : sessions.length > 0 ? (
            sessions.map(s => (
              <motion.button
                key={s.id}
                onClick={() => setCurrentSession(s.id)}
                className={`w-full text-left px-2 py-2 rounded text-sm mb-1 ${
                  currentSession === s.id
                    ? 'bg-cyan-500/20 text-cyan-400'
                    : 'text-gray-400 hover:bg-gray-800'
                }`}
              >
                {s.name}
              </motion.button>
            ))
          ) : (
            <div className="text-gray-500 text-xs text-center py-4">暂无会话</div>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              发送消息，和弥娅开始对话吧~
            </div>
          )}
          {messages.map(msg => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-[70%] rounded-2xl px-4 py-2 ${
                msg.type === 'user'
                  ? 'bg-cyan-500/30 text-white rounded-br-md'
                  : 'bg-gray-800/50 text-gray-200 rounded-bl-md'
              }`}>
                <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                <div className={`text-xs mt-1 ${
                  msg.type === 'user' ? 'text-cyan-300/50' : 'text-gray-500'
                }`}>{msg.time}</div>
              </div>
            </motion.div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="bg-gray-800/50 text-gray-200 rounded-2xl rounded-bl-md px-4 py-2">
                <div className="text-sm animate-pulse">思考中...</div>
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-800">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入消息..."
              disabled={sending}
              className="flex-1 bg-gray-800/50 border border-gray-700 rounded-full px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
            />
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleSend}
              disabled={!input.trim() || sending}
              className="px-4 py-2 bg-cyan-500/30 border border-cyan-500/50 rounded-full text-cyan-400 hover:bg-cyan-500/40 disabled:opacity-50"
            >
              {sending ? '...' : '发送'}
            </motion.button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;