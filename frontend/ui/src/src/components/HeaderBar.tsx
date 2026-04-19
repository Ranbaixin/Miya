import { useState, useEffect } from 'react';

interface HeaderBarProps {
  identity?: {
    name: string;
    version: string;
    form: string;
  };
  connected?: boolean;
}

const HeaderBar: React.FC<HeaderBarProps> = ({ identity, connected }) => {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (d: Date) => {
    return d.toLocaleTimeString('zh-CN', { hour12: false });
  };

  return (
    <div className="flex items-center justify-between px-4 py-2 glass-panel border-b border-cyan-500/20">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'} animate-pulse-glow`} />
          <span className="text-cyan-300 font-bold text-sm tracking-wider">MIYA</span>
        </div>
        <span className="text-gray-500 text-xs">|</span>
        <span className="text-cyan-100/70 text-xs">{identity?.name || '弥娅·阿尔缪斯'}</span>
        {identity?.form && (
          <>
            <span className="text-gray-500 text-xs">|</span>
            <span className="text-purple-400 text-xs">{identity.form}</span>
          </>
        )}
      </div>
      
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-cyan-100/60 text-xs">
          <span>{formatTime(time)}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-400' : 'bg-yellow-400'} animate-pulse`} />
          <span className="text-xs text-cyan-100/60">{connected ? '已连接' : '连接中...'}</span>
        </div>
      </div>
    </div>
  );
};

export default HeaderBar;