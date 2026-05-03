import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const defaultMessages = [
  { id: '1', sender: 'user', content: '你好呀弥娅', time: '14:30' },
  { id: '2', sender: 'miya', content: '你好呀亲爱的~ 欢迎回来', time: '14:30' },
  { id: '3', sender: 'user', content: '今天过得怎么样？', time: '14:31' },
  { id: '4', sender: 'miya', content: '还不错呀～ 处理了一些事情，现在在等你呢', time: '14:31' },
];

const defaultSessions = [
  { id: 'default', name: '默认会话', updated_at: '2026-05-02T14:31:00' },
  { id: 'session_2', name: '关于AI的讨论', updated_at: '2026-05-02T12:00:00' },
];

const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState(defaultMessages);
  const [input, setInput] = useState('');
  const [sessions, setSessions] = useState(defaultSessions);
  const [currentSession, setCurrentSession] = useState('default');
  const [sending, setSending] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    
    setSending(true);
    const userMsg = {
      id: `msg_${Date.now()}`,
      sender: 'user',
      content: input,
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages(prev => [...prev, userMsg]);
    const msgToSend = input;
    setInput('');

    setTimeout(() => {
      const miyaMsg = {
        id: `msg_${Date.now()}_miya`,
        sender: 'miya',
        content: '收到你的消息啦~ 具体内容需要连接真实后端API才能回复呢',
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages(prev => [...prev, miyaMsg]);
      setSending(false);
    }, 500);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full">
      <div className="w-48 bg-gray-900/50 border-r border-gray-800 p-2">
        <div className="text-gray-400 text-xs mb-2 px-2">会话列表</div>
        {sessions.map(s => (
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
        ))}
      </div>

      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map(msg => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-[70%] rounded-2xl px-4 py-2 ${
                msg.sender === 'user'
                  ? 'bg-cyan-500/30 text-white rounded-br-md'
                  : 'bg-gray-800/50 text-gray-200 rounded-bl-md'
              }`}>
                <div className="text-sm">{msg.content}</div>
                <div className={`text-xs mt-1 ${
                  msg.sender === 'user' ? 'text-cyan-300/50' : 'text-gray-500'
                }`}>{msg.time}</div>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="p-4 border-t border-gray-800">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
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