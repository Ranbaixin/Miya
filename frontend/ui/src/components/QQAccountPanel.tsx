import { motion } from 'framer-motion';

interface QQAccountInfo {
  uin: string;
  nick: string;
  status: 'online' | 'offline' | 'connecting';
  client: string;
  level: number;
  friends: number;
  groups: number;
  lastActive: string;
}

interface QQAccountPanelProps {
  account?: QQAccountInfo;
}

const QQAccountPanel: React.FC<QQAccountPanelProps> = ({ account: propAccount }) => {
  const account: QQAccountInfo = propAccount || {
    uin: '3274361514',
    nick: 'Miya',
    status: 'online',
    client: 'Pad协议',
    level: 72,
    friends: 47,
    groups: 6,
    lastActive: '刚刚',
  };

  const statusColors = {
    online: { bg: 'bg-green-500', text: 'text-green-400', label: '在线' },
    offline: { bg: 'bg-red-500', text: 'text-red-400', label: '离线' },
    connecting: { bg: 'bg-yellow-500', text: 'text-yellow-400', label: '连接中' },
  };

  const status = statusColors[account.status];

  const levelProgress = (account.level % 80) / 80 * 100;

  return (
    <div className="glass-panel p-4 space-y-4">
      <div className="text-cyan-400 text-xs flex items-center gap-2">
        <span>◆</span> QQ账号
      </div>

      <div className="flex items-center gap-4">
        <div className="relative">
          <motion.div
            className="w-14 h-14 rounded-full bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center text-xl font-bold text-white"
            animate={{ 
              boxShadow: account.status === 'online' 
                ? ['0 0 20px rgba(6,182,212,0.3)', '0 0 40px rgba(6,182,212,0.6)', '0 0 20px rgba(6,182,212,0.3)']
                : 'none'
            }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            {account.nick[0]}
          </motion.div>
          <motion.div
            className={`absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full ${status.bg}`}
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        </div>

        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-white font-medium">{account.nick}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${status.bg}/20 ${status.text}`}>
              {status.label}
            </span>
          </div>
          <div className="text-xs text-gray-500">QQ: {account.uin}</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="bg-black/20 rounded p-2 text-center">
          <div className="text-lg text-cyan-400 font-bold">{account.friends}</div>
          <div className="text-[10px] text-gray-500">好友</div>
        </div>
        <div className="bg-black/20 rounded p-2 text-center">
          <div className="text-lg text-purple-400 font-bold">{account.groups}</div>
          <div className="text-[10px] text-gray-500">群聊</div>
        </div>
        <div className="bg-black/20 rounded p-2 text-center">
          <div className="text-lg text-yellow-400 font-bold">L{account.level}</div>
          <div className="text-[10px] text-gray-500">等级</div>
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex justify-between text-xs">
          <span className="text-gray-500">等级经验</span>
          <span className="text-cyan-400">{account.level}/80</span>
        </div>
        <div className="h-1.5 bg-black/30 rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-purple-500"
            initial={{ width: 0 }}
            animate={{ width: `${levelProgress}%` }}
            transition={{ duration: 1 }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between text-xs pt-2 border-t border-cyan-500/10">
        <div className="flex items-center gap-1">
          <div className={`w-1.5 h-1.5 rounded-full ${status.bg}`} />
          <span className="text-gray-500">{account.client}</span>
        </div>
        <span className="text-gray-600">活跃: {account.lastActive}</span>
      </div>
    </div>
  );
};

export default QQAccountPanel;