// ============================================================
// 弥娅运维中心 · 健康诊断 — HealthPage
//   全系统健康检查 / 指标历史 / 检查项状态
// ============================================================
import { useState } from 'react';
import { motion } from 'framer-motion';
import { useHealth } from '../services/miyaApi';
import { cn } from '../utils';

const HealthPage: React.FC = () => {
  const { report, metrics, checks, history, botStats, refresh } = useHealth();
  const [lastRefresh, setLastRefresh] = useState('');

  const doRefresh = async () => {
    const now = new Date().toLocaleTimeString();
    await refresh();
    setLastRefresh(now);
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-status-active';
      case 'degraded': return 'text-starlight';
      case 'unhealthy': return 'text-status-error';
      default: return 'text-text-dim';
    }
  };

  const statusDot = (status: string, extra?: string) => (
    <span className={cn(
      'w-2 h-2 rounded-full inline-block',
      status === 'healthy' ? 'bg-status-active shadow-[0_0_8px_rgba(0,229,255,0.5)]' :
      status === 'degraded' ? 'bg-starlight shadow-[0_0_6px_rgba(255,171,64,0.4)]' :
      status === 'unhealthy' ? 'bg-status-error shadow-[0_0_6px_rgba(255,77,77,0.4)]' :
      'bg-status-idle',
      extra
    )} />
  );

  const gauge = (label: string, value: number, max: number, color: string, unit = '%') => {
    const pct = Math.min((value / max) * 100, 100);
    return (
      <div className="glass-panel p-3 flex flex-col items-center">
        <div className="text-[9px] text-text-dim mb-1">{label}</div>
        <div className="relative w-12 h-12">
          <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
            <circle cx="18" cy="18" r="14" fill="none" stroke="rgba(0,229,255,0.08)" strokeWidth="3" />
            <motion.circle
              cx="18" cy="18" r="14" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round"
              strokeDasharray={`${(pct / 100) * 88} 88`}
              initial={{ strokeDasharray: '0 88' }}
              animate={{ strokeDasharray: `${(pct / 100) * 88} 88` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-[11px] font-bold font-mono" style={{ color }}>
            {Math.round(value)}{unit === 'MB' ? '' : unit}
          </span>
        </div>
        {unit === 'MB' && <span className="text-[9px] text-text-dim mt-0.5">MB</span>}
      </div>
    );
  };

  const getCheckColor = (r: any) => {
    if (!r) return 'text-text-dim';
    const s = r.status || (r.last_result !== false ? 'pass' : 'fail');
    if (s === 'pass' || s === 'healthy') return 'text-status-active';
    if (s === 'fail' || s === 'unhealthy') return 'text-status-error';
    return 'text-text-dim';
  };

  const hMetrics = metrics || {};

  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      {/* ---- 顶部状态栏 ---- */}
      <div className="flex items-center justify-between glass-panel px-4 py-2">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-text-primary">♥ 健康诊断</span>
          {report && (
            <span className={cn('text-[10px] font-mono', getStatusClass(report.status || 'unknown'))}>
              {report.status?.toUpperCase()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {lastRefresh && <span className="text-[9px] text-text-dim">刷新: {lastRefresh}</span>}
          <button className="text-[10px] text-aether hover:text-aether-bright" onClick={doRefresh}>↻ 刷新</button>
        </div>
      </div>

      {/* ---- 基础指标仪表 ---- */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
        {gauge('CPU', hMetrics.cpu_percent || 0, 100, '#00e5ff')}
        {gauge('内存', hMetrics.memory_percent || 0, 100, '#7c4dff')}
        {gauge('磁盘', hMetrics.disk_usage_percent || 0, 100, '#ffab40')}
        {gauge('线程', hMetrics.thread_count || 0, 200, '#ec4899', '')}
        {gauge('文件', hMetrics.open_files || 0, 500, '#10b981', '')}
        {gauge('进程', hMetrics.process_count || 0, 100, '#f59e0b', '')}
      </div>

      {/* ---- 详细指标 / 健康检查 ---- */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 指标详情 */}
        <motion.div className="glass-panel p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="text-xs font-bold text-text-primary mb-3">◆ 系统指标</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-[11px]">
            <MetricRow label="内存已用" value={`${hMetrics.memory_used_mb || 0} / ${hMetrics.memory_total_mb || 0} MB`} />
            <MetricRow label="内存占比" value={`${hMetrics.memory_percent || 0}%`} color="text-resonance-bright" />
            <MetricRow label="磁盘空闲" value={`${hMetrics.disk_free_gb || 0} / ${hMetrics.disk_total_gb || 0} GB`} />
            <MetricRow label="CPU" value={`${hMetrics.cpu_percent || 0}%`} color="text-aether" />
            <MetricRow label="网络发送" value={`${hMetrics.network_sent_mb || 0} MB`} />
            <MetricRow label="网络接收" value={`${hMetrics.network_recv_mb || 0} MB`} />
            <MetricRow label="进程数" value={String(hMetrics.process_count || 0)} />
            <MetricRow label="线程数" value={String(hMetrics.thread_count || 0)} />
            <MetricRow label="打开文件" value={String(hMetrics.open_files || 0)} />
            <MetricRow label="运行时间" value={formatUptime(hMetrics.uptime || 0)} color="text-starlight" />
          </div>

          {/* Bot 统计 */}
          {botStats && (
            <div className="mt-3 pt-3 border-t border-border-glass">
              <div className="text-[10px] text-text-dim mb-2">Bot 统计</div>
              <div className="grid grid-cols-3 gap-x-4 gap-y-1 text-[10px]">
                <span className="text-text-dim">消息</span><span className="text-text-primary col-span-2">{botStats.total_messages || 0}</span>
                <span className="text-text-dim">命令</span><span className="text-text-primary col-span-2">{botStats.total_commands || 0}</span>
                <span className="text-text-dim">工具成功</span><span className="text-status-active col-span-2">{botStats.tool_calls_success || 0}</span>
                <span className="text-text-dim">工具失败</span><span className="text-status-error col-span-2">{botStats.tool_calls_failed || 0}</span>
              </div>
            </div>
          )}
        </motion.div>

        {/* 健康检查项 */}
        <motion.div className="glass-panel p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="text-xs font-bold text-text-primary mb-3">◆ 健康检查项</div>
          <div className="space-y-1.5">
            {checks.length === 0 ? (
              <span className="text-[10px] text-text-dim">等待健康检查数据...</span>
            ) : (
              checks.map((check: any) => {
                const isHealthy = check.last_result !== false;
                return (
                  <div key={check.name} className="flex items-center justify-between py-1.5 border-b border-border-glass/30">
                    <div className="flex items-center gap-2">
                      {statusDot(isHealthy ? 'healthy' : 'unhealthy')}
                      <span className="text-[11px] text-text-primary">{check.name}</span>
                      <span className="text-[9px] text-text-dim px-1.5 py-0.5 rounded bg-void-deep/60">{check.type}</span>
                      {check.critical && <span className="text-[8px] text-status-error">CRIT</span>}
                    </div>
                    <div className="flex items-center gap-3 text-[10px]">
                      {check.failure_count > 0 && (
                        <span className="text-status-error">失败 x{check.failure_count}</span>
                      )}
                      <span className={cn('font-bold', getCheckColor(check))}>
                        {isHealthy ? 'OK' : 'FAIL'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </motion.div>
      </div>

      {/* ---- 指标历史趋势 ---- */}
      {history.length > 0 && (
        <motion.div className="glass-panel p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="text-xs font-bold text-text-primary mb-3">◆ 指标历史 ({history.length} 条)</div>
          <div className="flex gap-4 h-16">
            {(['cpu_percent', 'memory_percent', 'disk_usage_percent'] as const).map((key) => {
              const values = history.map((h: any) => h[key] || 0);
              const max = Math.max(...values, 1);
              const colors = { cpu_percent: '#00e5ff', memory_percent: '#7c4dff', disk_usage_percent: '#ffab40' };
              const labels = { cpu_percent: 'CPU', memory_percent: '内存', disk_usage_percent: '磁盘' };
              return (
                <div key={key} className="flex-1 flex flex-col">
                  <span className="text-[8px] text-text-dim mb-1">{labels[key]}</span>
                  <svg className="flex-1 w-full" viewBox={`0 0 ${values.length} 40`} preserveAspectRatio="none">
                    <polyline
                      points={values.map((v, i) => `${i},${40 - (v / max) * 35 - 2}`).join(' ')}
                      fill="none" stroke={colors[key]} strokeOpacity={0.6} strokeWidth={1}
                    />
                  </svg>
                  <span className="text-[8px] text-text-dim text-right">{Math.round(values[values.length - 1])}%</span>
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* ---- 问题列表 ---- */}
      {report?.issues?.length > 0 && (
        <motion.div className="glass-panel p-4 border border-status-error/15" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="text-xs font-bold text-status-error mb-2">⚠ 检测到 {report.issues.length} 个问题</div>
          {report.issues.map((issue: string, i: number) => (
            <div key={i} className="text-[10px] text-text-secondary ml-2">- {issue}</div>
          ))}
        </motion.div>
      )}
    </div>
  );
};

function MetricRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <>
      <span className="text-text-dim">{label}</span>
      <span className={cn('font-mono text-right', color || 'text-text-primary')}>{value}</span>
    </>
  );
}

function formatUptime(secs: number): string {
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return d > 0 ? `${d}d ${h}h` : `${h}h ${m}m`;
}

export default HealthPage;
