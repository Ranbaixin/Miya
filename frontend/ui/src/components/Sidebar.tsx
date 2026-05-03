import { motion } from 'framer-motion';

type NavItem = {
  id: string;
  icon: string;
  label: string;
};

const navItems: NavItem[] = [
  { id: 'dashboard', icon: '📊', label: '仪表盘' },
  { id: 'systems', icon: '💻', label: '系统' },
  { id: 'account', icon: '👤', label: '账号' },
  { id: 'logs', icon: '📝', label: '日志' },
  { id: 'groups', icon: '👥', label: '群组' },
  { id: 'friends', icon: '🤝', label: '好友' },
  { id: 'messages', icon: '💭', label: '消息' },
  { id: 'unified_messages', icon: '🌊', label: '消息流' },
  { id: 'emotion', icon: '💕', label: '情感' },
  { id: 'memory', icon: '🧠', label: '记忆' },
  { id: 'cognitive', icon: '🧩', label: '认知' },
  { id: 'tools', icon: '🔧', label: '工具' },
  { id: 'platform', icon: '🌐', label: '平台' },
  { id: 'plugin_market', icon: '🛒', label: '插件市场' },
  { id: 'plugin_manager', icon: '📦', label: '插件管理' },
  { id: 'mcp_server', icon: '🔌', label: 'MCP服务' },
  { id: 'chat', icon: '💬', label: '对话' },
  { id: 'soul', icon: '✨', label: '灵魂' },
  { id: 'personality', icon: '🎭', label: '人格' },
  { id: 'knowledge', icon: '📚', label: '知识库' },
  { id: 'voice', icon: '🎤', label: '语音' },
  { id: 'autonomy', icon: '🧠', label: '自主' },
  { id: 'settings', icon: '⚙️', label: '设置' },
];

interface SidebarProps {
  activePage: string;
  onNavigate: (page: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activePage, onNavigate }) => {
  return (
    <div className="w-14 bg-gray-900/80 backdrop-blur-sm flex flex-col items-center py-4 border-r border-gray-800/50">
      <div className="mb-4 flex-shrink-0">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-bold text-sm animate-float">
          M
        </div>
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-hidden flex flex-col gap-2 py-1 px-1 scrollbar-thin">
        {navItems.map((item) => (
          <motion.button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className={`w-11 h-11 rounded-2xl flex flex-col items-center justify-center transition-all duration-300 flex-shrink-0 ${
              activePage === item.id
                ? 'bg-primary/20 text-primary/80 border border-primary/40 backdrop-blur-sm hover:bg-primary/30 transform scale-105'
                : 'text-gray-400 hover:bg-gray-800/50 hover:text-white backdrop-blur-sm hover:border-gray-700/50'
            }`}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            title={item.label}
          >
            <span className="text-xl">{item.icon}</span>
          </motion.button>
        ))}
      </div>
    </div>
  );
};

export default Sidebar;
export { navItems };