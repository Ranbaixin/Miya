import { useState, useEffect } from 'react';

const FooterBar: React.FC = () => {
  const [statusText, setStatusText] = useState('系统正常');
  const [fps] = useState(60);

  useEffect(() => {
    const texts = ['系统正常', '监听中...', '情绪分析中...', '等待输入'];
    let idx = 0;
    const timer = setInterval(() => {
      idx = (idx + 1) % texts.length;
      setStatusText(texts[idx]);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex items-center justify-between px-4 py-2 glass-panel border-t border-cyan-500/20">
      <div className="flex items-center gap-4">
        <span className="text-cyan-100/40 text-xs font-mono">v4.3.0</span>
        <span className="text-gray-600 text-xs">|</span>
        <span className="text-cyan-100/50 text-xs">{statusText}</span>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1">
          <span className="text-cyan-100/40 text-xs">FPS</span>
          <span className="text-cyan-300 text-xs ml-1">{fps}</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-1 h-1 rounded-full bg-cyan-500/60" />
          <div className="w-1 h-1 rounded-full bg-cyan-500/60" />
          <div className="w-1 h-1 rounded-full bg-cyan-500/40" />
        </div>
      </div>
    </div>
  );
};

export default FooterBar;