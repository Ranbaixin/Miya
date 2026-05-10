// ============================================================
// 深蓝星渊 · StatusBar — 底部状态栏
// ============================================================

interface StatusBarProps {
  connected: boolean;
  runtimeDuration: number;
  subsystems?: {
    mlink: boolean; memorynet: boolean; toolnet: boolean;
    webnet: boolean; qqnet: boolean; tts: boolean;
    scheduler: boolean; proactive: boolean;
  };
  memoryStats?: { total: number; long_term: number; short_term: number; emotional: number };
}

const Dot: React.FC<{ on: boolean; label: string }> = ({ on, label }) => (
  <div className="flex items-center gap-1">
    <div className={`pulse-dot ${on ? 'on' : 'off'}`} />
    <span className="text-[9px] text-text-dim">{label}</span>
  </div>
);

const StatusBar: React.FC<StatusBarProps> = ({ connected, runtimeDuration, subsystems, memoryStats }) => {
  const fmt = (s: number) => {
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
  };
  const ss = subsystems || { mlink: false, memorynet: false, toolnet: false, webnet: false, qqnet: false, tts: false, scheduler: false, proactive: false };

  return (
    <div className="h-7 bg-void-panel backdrop-blur-xl flex items-center justify-between px-3 border-t border-border-glass text-[10px] font-mono z-20 relative shrink-0">
      <div className="flex items-center gap-2.5">
        <span className={connected ? 'text-status-active' : 'text-text-dim'}>
          {connected ? '● 已共鸣' : '○ 未连接'}
        </span>
        <span className="text-border-glass">|</span>
        <Dot on={ss.mlink} label="MLink" />
        <Dot on={ss.memorynet} label="MemNet" />
        <Dot on={ss.toolnet} label="ToolNet" />
        <Dot on={ss.webnet} label="WebNet" />
        <Dot on={ss.qqnet} label="QQNet" />
        <Dot on={ss.tts} label="TTS" />
        <Dot on={ss.scheduler} label="Sched" />
        <Dot on={ss.proactive} label="Active" />
      </div>
      <div className="flex items-center gap-2.5 text-text-dim">
        {memoryStats && (
          <span>
            记忆: <span className="text-aether">{memoryStats.total}</span>
            <span className="text-text-dim/50"> L:</span><span className="text-resonance-bright">{memoryStats.long_term}</span>
            <span className="text-text-dim/50"> S:</span><span className="text-aether-bright">{memoryStats.short_term}</span>
          </span>
        )}
        <span className="text-text-dim/30">|</span>
        <span>↑ {fmt(runtimeDuration)}</span>
      </div>
    </div>
  );
};

export default StatusBar;
