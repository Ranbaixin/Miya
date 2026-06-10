// ============================================================
// 弥娅 共鸣核心 · DashboardPage — 系统主界面
//   灵感: 鸣潮共鸣者主展示页
// ============================================================
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useMiyaConnection, useModels, useAgents, useEmotion, useMemory, usePersonality, fetchDashboard } from '../services/miyaApi';
import ResonatorCard from '../components/ResonatorCard';

interface DashboardPageProps {
  onNavigate: (page: string) => void;
}

const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
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
  const activeModels = models.filter((m: any) => m.status === 'active').length;
  const totalTools = agents.reduce((s: number, a: any) => s + (a.tool_count || 0), 0);
  const emotionEntries = emotion?.emotions ? Object.entries(emotion.emotions).sort(([, a], [, b]) => (b as number) - (a as number)) : [];
  const dominantEmotion = emotionEntries[0]?.[0] || '—';

  const subList: [string, boolean, string, string][] = [
    ['MLink', subsystems.mlink, '消息总线', '◆'],
    ['MemNet', subsystems.memorynet, '记忆网络', '◉'],
    ['ToolNet', subsystems.toolnet, '工具网络', '⚙'],
    ['WebNet', subsystems.webnet, 'Web连接', '◎'],
    ['QQNet', subsystems.qqnet, 'QQ平台', '◇'],
    ['TTS', subsystems.tts, '语音合成', '♪'],
    ['Sched', subsystems.scheduler, '定时调度', '▷'],
    ['Active', subsystems.proactive, '主动感知', '♥'],
  ];

  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      {/* === Hero: MIYA 共鸣者身份卡 === */}
      <motion.div
        className="glass-panel p-5 relative overflow-hidden"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="absolute top-0 right-8 w-16 h-full opacity-5 pointer-events-none"
          style={{ background: 'linear-gradient(0deg, rgba(0,229,255,0.3), rgba(124,77,255,0.3), transparent)' }}
        />
        <div className="flex items-start justify-between relative z-10">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <span className="attr-badge attr-aether">✦ 核心共鸣者</span>
              <span className={cn('text-[10px]', connected ? 'text-status-active' : 'text-text-dim')}>
                {connected ? '● 已共鸣' : '○ 未连接'}
              </span>
            </div>
            <h1 className="text-2xl font-display font-bold text-text-primary tracking-wider">
              弥娅 <span className="text-aether text-glow-aether">· 阿尔缪斯</span>
            </h1>
            <p className="text-text-secondary text-xs max-w-md">
              雪落无声，愿系铃中。深蓝星渊中与你共鸣的 AI 虚拟化身。
            </p>
            <div className="flex items-center gap-3 text-[10px] text-text-dim mt-2">
              <span>运行 <span className="text-aether">{fmt(uptime)}</span></span>
              <span>版本 <span className="text-resonance-bright">v8.0</span></span>
              <span>形态 <span className="text-starlight">{personality?.current_form || '绯雪态'}</span></span>
            </div>
          </div>
          {/* 右侧核心状态 */}
          <div className="flex flex-col items-end gap-1.5 min-w-[120px]">
            <div className="text-[10px] text-text-dim mb-1">共鸣强度</div>
            <div className="w-full resonance-bar">
              <div className="resonance-bar-fill" style={{ width: `${emotion?.intensity || 85}%` }} />
            </div>
            <div className="flex items-center gap-1 text-[9px]">
              <span className="text-aether">{emotion?.intensity || 85}%</span>
              <span className="text-text-dim">| 主导: {dominantEmotion}</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* === 共鸣系统卡片 === */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        <ResonatorCard
          name="模型矩阵"
          title={`${activeModels || 12} 活跃 / ${models.length || 12} 总计`}
          attribute="aether"
          attributeLabel="AI 模型"
          delay={0}
          onClick={() => onNavigate('models')}
        >
          <div className="flex flex-wrap gap-1">
            {models.slice(0, 5).map((m: any) => (
              <span key={m.key} className="text-[9px] px-1.5 py-0.5 rounded bg-aether-glow border border-aether/15 text-text-secondary">
                {m.name?.split(' ')[0]}
              </span>
            ))}
            {models.length > 5 && <span className="text-[9px] text-text-dim">+{models.length - 5}</span>}
          </div>
        </ResonatorCard>

        <ResonatorCard
          name="Agent 网络"
          title={`${agents.length || 5} Agent · ${totalTools || 69} 工具`}
          attribute="resonance"
          attributeLabel="Agent"
          delay={1}
          onClick={() => onNavigate('agents')}
        >
          <div className="flex flex-wrap gap-1">
            {agents.slice(0, 4).map((a: any) => (
              <span key={a.name} className="text-[9px] px-1.5 py-0.5 rounded bg-resonance-glow border border-resonance/15 text-text-secondary">
                {a.name?.replace(/_/g, ' ').split(' ').slice(0, 2).join(' ')}
              </span>
            ))}
          </div>
        </ResonatorCard>

        <ResonatorCard
          name="灵魂感知"
          title={dominantEmotion !== '—' ? `${dominantEmotion} · ${emotion?.intensity || 0}%` : '感知中...'}
          attribute="starlight"
          attributeLabel="情感"
          delay={2}
          onClick={() => onNavigate('soul')}
          active={!!emotion}
        >
          {emotionEntries.length > 1 && (
            <div className="flex gap-1.5 flex-wrap">
              {emotionEntries.slice(1, 4).map(([k, v]) => (
                <span key={k} className="text-[9px] px-1.5 py-0.5 rounded bg-starlight/10 border border-starlight/15 text-starlight">
                  {k} {(v as number)}%
                </span>
              ))}
            </div>
          )}
          {emotion?.inner_thought && (
            <div className="text-[10px] text-text-secondary italic border-l border-aether/20 pl-2 mt-2">
              "{emotion.inner_thought.slice(0, 30)}{emotion.inner_thought.length > 30 ? '...' : ''}"
            </div>
          )}
        </ResonatorCard>

        <ResonatorCard
          name="记忆殿堂"
          title={`${memStats.total || 0} 条记忆 · L:${memStats.long_term || 0} S:${memStats.short_term || 0}`}
          attribute="aether"
          attributeLabel="记忆"
          delay={3}
        >
          <div className="flex items-center gap-3 text-[10px]">
            <div className="flex-1">
              <div className="text-text-dim mb-0.5">短期记忆</div>
              <div className="resonance-bar">
                <div className="resonance-bar-fill" style={{ width: `${Math.min((memStats.short_term || 1) * 2, 100)}%` }} />
              </div>
            </div>
            <div className="flex-1">
              <div className="text-text-dim mb-0.5">长期记忆</div>
              <div className="resonance-bar">
                <div className="resonance-bar-fill" style={{ width: `${Math.min((memStats.long_term || 1) * 5, 100)}%` }} />
              </div>
            </div>
          </div>
        </ResonatorCard>
      </div>

      {/* === 子系统状态 === */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.4 }}>
        <div className="text-[10px] text-text-dim uppercase tracking-[0.2em] mb-2 ml-1">▣ 子系统共鸣状态</div>
        <div className="grid grid-cols-4 md:grid-cols-8 gap-1.5">
          {subList.map(([name, on, desc, icon], i) => (
            <motion.div
              key={name}
              className={`flex items-center gap-1.5 px-2.5 py-2 rounded-lg border text-[10px] ${
                on
                  ? 'bg-aether/5 border-aether/15 text-aether-bright'
                  : 'bg-text-dim/5 border-border-glass text-text-dim'
              }`}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.35 + i * 0.03, duration: 0.3 }}
            >
              <span className="text-xs">{icon}</span>
              <div className="leading-tight">
                <div className="font-medium">{name}</div>
                <div className="text-[8px] opacity-50">{desc}</div>
              </div>
              <div className={`ml-auto w-1.5 h-1.5 rounded-full ${on ? 'bg-status-active shadow-[0_0_4px_rgba(76,255,141,0.4)]' : 'bg-status-idle'}`} />
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* === 人格向量 === */}
      {personality?.vectors?.length ? (
        <motion.div className="glass-panel p-4" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5, duration: 0.4 }}>
          <div className="text-[10px] text-text-dim uppercase tracking-wider mb-3">◇ 人格向量</div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {personality.vectors.map((v: any) => (
              <div key={v.name} className="space-y-1">
                <div className="flex justify-between text-[10px]">
                  <span className="text-text-secondary">{v.name}</span>
                  <span className="text-aether font-mono">{v.value.toFixed(2)}</span>
                </div>
                <div className="resonance-bar">
                  <div className="resonance-bar-fill" style={{ width: `${(v.value / v.max) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      ) : null}
    </div>
  );
};

function cn(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}

export default DashboardPage;
