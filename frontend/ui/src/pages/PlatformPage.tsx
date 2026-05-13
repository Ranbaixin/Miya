// ============================================================
// 弥娅运维中心 · 平台管理页 — 平台启停 / 状态 / 重启
// ============================================================
import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePlatforms } from '../services/miyaApi';
import { cn } from '../utils';

const PlatformPage: React.FC = () => {
  const { platforms, daemonStatus, wsConnected, start, stop, restart, refresh } = usePlatforms();
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState<{ action: string; id: string; name: string } | null>(null);

  const onlineCount = platforms.filter((p: any) => p.status === 'online').length;
  const offlineCount = platforms.filter((p: any) => p.status === 'offline' || p.status === 'error').length;

  const doAction = useCallback(async (action: string, id: string) => {
    setActionInProgress(id);
    setShowConfirm(null);
    try {
      if (action === 'start') await start(id);
      else if (action === 'stop') await stop(id);
      else if (action === 'restart') await restart(id);
      setTimeout(refresh, 500);
    } finally {
      setActionInProgress(null);
    }
  }, [start, stop, restart, refresh]);

  const statusConfig = (status: string) => {
    switch (status) {
      case 'online': return { color: 'text-status-active', bg: 'bg-status-active/10', dot: 'bg-status-active shadow-[0_0_8px_rgba(0,229,255,0.6)]', label: '在线' };
      case 'offline': return { color: 'text-text-dim', bg: 'bg-void-deep/50', dot: 'bg-status-idle', label: '离线' };
      case 'error': return { color: 'text-status-error', bg: 'bg-status-error/10', dot: 'bg-status-error shadow-[0_0_8px_rgba(255,77,77,0.5)]', label: '异常' };
      case 'starting': return { color: 'text-starlight', bg: 'bg-starlight/10', dot: 'bg-starlight animate-pulse', label: '启动中' };
      case 'stopping': return { color: 'text-starlight', bg: 'bg-starlight/10', dot: 'bg-starlight animate-pulse', label: '停止中' };
      default: return { color: 'text-text-dim', bg: 'bg-void-deep/50', dot: 'bg-status-idle', label: status };
    }
  };

  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      {/* ---- 守护进程状态 ---- */}
      <motion.div className="glass-panel p-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={cn(
              'w-3 h-3 rounded-full',
              daemonStatus?.started
                ? 'bg-status-active shadow-[0_0_10px_rgba(0,229,255,0.5)] animate-pulse'
                : 'bg-starlight'
            )} />
            <div>
              <span className="text-sm font-bold text-text-primary">守护进程</span>
              <span className={cn(
                'text-[10px] ml-2',
                daemonStatus?.started ? 'text-status-active' : 'text-starlight'
              )}>
                {daemonStatus?.started ? '运行中' : '未启动'}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-4 text-[10px] text-text-dim">
            <span>平台 <span className="text-status-active">{onlineCount}</span>/{platforms.length} 在线</span>
            <span className="flex items-center gap-1">
              <span className={cn('w-1.5 h-1.5 rounded-full', wsConnected ? 'bg-status-active' : 'bg-status-error')} />
              {wsConnected ? 'WS 已连接' : 'WS 断开'}
            </span>
            <button onClick={refresh} className="text-aether hover:text-aether-bright transition-colors">
              ↻ 刷新
            </button>
          </div>
        </div>
        {daemonStatus?.uptime_seconds != null && (
          <div className="mt-2 text-[10px] text-text-dim">
            运行时间: {Math.floor(daemonStatus.uptime_seconds / 3600)}h {Math.floor((daemonStatus.uptime_seconds % 3600) / 60)}m
          </div>
        )}
      </motion.div>

      {/* ---- 平台列表 ---- */}
      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <span className="text-xs font-bold text-text-primary">◆ 平台列表</span>
          <span className="text-[10px] text-text-dim">
            共 {platforms.length} 个平台 · {onlineCount} 在线 · {offlineCount} 离线
          </span>
        </div>

        <AnimatePresence>
          {platforms.map((platform: any, i: number) => {
            const sc = statusConfig(platform.status);
            const isOnline = platform.status === 'online';
            const isAction = actionInProgress === platform.platform_id;

            return (
              <motion.div
                key={platform.platform_id}
                className="glass-panel p-3 flex items-center justify-between"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
                whileHover={{ borderColor: 'rgba(0,229,255,0.2)' }}
              >
                <div className="flex items-center gap-3">
                  <span className={cn('w-2.5 h-2.5 rounded-full flex-shrink-0', sc.dot)} />
                  <div>
                    <span className="text-sm text-text-primary">{platform.name || platform.platform_id}</span>
                    <span className={cn('text-[10px] ml-2 font-mono', sc.color)}>{sc.label}</span>
                  </div>
                  {platform.type && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-void-deep/60 text-text-dim">{platform.type}</span>
                  )}
                </div>

                <div className="flex items-center gap-1.5">
                  {isOnline ? (
                    <>
                      <ActionBtn
                        label="停止"
                        onClick={() => setShowConfirm({ action: 'stop', id: platform.platform_id, name: platform.name || platform.platform_id })}
                        disabled={isAction}
                        variant="danger"
                      />
                      <ActionBtn
                        label="重启"
                        onClick={() => setShowConfirm({ action: 'restart', id: platform.platform_id, name: platform.name || platform.platform_id })}
                        disabled={isAction}
                        variant="warning"
                      />
                    </>
                  ) : (
                    <ActionBtn
                      label="启动"
                      onClick={() => doAction('start', platform.platform_id)}
                      disabled={isAction}
                      variant="primary"
                    />
                  )}
                  {isAction && (
                    <span className="text-[9px] text-starlight animate-pulse">处理中...</span>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {platforms.length === 0 && (
          <div className="glass-panel p-8 text-center">
            <span className="text-text-dim text-sm">暂无平台连接 · 等待守护进程推送...</span>
          </div>
        )}
      </div>

      {/* ---- 确认对话框 ---- */}
      <AnimatePresence>
        {showConfirm && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-void-deep/80 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowConfirm(null)}
          >
            <motion.div
              className="glass-panel p-6 max-w-sm w-full"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={e => e.stopPropagation()}
            >
              <div className="text-sm font-bold text-text-primary mb-2">确认操作</div>
              <div className="text-xs text-text-secondary mb-4">
                {showConfirm.action === 'stop' && `确定要停止 "${showConfirm.name}" 吗？该平台将断开连接。`}
                {showConfirm.action === 'restart' && `确定要重启 "${showConfirm.name}" 吗？过程中服务将短暂中断。`}
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  className="px-3 py-1.5 text-[11px] rounded-lg bg-void-deep/60 text-text-dim hover:text-text-primary transition-colors"
                  onClick={() => setShowConfirm(null)}
                >
                  取消
                </button>
                <button
                  className={cn(
                    'px-3 py-1.5 text-[11px] rounded-lg text-white transition-colors',
                    showConfirm.action === 'stop' ? 'bg-status-error/80 hover:bg-status-error' : 'bg-starlight/80 hover:bg-starlight'
                  )}
                  onClick={() => doAction(showConfirm.action, showConfirm.id)}
                >
                  确认{showConfirm.action === 'stop' ? '停止' : '重启'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ---- Action Button ----

function ActionBtn({ label, onClick, disabled, variant }: {
  label: string;
  onClick: () => void;
  disabled: boolean;
  variant: 'primary' | 'danger' | 'warning';
}) {
  const variantClass = variant === 'primary'
    ? 'bg-aether/10 text-aether border-aether/20 hover:bg-aether/20 hover:text-aether-bright'
    : variant === 'danger'
    ? 'bg-status-error/10 text-status-error border-status-error/20 hover:bg-status-error/20 hover:text-[#ff6666]'
    : 'bg-starlight/10 text-starlight border-starlight/20 hover:bg-starlight/20 hover:text-starlight';

  return (
    <button
      className={cn(
        'px-2.5 py-1 text-[10px] rounded-lg border transition-all duration-200',
        variantClass,
        disabled && 'opacity-50 cursor-not-allowed'
      )}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  );
}

export default PlatformPage;
