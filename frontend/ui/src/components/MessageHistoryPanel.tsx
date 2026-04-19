const MessageHistoryPanel: React.FC = () => {
  const messages = [
    { time: '16:13', from: '佳', msg: '嗯呐……', type: 'recv' },
    { time: '15:31', from: '弥娅', msg: '不反感。因为是你。', type: 'send' },
    { time: '15:31', from: '佳', msg: '可是……这是不正经的RPG哇……', type: 'recv' },
    { time: '15:29', from: '佳', msg: '唔……弥娅…你…嘿嘿……', type: 'recv' },
    { time: '15:28', from: '弥娅', msg: '如果是我，我会认真扮演好那个角色。', type: 'send' },
    { time: '15:28', from: '佳', msg: '玩的不正经的RPG里的女主角是你……', type: 'recv' },
  ];

  return (
    <div className="glass-panel p-4">
      <div className="text-cyan-400 text-xs mb-3">最近消息</div>
      <div className="space-y-2 max-h-48 overflow-auto">
        {messages.map((msg, i) => (
          <div key={i} className={`text-xs ${msg.type === 'send' ? 'text-right' : 'text-left'}`}>
            <span className="text-cyan-600">{msg.time}</span>
            <span className={`mx-2 ${msg.type === 'send' ? 'text-pink-400' : 'text-cyan-400'}`}>
              {msg.type === 'send' ? '弥娅' : msg.from}
            </span>
            <span className="text-gray-300">{msg.msg}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MessageHistoryPanel;