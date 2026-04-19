

interface QuickActionsProps {
  onSendMessage?: (msg: string) => void;
}

const QuickActionsPanel: React.FC<QuickActionsProps> = ({ onSendMessage }) => {
  const actions = [
    { label: '戳一戳', icon: '👋', action: '戳' },
    { label: '点赞', icon: '👍', action: '点赞' },
    { label: '早安', icon: '🌅', action: '早安' },
    { label: '晚安', icon: '🌙', action: '晚安' },
    { label: '抱抱', icon: '🤗', action: '抱抱' },
    { label: '亲亲', icon: '💋', action: '亲亲' },
  ];

  return (
    <div className="glass-panel p-4">
      <div className="text-cyan-400 text-xs mb-3">快捷动作</div>
      <div className="grid grid-cols-3 gap-2">
        {actions.map((item) => (
          <button
            key={item.action}
            onClick={() => onSendMessage?.(item.action)}
            className="p-2 rounded border border-cyan-500/20 hover:border-cyan-500/50 hover:bg-cyan-500/10 transition-all text-xs text-gray-300"
          >
            <span className="text-lg block mb-1">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default QuickActionsPanel;