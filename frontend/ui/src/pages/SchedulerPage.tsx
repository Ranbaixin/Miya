import { useState } from 'react';
import { motion } from 'framer-motion';
import { useScheduler, useKnowledge } from '../services/miyaApi';
import { cn } from '../utils';

const SchedulerPage: React.FC = () => {
  const { cronJobs, refresh: refreshSched } = useScheduler();
  const { kb, plugins, providers, skills, mcpServers, refresh: refreshKb } = useKnowledge();
  const [tab, setTab] = useState<'cron' | 'kb' | 'plugins' | 'providers' | 'skills' | 'mcp'>('cron');
  const jobs = Array.isArray(cronJobs?.data) ? cronJobs.data : [];
  const safe = (d: any, k?: string) => Array.isArray(k ? d?.[k] : d) ? (k ? d[k] : d) : [];
  const tabs = [{ k: 'cron', l: '定时任务', i: '↻' }, { k: 'kb', l: '知识库', i: '◉' }, { k: 'plugins', l: '插件', i: '⬡' }, { k: 'providers', l: 'Provider', i: '◆' }, { k: 'skills', l: '技能', i: '⚙' }, { k: 'mcp', l: 'MCP', i: '⊿' }] as const;
  const st = (s: string) => ({ running: 'text-status-active', completed: 'text-aether', failed: 'text-status-error', pending: 'text-starlight', scheduled: 'text-starlight' }[s?.toLowerCase()] || 'text-text-dim');
  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      <motion.div className="glass-panel p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="flex items-center justify-between mb-3"><span className="text-sm font-bold text-text-primary">↻ 调度中心</span><button className="text-[10px] text-aether hover:text-aether-bright" onClick={() => { refreshSched(); refreshKb(); }}>↻ 刷新</button></div>
        <div className="grid grid-cols-6 gap-3">
          <MS label="定时任务" value={jobs.length} color="text-aether" /><MS label="知识库" value={safe(kb, 'data').length} color="text-resonance-bright" />
          <MS label="插件" value={safe(plugins, 'data').length || safe(plugins).length} color="text-starlight" /><MS label="Provider" value={safe(providers, 'providers').length} color="text-status-active" />
          <MS label="技能" value={safe(skills, 'skills').length || safe(skills).length} color="text-text-primary" /><MS label="MCP" value={safe(mcpServers, 'servers').length} color="text-text-dim" />
        </div>
      </motion.div>
      <div className="flex items-center gap-1 overflow-x-auto">{tabs.map(t => <button key={t.k} className={cn('px-3 py-1.5 text-[10px] rounded-lg transition-colors whitespace-nowrap', tab === t.k ? 'bg-aether/10 text-aether border border-aether/20' : 'text-text-dim hover:text-text-primary')} onClick={() => setTab(t.k as any)}>{t.i} {t.l}</button>)}</div>
      {tab === 'cron' && <LP items={jobs} empty="暂无定时任务">{(j: any, i: number) => <div key={j.job_id || i} className="glass-panel p-3 flex items-center justify-between"><div className="flex items-center gap-3"><span className="text-[10px] text-text-dim px-1.5 py-0.5 rounded bg-void-deep/60">{j.task_type || '—'}</span><span className="text-[11px] text-text-primary">{j.job_id?.slice(0, 16) || '—'}</span><span className={cn('text-[9px] font-mono', st(j.status))}>{j.status || '—'}</span></div><div className="flex items-center gap-3 text-[9px] text-text-dim">{j.execute_at && <span>执行: {new Date(j.execute_at).toLocaleTimeString()}</span>}<span>优先级: {j.priority || 0}</span></div></div>}</LP>}
      {tab === 'kb' && <LP items={safe(kb, 'data')} empty="暂无知识库">{(it: any, i: number) => <div key={it.id || i} className="glass-panel p-3 flex items-center justify-between"><span className="text-[10px] text-text-primary">{it.name || it.id}</span><span className="text-[9px] text-text-dim">{it.description || ''}</span><span className="text-[9px] text-resonance-bright font-mono">{it.document_count || 0} 文档</span></div>}</LP>}
      {tab === 'plugins' && <LP items={safe(plugins, 'data')} empty="暂无插件">{(p: any, i: number) => <div key={p.name || i} className="glass-panel p-3 flex items-center justify-between"><span className="text-xs text-text-primary">{p.name}</span><span className="text-[9px] text-text-dim">{p.description?.slice(0, 60) || ''}</span><span className={cn('text-[9px]', p.enabled ? 'text-status-active' : 'text-text-dim')}>{p.enabled ? '启用' : '禁用'}</span></div>}</LP>}
      {tab === 'providers' && <LP items={safe(providers, 'providers')} empty="暂无Provider">{(p: any, i: number) => <div key={p.id || i} className="glass-panel p-3 flex items-center justify-between"><div className="flex items-center gap-3"><span className={cn('w-1.5 h-1.5 rounded-full', p.enabled ? 'bg-status-active' : 'bg-status-idle')} /><span className="text-[11px] text-text-primary">{p.name}</span><span className="text-[9px] text-text-dim">{p.default_model || ''}</span></div><span className="text-[9px] text-text-dim">{p.models?.length || 0} 模型</span></div>}</LP>}
      {tab === 'skills' && <LP items={safe(skills, 'skills')} empty="暂无技能">{(s: any, i: number) => <div key={i} className="glass-panel p-3 flex items-center justify-between"><span className="text-[11px] text-text-primary">{s.name || s.id || '—'}</span><span className="text-[9px] text-text-dim">{s.description?.slice(0, 60) || ''}</span></div>}</LP>}
      {tab === 'mcp' && <LP items={safe(mcpServers, 'servers')} empty="暂无MCP服务器">{(s: any, i: number) => <div key={s.name || i} className="glass-panel p-3 flex items-center justify-between"><div className="flex items-center gap-3"><span className="w-1.5 h-1.5 rounded-full bg-starlight/60" /><span className="text-[11px] text-text-primary">{s.name}</span>{s.command && <span className="text-[9px] text-text-dim font-mono">{s.command}</span>}</div>{s.args && <span className="text-[9px] text-text-dim">{s.args.slice(0, 3).join(' ')}</span>}</div>}</LP>}
    </div>
  );
};

function MS({ label, value, color }: { label: string; value: number; color: string }) {
  return <motion.div className="glass-panel p-2.5 text-center" whileHover={{ scale: 1.03, borderColor: 'rgba(0,229,255,0.15)' }}><div className="text-[8px] text-text-dim mb-0.5">{label}</div><div className={cn('text-sm font-bold font-mono', color)}>{value}</div></motion.div>;
}

function LP({ items, empty, children }: { items: any[]; empty: string; children: (item: any, i: number) => React.ReactNode }) {
  if (items.length === 0) return <div className="glass-panel p-8 text-center text-text-dim text-xs">{empty}</div>;
  return <div className="space-y-1">{items.map((item, i) => <motion.div key={i} initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.02 }}>{children(item, i)}</motion.div>)}</div>;
}

export default SchedulerPage;
