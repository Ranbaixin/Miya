// ============================================================
// 弥娅 仪表盘 · 樱梦琉璃
// ============================================================
import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useMiyaConnection, useModels, useAgents, useEmotion, useMemory, usePersonality, fetchDashboard } from '../services/miyaApi';

const StatCard: React.FC<{ label: string; value: string | number; sub?: string; accent?: string; icon?: string; delay?: number }> = ({ label, value, sub, accent = 'text-[#d4789e]', icon, delay = 0 }) => (
  <motion.div className="frost-panel p-3 cursor-default" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: delay * 0.04, duration: 0.35 }} whileHover={{ borderColor: 'rgba(240,168,192,0.3)', y: -1 }}>
    <div className="flex items-center justify-between mb-1"><span className="text-[10px] text-[#b8aec8] uppercase tracking-widest">{label}</span>{icon && <span className="text-sm opacity-60">{icon}</span>}</div>
    <div className={`text-xl font-bold font-mono tracking-tight ${accent}`}>{value}</div>
    {sub && <div className="text-[10px] text-[#b8aec8] mt-0.5">{sub}</div>}
  </motion.div>
);

const SubChip: React.FC<{ name: string; on: boolean; desc: string; delay: number }> = ({ name, on, desc, delay }) => (
  <motion.div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[10px] ${on ? 'bg-[rgba(167,243,208,0.08)] border-[rgba(167,243,208,0.2)] text-[#7dd3a8]' : 'bg-[rgba(229,217,232,0.2)] border-[rgba(229,217,232,0.3)] text-[#d0c4d8]'}`} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 + delay * 0.04 }}>
    <div className={`w-1.5 h-1.5 rounded-full ${on ? 'bg-[#a7f3d0] shadow-[0_0_5px_rgba(167,243,208,0.4)]' : 'bg-[#e5d9e8]'}`} /><span className="font-medium">{name}</span><span className="text-[9px] opacity-50 ml-auto">{desc}</span>
  </motion.div>
);

const DashboardPage: React.FC = () => {
  const { connected } = useMiyaConnection();
  const { models } = useModels();
  const { agents } = useAgents();
  const { emotion } = useEmotion();
  const { stats: memStats } = useMemory();
  const { personality } = usePersonality();
  const [subsystems, setSubsystems] = useState({ mlink: true, memorynet: true, toolnet: true, webnet: true, qqnet: true, tts: true, scheduler: true, proactive: true });
  const [uptime, setUptime] = useState(0);

  useEffect(() => { const t = setInterval(() => setUptime(u => u + 1), 1000); return () => clearInterval(t); }, []);
  useEffect(() => { fetchDashboard().then(d => { if (d?.subsystems) setSubsystems(d.subsystems); }); }, []);

  const fmt = (s: number) => { const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60; return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`; };
  const emotionEntries = emotion?.emotions ? Object.entries(emotion.emotions).sort(([,a], [,b]) => b - a) : [];
  const dominantEmotion = emotionEntries[0]?.[0] || '—';
  const activeModels = models.filter((m: any) => m.status === 'active').length;
  const totalTools = agents.reduce((s: number, a: any) => s + (a.tool_count || 0), 0);

  return (
    <div className="p-3 overflow-auto h-full space-y-3">
      <motion.div className="flex items-center gap-2" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <span className="text-[10px] text-[#b8aec8] uppercase tracking-[0.2em]">◈ 系统概览</span>
        <div className="flex-1 data-stream" />
      </motion.div>

      <div className="grid grid-cols-6 gap-2">
        <StatCard label="连接" value={connected ? 'ONLINE' : 'OFFLINE'} accent={connected ? 'text-[#a7f3d0]' : 'text-[#d0c4d8]'} delay={0} />
        <StatCard label="运行" value={fmt(uptime)} sub="弥娅 v6.0" delay={1} />
        <StatCard label="模型池" value={activeModels || 12} accent="text-[#c4b5fd]" sub={`/ ${models.length || 12} 可用`} delay={2} />
        <StatCard label="Agent" value={agents.length || 5} accent="text-[#93c5fd]" sub={`${totalTools || 69} 工具`} delay={3} />
        <StatCard label="记忆" value={memStats.total || 0} sub={`L:${memStats.long_term || 0} S:${memStats.short_term || 0}`} delay={4} />
        <StatCard label="情绪" value={dominantEmotion} accent="text-[#f0a8c0]" sub={emotion?.intensity ? `强度 ${emotion.intensity}%` : undefined} delay={5} />
      </div>

      <div>
        <div className="text-[10px] text-[#b8aec8] uppercase tracking-widest mb-1.5">子系统</div>
        <div className="grid grid-cols-8 gap-1">
          {[['MLink',subsystems.mlink,'总线'],['MemNet',subsystems.memorynet,'记忆'],['ToolNet',subsystems.toolnet,'工具'],['WebNet',subsystems.webnet,'Web'],['QQNet',subsystems.qqnet,'QQ'],['TTS',subsystems.tts,'语音'],['调度',subsystems.scheduler,'定时'],['主动',subsystems.proactive,'聊天']].map(([n,s,d],i)=><SubChip key={n} name={n!} on={s as boolean} desc={d!} delay={i} />)}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <motion.div className="frost-panel p-3" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
          <div className="text-[10px] text-[#b8aec8] uppercase tracking-widest mb-2">♥ 灵魂</div>
          {emotion ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2"><span className="text-lg font-bold text-[#f0a8c0]">{dominantEmotion}</span><span className="text-[10px] text-[#b8aec8]">[{emotion.intensity}%]</span></div>
              {emotionEntries.length > 1 && <div className="flex gap-1.5 flex-wrap">{emotionEntries.slice(1,4).map(([k,v])=><span key={k} className="text-[10px] px-2 py-0.5 rounded-lg bg-[rgba(240,168,192,0.1)] text-[#f0a8c0] border border-[rgba(240,168,192,0.15)]">{k} {v}%</span>)}</div>}
              {emotion.inner_thought && <div className="text-[10px] text-[#887c9e] italic border-l-2 border-[rgba(240,168,192,0.3)] pl-2 py-0.5">"{emotion.inner_thought}"</div>}
            </div>
          ) : <div className="text-[#b8aec8] text-xs">✦ 等待数据...</div>}
        </motion.div>

        <motion.div className="frost-panel p-3" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }}>
          <div className="text-[10px] text-[#b8aec8] uppercase tracking-widest mb-2">◇ 人格</div>
          {personality?.vectors?.length ? (
            <div className="space-y-2">
              <div className="text-xs text-[#d4789e] mb-1">{personality.current_form} · {personality.description||''}</div>
              {personality.vectors.map((v: any) => <div key={v.name} className="flex items-center gap-2"><span className="text-[10px] text-[#b8aec8] w-10 text-right">{v.name}</span><div className="flex-1 h-1.5 bg-[rgba(240,168,192,0.1)] rounded-full overflow-hidden"><motion.div className="h-full rounded-full" style={{background:'linear-gradient(90deg, rgba(240,168,192,0.8), rgba(196,181,253,0.7))'}} initial={{width:0}} animate={{width:`${(v.value/v.max)*100}%`}} transition={{duration:0.6,delay:0.8}}/></div><span className="text-[10px] text-[#887c9e] w-8 font-mono">{v.value.toFixed(2)}</span></div>)}
            </div>
          ) : <div className="text-[#b8aec8] text-xs">等待数据...</div>}
        </motion.div>
      </div>
    </div>
  );
};

export default DashboardPage;
