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
  { id: 'emotion', icon: '💕', label: '情感' },
  { id: 'memory', icon: '🧠', label: '记忆' },
  { id: 'cognitive', icon: '🧩', label: '认知' },
  { id: 'tools', icon: '🔧', label: '工具' },
  { id: 'settings', icon: '⚙️', label: '设置' },
];

interface SidebarProps {
  activePage: string;
  onNavigate: (page: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activePage, onNavigate }) => {
  return (
    <div className="w-14 bg-gray-900/80 backdrop-blur-sm flex flex-col items-center py-4 border-r border-gray-800/50">
      <div className="mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-bold text-sm animate-float">
          M
        </div>
      </div>

      <div className="flex-1 flex flex-col gap-2">
        {navItems.map((item) => (
          <motion.button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className={`w-11 h-11 rounded-2xl flex flex-col items-center justify-center transition-all duration-300 ${
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