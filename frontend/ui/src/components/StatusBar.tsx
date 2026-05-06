// ============================================================
// 弥娅 底部状态栏 · 樱梦琉璃
// ============================================================
interface StatusBarProps {
  connected: boolean; runtimeDuration: number;
  subsystems?: { mlink: boolean; memorynet: boolean; toolnet: boolean; webnet: boolean; qqnet: boolean; tts: boolean; scheduler: boolean; proactive: boolean };
  memoryStats?: { total: number; long_term: number; short_term: number; emotional: number };
}

const Dot: React.FC<{ on: boolean; label: string }> = ({ on, label }) => (
  <div className="flex items-center gap-1">
    <div className={`w-1.5 h-1.5 rounded-full ${on ? 'bg-[#a7f3d0] shadow-[0_0_4px_rgba(167,243,208,0.4)]' : 'bg-[#e5d9e8]'}`} />
    <span className="text-[9px] text-[#b8aec8]">{label}</span>
  </div>
);

const StatusBar: React.FC<StatusBarProps> = ({ connected, runtimeDuration, subsystems, memoryStats }) => {
  const fmt = (s: number) => {
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
  };
  const ss = subsystems || { mlink: false, memorynet: false, toolnet: false, webnet: false, qqnet: false, tts: false, scheduler: false, proactive: false };

  return (
    <div className="h-6 bg-[rgba(255,255,255,0.75)] backdrop-blur-xl flex items-center justify-between px-3 border-t border-[rgba(240,168,192,0.1)] text-[10px] font-mono z-10 relative">
      <div className="flex items-center gap-3">
        <span className={connected ? 'text-[#a7f3d0]' : 'text-[#e5d9e8]'}>
          {connected ? '● ONLINE' : '○ OFFLINE'}
        </span>
        <span className="text-[rgba(240,168,192,0.2)]">|</span>
        <Dot on={ss.mlink} label="MLink" />
        <Dot on={ss.memorynet} label="MemNet" />
        <Dot on={ss.toolnet} label="ToolNet" />
        <Dot on={ss.qqnet} label="QQNet" />
        <Dot on={ss.webnet} label="WebNet" />
        <Dot on={ss.tts} label="TTS" />
        <Dot on={ss.scheduler} label="Sched" />
        <Dot on={ss.proactive} label="Active" />
      </div>
      <div className="flex items-center gap-3 text-[#b8aec8]">
        {memoryStats && (
          <span>
            记忆: <span className="text-[#d4789e]">{memoryStats.total}</span>
            <span className="text-[#d8d0e0]"> L:</span><span className="text-[#c4b5fd]">{memoryStats.long_term}</span>
            <span className="text-[#d8d0e0]"> S:</span><span className="text-[#93c5fd]">{memoryStats.short_term}</span>
          </span>
        )}
        <span>↑ {fmt(runtimeDuration)}</span>
      </div>
    </div>
  );
};

export default StatusBar;
