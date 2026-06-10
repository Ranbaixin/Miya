// ============================================================
// 弥娅运维中心 · 系统总览 — 实时指标 / 服务健康 / 子网状态
// ============================================================
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useMiyaConnection, useModels, useAgents, useEmotion, useMemory, usePlatforms, useSystemMetrics } from '../services/miyaApi';
import { cn } from '../utils';

interface Props {
  metrics: ReturnType<typeof useSystemMetrics>['metrics'];
}

const SystemOverviewPage: React.FC<Props> = ({ metrics }) => {
  const { connected } = useMiyaConnection();
  const { models } = useModels();
  const { agents } = useAgents();
  const { emotion } = useEmotion();
  const { stats: memStats } = useMemory();
  const { platforms, daemonStatus } = usePlatforms();
  const [lastRefresh, setLastRefresh] = useState('');
  const [history, setHistory] = useState<Array<{ cpu: number; mem: number; disk: number }>>([]);

  useEffect(() => {
    const h = [...history, { cpu: metrics.cpu_percent, mem: metrics.memory_percent, disk: metrics.disk_percent }];
    if (h.length > 60) h.shift();
    setHistory(h);
  }, [metrics.timestamp]);

  useEffect(() => {
    setLastRefresh(new Date().toLocaleTimeString());
  }, [metrics.cpu_percent]);

  const subList = [
    { name: 'MLink', status: true, desc: '消息总线', icon: '◆' },
    { name: 'MemNet', status: true, desc: '记忆网络', icon: '◉' },
    { name: 'ToolNet', status: true, desc: '工具网络', icon: '⚙' },
    { name: 'WebNet', status: true, desc: 'Web 服务', icon: '◎' },
    { name: 'QQNet', status: platforms.some((p: any) => p.status === 'online'), desc: 'QQ 平台', icon: '◇' },
    { name: 'TTS', status: true, desc: '语音合成', icon: '♪' },
    { name: 'Scheduler', status: true, desc: '定时调度', icon: '▷' },
    { name: 'Proactive', status: true, desc: '主动感知', icon: '♥' },
  ];

  const onlinePlatforms = platforms.filter((p: any) => p.status === 'online').length;
  const activeModels = models.filter((m: any) => m.status === 'active').length;
  const totalTools = agents.reduce((s: number, a: any) => s + (a.tool_count || 0), 0);

  const getStatusColor = (val: number) => {
    if (val > 85) return 'text-status-error';
    if (val > 65) return 'text-starlight';
    return 'text-status-active';
  };

  const statCard = (label: string, value: string | number, icon: string, color: string, sub?: string) => (
    <motion.div
      className="glass-panel p-3 flex items-center gap-3 cursor-default"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      whileHover={{ scale: 1.02, borderColor: 'rgba(0,229,255,0.3)' }}
    >
      <span className="text-xl">{icon}</span>
      <div>
        <div className="text-[10px] text-text-dim uppercase tracking-wider">{label}</div>
        <div className={cn('text-lg font-bold font-mono', color)}>{value}</div>
        {sub && <div className="text-[9px] text-text-dim">{sub}</div>}
      </div>
    </motion.div>
  );

  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      {/* ---- 系统状态栏 ---- */}
      <motion.div
        className="flex items-center justify-between glass-panel px-4 py-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <div className="flex items-center gap-4">
          <span className="text-sm font-display text-aether">◆ MIYA Ops Center</span>
          <span className="text-[10px] text-text-dim">v8.0</span>
        </div>
        <div className="flex items-center gap-4 text-[10px]">
          <span className="flex items-center gap-1.5">
            <span className={cn('w-1.5 h-1.5 rounded-full', connected ? 'bg-status-active animate-pulse' : 'bg-status-error')} />
            <span className={connected ? 'text-status-active' : 'text-status-error'}>
              {connected ? '已共鸣' : '未连接'}
            </span>
          </span>
          {daemonStatus && (
            <span className="text-text-dim">
              守护进程: <span className={daemonStatus.started ? 'text-status-active' : 'text-starlight'}>
                {daemonStatus.started ? '运行中' : '启动中'}
              </span>
            </span>
          )}
          <span className="text-text-dim">刷新: {lastRefresh}</span>
        </div>
      </motion.div>

      {/* ---- 核心指标卡片 ---- */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {statCard('CPU', `${metrics.cpu_percent}%`, '◈', getStatusColor(metrics.cpu_percent * 100))}
        {statCard('内存', `${metrics.memory_percent}%`, '◆', getStatusColor(metrics.memory_percent * 100),
          `${metrics.memory_used_gb}/${metrics.memory_total_gb} GB`)}
        {statCard('磁盘', `${metrics.disk_percent}%`, '▣', getStatusColor(metrics.disk_percent * 100),
          `${metrics.disk_used_gb}/${metrics.disk_total_gb} GB`)}
        {statCard('运行时间', formatTime(metrics.uptime_seconds || 0), '↻', 'text-aether')}
      </div>

      {/* ---- 实时趋势 ---- */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'CPU', val: metrics.cpu_percent, hist: history.map(h => h.cpu), color: 'aether' as const },
          { label: '内存', val: metrics.memory_percent, hist: history.map(h => h.mem), color: 'resonance' as const },
          { label: '磁盘', val: metrics.disk_percent, hist: history.map(h => h.disk), color: 'starlight' as const },
        ].map((item) => (
          <motion.div key={item.label} className="glass-panel p-3" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] text-text-dim">{item.label}</span>
              <span className={cn('text-xs font-mono font-bold', item.color === 'aether' ? 'text-aether' : item.color === 'resonance' ? 'text-resonance-bright' : 'text-starlight')}>
                {item.val}%
              </span>
            </div>
            <Sparkline data={item.hist} color={item.color} />
          </motion.div>
        ))}
      </div>

      {/* ---- 服务与平台 ---- */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 子网状态 */}
        <motion.div className="glass-panel p-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="text-xs font-bold text-text-primary mb-3">◆ 子网状态</div>
          <div className="grid grid-cols-2 gap-2">
            {subList.map((s) => (
              <div key={s.name} className="flex items-center gap-2 text-[11px]">
                <span className={cn(
                  'w-2 h-2 rounded-full',
                  s.status ? 'bg-status-active shadow-[0_0_6px_rgba(0,229,255,0.5)]' : 'bg-status-idle'
                )} />
                <span className="text-text-dim w-6">{s.icon}</span>
                <span className={s.status ? 'text-text-primary' : 'text-text-dim'}>{s.name}</span>
                <span className="text-text-dim ml-auto">{s.desc}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* 核心摘要 */}
        <motion.div className="glass-panel p-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <div className="text-xs font-bold text-text-primary mb-3">◆ 核心摘要</div>
          <div className="space-y-2 text-[11px]">
            <SummaryRow label="平台在线" value={`${onlinePlatforms}/${platforms.length}`} color="text-status-active" />
            <SummaryRow label="AI 模型" value={`${activeModels} 活跃`} color="text-aether" />
            <SummaryRow label="Agent" value={`${agents.length} 就绪`} color="text-resonance-bright" />
            <SummaryRow label="工具" value={`${totalTools} 可用`} color="text-starlight" />
            <SummaryRow label="记忆条目" value={`${memStats.total || 0}`} color="text-text-secondary" />
            <SummaryRow label="情绪" value={`${emotion?.dominant_emotion || '—'} ${emotion?.intensity || 0}%`} color="text-text-secondary" />
          </div>
        </motion.div>
      </div>

      {/* ---- 平台快速卡片 ---- */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <div className="text-xs font-bold text-text-primary mb-2 px-1">◆ 平台状态</div>
        <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
          {platforms.slice(0, 10).map((p: any) => (
            <motion.div
              key={p.platform_id}
              className="glass-panel p-2 text-center cursor-default"
              whileHover={{ scale: 1.03, borderColor: 'rgba(0,229,255,0.25)' }}
            >
              <span className={cn(
                'w-1.5 h-1.5 rounded-full inline-block mr-1',
                p.status === 'online' ? 'bg-status-active' : p.status === 'error' ? 'bg-status-error' : 'bg-status-idle'
              )} />
              <span className="text-[10px] text-text-primary">{p.name || p.platform_id}</span>
              <div className={cn(
                'text-[9px]',
                p.status === 'online' ? 'text-status-active' : p.status === 'error' ? 'text-status-error' : 'text-text-dim'
              )}>
                {p.status === 'online' ? '在线' : p.status === 'error' ? '异常' : '离线'}
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
};

// ---- Helpers ----

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function SummaryRow({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-text-dim">{label}</span>
      <span className={cn('font-mono', color)}>{value}</span>
    </div>
  );
}

function Sparkline({ data, color }: { data: number[]; color: 'aether' | 'resonance' | 'starlight' }) {
  if (data.length < 2) return <div className="h-8" />;
  const max = Math.max(...data, 1);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 100;
  const h = 32;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * (h - 4) - 2}`).join(' ');

  const colorMap = { aether: '#00e5ff', resonance: '#7c4dff', starlight: '#ffab40' };

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-8" preserveAspectRatio="none">
      <polyline
        points={points}
        fill="none"
        stroke={colorMap[color]}
        strokeOpacity={0.6}
        strokeWidth={1}
      />
    </svg>
  );
}

export default SystemOverviewPage;
