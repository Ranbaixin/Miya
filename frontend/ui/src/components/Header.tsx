// ============================================================
// 弥娅 头部 · 樱梦琉璃
// ============================================================
import { useState, useEffect } from 'react';

interface HeaderProps {
  title: string; connected?: boolean; modelCount?: number; queueSize?: number;
  currentEmotion?: string; emotionIntensity?: number; currentForm?: string; uptime?: string;
}

const Header: React.FC<HeaderProps> = ({
  title, connected = false, modelCount = 0, queueSize = 0,
  currentEmotion = '—', emotionIntensity = 0, currentForm = '—', uptime = '—',
}) => {
  const [time, setTime] = useState('');
  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
    tick(); const t = setInterval(tick, 1000); return () => clearInterval(t);
  }, []);

  return (
    <div className="h-10 bg-[rgba(255,255,255,0.7)] backdrop-blur-xl flex items-center justify-between px-4 border-b border-[rgba(240,168,192,0.1)] z-10 relative">
      <div className="flex items-center gap-3">
        <div className={`w-2 h-2 rounded-full ${connected ? 'bg-[#a7f3d0] shadow-[0_0_6px_rgba(167,243,208,0.5)] animate-pulse' : 'bg-[#e5d9e8]'}`} />
        <span className="text-[#d4789e] text-xs font-medium tracking-wide">{title}</span>
      </div>

      <div className="flex items-center gap-3 text-[10px] font-mono text-[#b8aec8]">
        <span>形态</span><span className="text-[#c4b5fd]">{currentForm}</span>
        <span className="w-px h-3 bg-[rgba(240,168,192,0.15)]" />
        <span>情绪</span><span className="text-[#f0a8c0]">{currentEmotion}</span>
        <span>[{emotionIntensity}%]</span>
        <span className="w-px h-3 bg-[rgba(240,168,192,0.15)]" />
        <span>模型</span><span className="text-[#c4b5fd]">{modelCount}</span>
        <span className="w-px h-3 bg-[rgba(240,168,192,0.15)]" />
        <span>队列</span><span className={queueSize > 0 ? 'text-[#fcd4b6]' : ''}>{queueSize}</span>
        <span className="w-px h-3 bg-[rgba(240,168,192,0.15)]" />
        <span className="text-[#887c9e]">{time}</span>
        <span className="text-[#b8aec8] text-[9px]">↑ {uptime}</span>
      </div>
    </div>
  );
};

export default Header;
