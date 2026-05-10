// ============================================================
// 深蓝星渊 · Header — 顶部栏 · MIYA 身份 & 实时状态
// ============================================================
import { useState, useEffect } from 'react';

interface HeaderProps {
  connected?: boolean;
  modelCount?: number;
  queueSize?: number;
  currentEmotion?: string;
  emotionIntensity?: number;
  currentForm?: string;
  uptime?: string;
}

const Header: React.FC<HeaderProps> = ({
  connected = false, modelCount = 0, queueSize = 0,
  currentEmotion = '—', emotionIntensity = 0, currentForm = '—', uptime = '—',
}) => {
  const [time, setTime] = useState('');
  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
    tick(); const t = setInterval(tick, 1000); return () => clearInterval(t);
  }, []);

  return (
    <div className="h-11 bg-void-panel backdrop-blur-xl flex items-center justify-between px-4 border-b border-border-glass z-20 relative shrink-0">
      {/* 左侧: MIYA 品牌 */}
      <div className="flex items-center gap-3">
        {/* 共鸣核心 */}
        <div className="w-7 h-7 rounded-lg flex items-center justify-center relative"
          style={{
            background: 'linear-gradient(135deg, rgba(0, 229, 255, 0.2), rgba(124, 77, 255, 0.2))',
            border: '1px solid rgba(0, 229, 255, 0.25)',
          }}
        >
          <span className="text-xs font-bold text-aether-bright z-10">M</span>
          <div className="absolute inset-0 rounded-lg bg-aether/5 animate-pulse-energy" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-xs font-bold text-text-primary tracking-wider">MIYA · 弥娅</span>
          <span className="text-[9px] text-text-dim">深蓝星渊 v7.0</span>
        </div>
      </div>

      {/* 中间: 形态 & 情绪 */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-text-dim">形态</span>
          <span className="text-xs font-medium text-resonance-bright">{currentForm}</span>
        </div>
        <div className="w-px h-4 bg-border-glass" />
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-text-dim">情绪</span>
          <span className="text-xs font-medium text-aether">{currentEmotion}</span>
          <span className="text-[10px] text-text-dim">[{emotionIntensity}%]</span>
        </div>
      </div>

      {/* 右侧: 系统信息 */}
      <div className="flex items-center gap-3 text-[10px] font-mono text-text-dim">
        <div className={cn('w-1.5 h-1.5 rounded-full', connected ? 'bg-status-active shadow-[0_0_6px_rgba(76,255,141,0.4)]' : 'bg-status-idle')} />
        <span className={connected ? 'text-status-active' : 'text-text-dim'}>{connected ? 'ONLINE' : 'OFFLINE'}</span>
        <span className="text-text-dim/30">|</span>
        <span>模型 <span className="text-aether">{modelCount}</span></span>
        <span className="text-text-dim/30">|</span>
        <span>队列 <span className={queueSize > 0 ? 'text-starlight' : 'text-text-dim'}>{queueSize}</span></span>
        <span className="text-text-dim/30">|</span>
        <span>{time}</span>
        <span className="text-text-dim/40 text-[9px]">↑ {uptime}</span>
      </div>
    </div>
  );
};

function cn(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}

export default Header;
