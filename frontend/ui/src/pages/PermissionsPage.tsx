// ============================================================
// 弥娅运维中心 · 权限管理页 — AuthNet 可视化
// ============================================================
import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../services/miyaApi';
import { cn } from '../utils';

const PermissionsPage: React.FC = () => {
  const { users, roles, stats, selectedUser, viewUser, grant, refresh, clearUser } = useAuth();
  const [search, setSearch] = useState('');
  const [showGrant, setShowGrant] = useState(false);
  const [grantUserId, setGrantUserId] = useState('');
  const [grantPlatform, setGrantPlatform] = useState('');
  const [grantGroups, setGrantGroups] = useState<string[]>([]);
  const [grantUsername, setGrantUsername] = useState('');

  const filteredUsers = users.filter((u: any) => {
    const id = (u.user_id || u.id || '').toLowerCase();
    const name = (u.username || u.name || '').toLowerCase();
    const s = search.toLowerCase();
    return id.includes(s) || name.includes(s);
  });

  const doGrant = useCallback(async () => {
    if (!grantUserId || !grantPlatform || grantGroups.length === 0) return;
    await grant(grantUserId, grantPlatform, grantGroups, grantUsername || undefined);
    setShowGrant(false);
    setGrantUserId('');
    setGrantPlatform('');
    setGrantGroups([]);
    setGrantUsername('');
    refresh();
  }, [grantUserId, grantPlatform, grantGroups, grantUsername, grant, refresh]);

  const toggleGroup = (group: string) => {
    setGrantGroups(prev => prev.includes(group) ? prev.filter(g => g !== group) : [...prev, group]);
  };

  const getRoleLevelClass = (level: number) => {
    if (level >= 100) return 'text-aether';
    if (level >= 50) return 'text-resonance-bright';
    if (level >= 20) return 'text-starlight';
    return 'text-text-dim';
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* ---- 用户列表 ---- */}
      <div className="w-80 flex-shrink-0 border-r border-border-glass flex flex-col">
        <div className="p-3 border-b border-border-glass">
          <div className="text-xs font-bold text-text-primary mb-2">◆ 用户列表</div>
          <div className="flex gap-2 mb-2">
            <input
              className="flex-1 bg-void-deep/60 border border-border-glass rounded-lg px-2.5 py-1.5 text-[11px] text-text-primary outline-none focus:border-aether/30 placeholder:text-text-dim"
              placeholder="搜索用户 ID..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <button
              className="px-3 py-1.5 text-[10px] rounded-lg bg-aether/10 text-aether border border-aether/20 hover:bg-aether/20 transition-all"
              onClick={() => setShowGrant(true)}
            >
              授权
            </button>
          </div>
          {stats && (
            <div className="flex items-center gap-3 text-[10px] text-text-dim">
              <span>用户 <span className="text-text-primary">{stats.total_users || users.length}</span></span>
              <span>角色 <span className="text-text-primary">{stats.total_roles || roles.length}</span></span>
              <span>权限 <span className="text-text-primary">{stats.total_permissions || 0}</span></span>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-auto">
          <AnimatePresence>
            {filteredUsers.length === 0 ? (
              <div className="p-8 text-center text-text-dim text-xs">暂无用户数据</div>
            ) : (
              filteredUsers.map((user: any, i: number) => {
                const uid = user.user_id || user.id || 'unknown';
                const isSuper = user.is_superadmin;
                const roleLevel = user.role_level ?? 0;
                const groups = user.groups || [];
                const active = selectedUser?.user_id === uid;

                return (
                  <motion.button
                    key={uid}
                    className={cn(
                      'w-full text-left px-3 py-2.5 border-b border-border-glass/50 transition-colors',
                      active ? 'bg-aether/5' : 'hover:bg-void-surface/40'
                    )}
                    initial={{ opacity: 0, x: -5 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.01 }}
                    onClick={() => viewUser(uid)}
                  >
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        'w-2 h-2 rounded-full',
                        isSuper ? 'bg-aether shadow-[0_0_6px_rgba(0,229,255,0.5)]' : 'bg-text-dim'
                      )} />
                      <span className="text-[11px] text-text-primary truncate flex-1">{uid}</span>
                      {isSuper && <span className="text-[8px] px-1 py-0.5 rounded bg-aether/10 text-aether">SU</span>}
                    </div>
                    <div className="flex items-center gap-2 mt-1 ml-4">
                      {roleLevel !== undefined && (
                        <span className={cn('text-[9px] font-mono', getRoleLevelClass(roleLevel))}>Lv{roleLevel}</span>
                      )}
                      {groups.slice(0, 3).map((g: string) => (
                        <span key={g} className="text-[8px] px-1 py-0.5 rounded bg-void-deep/60 text-text-dim">{g}</span>
                      ))}
                      {groups.length > 3 && <span className="text-[8px] text-text-dim">+{groups.length - 3}</span>}
                    </div>
                  </motion.button>
                );
              })
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ---- 用户详情 ---- */}
      <div className="flex-1 flex flex-col min-w-0">
        <AnimatePresence mode="wait">
          {selectedUser ? (
            <motion.div
              key={selectedUser.user_id}
              className="flex-1 p-4 space-y-4 overflow-auto"
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-bold text-text-primary">{selectedUser.user_id}</h2>
                  {selectedUser.username && selectedUser.username !== selectedUser.user_id && (
                    <span className="text-[10px] text-text-dim">别名: {selectedUser.username}</span>
                  )}
                </div>
                <button
                  className="px-2 py-1 text-[10px] rounded-lg text-text-dim hover:text-text-primary transition-colors"
                  onClick={clearUser}
                >
                  关闭
                </button>
              </div>

              {selectedUser.is_superadmin && (
                <div className="px-3 py-2 rounded-lg bg-aether/5 border border-aether/10 text-[11px] text-aether">
                  ◆ 超级管理员 — 拥有所有权限
                </div>
              )}

              {/* 角色等级 */}
              <div className="glass-panel p-4">
                <div className="text-[10px] text-text-dim mb-2">权限等级</div>
                <div className="flex items-center gap-3">
                  <div className="w-full h-2 bg-void-deep/60 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full rounded-full bg-gradient-to-r from-aether via-resonance to-starlight"
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min((selectedUser.role_level || 0), 100)}%` }}
                      transition={{ duration: 0.5, ease: 'easeOut' }}
                    />
                  </div>
                  <span className={cn('text-xs font-mono font-bold', getRoleLevelClass(selectedUser.role_level || 0))}>
                    Lv.{selectedUser.role_level || 0}
                  </span>
                </div>
              </div>

              {/* 角色组 */}
              <div className="glass-panel p-4">
                <div className="text-[10px] text-text-dim mb-2">角色组</div>
                <div className="flex flex-wrap gap-1.5">
                  {(selectedUser.groups || []).length === 0 ? (
                    <span className="text-[10px] text-text-dim">无</span>
                  ) : (
                    (selectedUser.groups || []).map((g: string) => (
                      <span key={g} className="text-[10px] px-2 py-1 rounded bg-resonance/10 text-resonance-bright border border-resonance/15">
                        {g}
                      </span>
                    ))
                  )}
                </div>
              </div>

              {/* 权限列表 */}
              <div className="glass-panel p-4">
                <div className="text-[10px] text-text-dim mb-2">拥有权限 ({(selectedUser.permissions || []).length})</div>
                <div className="flex flex-wrap gap-1 max-h-48 overflow-auto">
                  {(selectedUser.permissions || []).length === 0 ? (
                    <span className="text-[10px] text-text-dim">无独立权限</span>
                  ) : (
                    (selectedUser.permissions || []).slice(0, 50).map((p: string) => (
                      <span key={p} className="text-[9px] px-1.5 py-0.5 rounded bg-void-deep/60 text-text-secondary font-mono">
                        {p}
                      </span>
                    ))
                  )}
                  {(selectedUser.permissions || []).length > 50 && (
                    <span className="text-[9px] text-text-dim">...还有 {(selectedUser.permissions || []).length - 50} 个</span>
                  )}
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              className="flex-1 flex items-center justify-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="text-center">
                <div className="text-3xl text-text-dim mb-3">☰</div>
                <div className="text-sm text-text-secondary mb-1">权限管理</div>
                <div className="text-[10px] text-text-dim">从左侧选择用户查看详情</div>
                <div className="text-[10px] text-text-dim mt-1">或点击"授权"授予新用户角色</div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ---- 授权弹窗 ---- */}
      <AnimatePresence>
        {showGrant && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-void-deep/80 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowGrant(false)}
          >
            <motion.div
              className="glass-panel p-5 max-w-md w-full"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={e => e.stopPropagation()}
            >
              <div className="text-sm font-bold text-text-primary mb-4">授予角色权限</div>

              <div className="space-y-3">
                <div>
                  <label className="text-[10px] text-text-dim block mb-1">用户 ID</label>
                  <input
                    className="w-full bg-void-deep/60 border border-border-glass rounded-lg px-2.5 py-1.5 text-[11px] text-text-primary outline-none focus:border-aether/30"
                    value={grantUserId}
                    onChange={e => setGrantUserId(e.target.value)}
                    placeholder="user_xxx"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-text-dim block mb-1">平台</label>
                  <input
                    className="w-full bg-void-deep/60 border border-border-glass rounded-lg px-2.5 py-1.5 text-[11px] text-text-primary outline-none focus:border-aether/30"
                    value={grantPlatform}
                    onChange={e => setGrantPlatform(e.target.value)}
                    placeholder="例如: qq, telegram, webchat"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-text-dim block mb-1">显示名称 (可选)</label>
                  <input
                    className="w-full bg-void-deep/60 border border-border-glass rounded-lg px-2.5 py-1.5 text-[11px] text-text-primary outline-none focus:border-aether/30"
                    value={grantUsername}
                    onChange={e => setGrantUsername(e.target.value)}
                    placeholder="用户昵称"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-text-dim block mb-1">角色组</label>
                  <div className="flex flex-wrap gap-1.5">
                    {(roles || []).length === 0 ? (
                      <span className="text-[10px] text-text-dim">暂无可用角色</span>
                    ) : (
                      (roles || []).map((role: any) => {
                        const roleName = role.name || role.id || role;
                        const selected = grantGroups.includes(roleName);
                        return (
                          <button
                            key={roleName}
                            className={cn(
                              'text-[10px] px-2.5 py-1 rounded-lg border transition-all',
                              selected
                                ? 'bg-aether/15 text-aether border-aether/30'
                                : 'bg-void-deep/60 text-text-dim border-border-glass hover:border-aether/15'
                            )}
                            onClick={() => toggleGroup(roleName)}
                          >
                            {roleName}
                          </button>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>

              <div className="flex gap-2 justify-end mt-4">
                <button
                  className="px-3 py-1.5 text-[11px] rounded-lg bg-void-deep/60 text-text-dim hover:text-text-primary transition-colors"
                  onClick={() => setShowGrant(false)}
                >
                  取消
                </button>
                <button
                  className="px-3 py-1.5 text-[11px] rounded-lg bg-aether/10 text-aether border border-aether/20 hover:bg-aether/20 transition-all disabled:opacity-50"
                  disabled={!grantUserId || !grantPlatform || grantGroups.length === 0}
                  onClick={doGrant}
                >
                  确认授权
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default PermissionsPage;
