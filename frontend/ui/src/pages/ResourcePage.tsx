// ============================================================
// 弥娅运维中心 · 资源管理 — ResourcePage
//   进程内存 / GC 统计 / 泄漏检测 / 强制清理
// ============================================================
import { useState } from 'react';
import { motion } from 'framer-motion';
import { useResources } from '../services/miyaApi';
import { cn } from '../utils';

const ResourcePage: React.FC = () => {
  const { stats, memory, refresh, cleanup } = useResources();
  const [cleaningUp, setCleaningUp] = useState(false);
  const [lastCleanup, setLastCleanup] = useState('');

  const doCleanup = async (forceGc: boolean) => {
    setCleaningUp(true);
    await cleanup(forceGc);
    setLastCleanup(new Date().toLocaleTimeString());
    setCleaningUp(false);
  };

  const mi = stats?.memory_info || {};
  const byType = stats?.by_type || {};

  const barV = (label: string, used: number, total: number, color: string) => {
    const pct = total > 0 ? Math.min((used / total) * 100, 100) : 0;
    return (
      <div className="space-y-0.5">
        <div className="flex justify-between text-[9px]">
          <span className="text-text-dim">{label}</span>
          <span className={cn('font-mono', color)}>{used} / {total} MB</span>
        </div>
        <div className="h-1.5 bg-void-deep/60 rounded-full overflow-hidden">
          <motion.div
            className={cn('h-full rounded-full', color === 'aether' ? 'bg-aether/60' : color === 'resonance' ? 'bg-resonance/60' : 'bg-starlight/60')}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>
    );
  };

  const resourceTypes = Object.entries(byType).map(([key, val]: [string, any]) => ({
    name: key,
    count: val.count || 0,
    size: val.total_size || val.total_size_bytes || 0,
    active: val.active || 0,
    idle: val.idle || 0,
    leaking: val.leaking || 0,
  }));

  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      {/* ---- 顶部 ---- */}
      <div className="flex items-center justify-between glass-panel px-4 py-2">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-text-primary">◉ 资源管理</span>
          {stats && (
            <span className="text-[10px] text-text-dim">
              共 {stats.total_resources || 0} 资源 · {((stats.total_size_bytes || 0) / 1024 / 1024).toFixed(1)} MB
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {lastCleanup && <span className="text-[9px] text-text-dim">上次清理: {lastCleanup}</span>}
          <button
            className="px-2 py-1 text-[10px] rounded-lg bg-starlight/10 text-starlight border border-starlight/20 hover:bg-starlight/20 transition-colors disabled:opacity-50"
            disabled={cleaningUp}
            onClick={() => doCleanup(true)}
          >
            {cleaningUp ? '清理中...' : '强制 GC'}
          </button>
          <button
            className="px-2 py-1 text-[10px] rounded-lg bg-aether/10 text-aether border border-aether/20 hover:bg-aether/20 transition-colors disabled:opacity-50"
            disabled={cleaningUp}
            onClick={() => doCleanup(false)}
          >
            {cleaningUp ? '清理中...' : '清理资源'}
          </button>
          <button className="text-[10px] text-text-dim hover:text-text-primary" onClick={refresh}>↻ 刷新</button>
        </div>
      </div>

      {/* ---- 进程内存 ---- */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <motion.div className="glass-panel p-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="text-xs font-bold text-text-primary mb-3">◆ 进程内存</div>
          {stats ? (
            <div className="space-y-3">
              {barV('RSS', mi.rss_mb || 0, (mi.rss_mb || 0) * 1.5 || 100, 'aether')}
              {barV('VMS', mi.vms_mb || 0, (mi.vms_mb || 0) * 1.5 || 100, 'resonance')}

              <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-border-glass">
                <MiniCard label="GC 对象数" value={String(mi.gc_objects || 0)} color="text-aether" />
                <MiniCard label="已回收" value={String(mi.gc_collected || 0)} color="text-status-active" />
                <MiniCard label="未回收" value={String(mi.gc_uncollectable || 0)} color={mi.gc_uncollectable > 0 ? 'text-status-error' : 'text-text-dim'} />
                <MiniCard label="GC 阈值" value={`${mi.gc_threshold?.[0] || 0} / ${mi.gc_threshold?.[1] || 0} / ${mi.gc_threshold?.[2] || 0}`} color="text-text-secondary" />
              </div>
            </div>
          ) : (
            <span className="text-[10px] text-text-dim">等待数据...</span>
          )}

          {/* 系统内存 */}
          {memory && (
            <div className="mt-3 pt-3 border-t border-border-glass space-y-2">
              <div className="text-[10px] text-text-dim mb-1">系统内存</div>
              {barV('总量', memory.system_memory?.used_mb || 0, memory.system_memory?.total_mb || 1, 'starlight')}
              <div className="text-[9px] text-text-dim">可用: {memory.system_memory?.available_mb || 0} MB · {memory.system_memory?.percent || 0}%</div>
            </div>
          )}
        </motion.div>

        {/* ---- 资源类型分布 ---- */}
        <motion.div className="glass-panel p-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <div className="text-xs font-bold text-text-primary mb-3">◆ 资源分布</div>

          {resourceTypes.length === 0 ? (
            <span className="text-[10px] text-text-dim">无活跃资源</span>
          ) : (
            <div className="space-y-2">
              {resourceTypes.map((rt) => (
                <div key={rt.name} className="border-b border-border-glass/30 pb-1.5">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-text-primary">{rt.name}</span>
                    <span className="text-text-dim">{rt.count} 个 · {(rt.size / 1024).toFixed(1)} KB</span>
                  </div>
                  <div className="flex gap-3 text-[9px] mt-0.5">
                    <span className="text-status-active">{rt.active} 活跃</span>
                    <span className="text-text-dim">{rt.idle} 空闲</span>
                    {rt.leaking > 0 && <span className="text-status-error">{rt.leaking} 泄漏</span>}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 泄漏检测 */}
          {stats?.leaks_detected > 0 && (
            <div className="mt-3 p-2 rounded-lg bg-status-error/5 border border-status-error/15">
              <span className="text-[10px] text-status-error">⚠ 检测到 {stats.leaks_detected} 个疑似内存泄漏</span>
            </div>
          )}
        </motion.div>
      </div>

      {/* ---- 资源总览 ---- */}
      {stats && (
        <motion.div className="glass-panel p-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <div className="text-xs font-bold text-text-primary mb-3">◆ 概览</div>
          <div className="grid grid-cols-5 gap-3">
            <BigStat label="总资源" value={stats.total_resources || 0} color="text-aether" />
            <BigStat label="总大小" value={(stats.total_size_bytes / 1024 / 1024).toFixed(1)} unit=" MB" color="text-resonance-bright" />
            <BigStat label="RSS" value={mi.rss_mb || 0} unit=" MB" color="text-starlight" />
            <BigStat label="GC 对象" value={mi.gc_objects || 0} color="text-text-primary" />
            <BigStat label="泄漏" value={stats.leaks_detected || 0} color={stats.leaks_detected > 0 ? 'text-status-error' : 'text-status-active'} />
          </div>
        </motion.div>
      )}
    </div>
  );
};

function MiniCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-void-deep/40 rounded-lg p-2">
      <div className="text-[8px] text-text-dim">{label}</div>
      <div className={cn('text-xs font-mono font-bold', color)}>{value}</div>
    </div>
  );
}

function BigStat({ label, value, unit, color }: { label: string; value: string | number; unit?: string; color: string }) {
  return (
    <div className="text-center">
      <div className="text-[9px] text-text-dim mb-0.5">{label}</div>
      <div className={cn('text-lg font-bold font-mono', color)}>
        {value}{unit || ''}
      </div>
    </div>
  );
}

export default ResourcePage;
