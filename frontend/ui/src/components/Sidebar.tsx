// ============================================================
// 弥娅 侧边栏 · 樱梦琉璃
// ============================================================
import { motion } from 'framer-motion';

type NavItem = { id: string; icon: string; label: string };

const sections: { label: string; items: NavItem[] }[] = [
  { label: '核心', items: [{ id: 'dashboard', icon: '◈', label: '仪表盘' }] },
  { label: '系统', items: [
    { id: 'models', icon: '◆', label: '模型池' },
    { id: 'agents', icon: '▣', label: 'Agent' },
    { id: 'platform', icon: '◎', label: '平台' },
    { id: 'queue', icon: '≣', label: '队列' },
  ]},
  { label: '灵魂', items: [
    { id: 'soul', icon: '♥', label: '灵魂' },
    { id: 'personality', icon: '◇', label: '人格' },
    { id: 'memory', icon: '◉', label: '记忆' },
    { id: 'cognitive', icon: '⬡', label: '认知' },
  ]},
  { label: '运维', items: [
    { id: 'logs', icon: '▷', label: '日志' },
    { id: 'tools', icon: '⚙', label: '工具' },
    { id: 'settings', icon: '☰', label: '设置' },
  ]},
];

interface SidebarProps { activePage: string; onNavigate: (page: string) => void; }

const Sidebar: React.FC<SidebarProps> = ({ activePage, onNavigate }) => (
  <div className="w-[54px] bg-[rgba(255,255,255,0.7)] backdrop-blur-xl flex flex-col items-center border-r border-[rgba(240,168,192,0.12)] z-10 relative">
    <motion.div
      className="w-10 h-10 my-3 rounded-xl flex items-center justify-center cursor-pointer relative overflow-hidden"
      style={{ background: 'linear-gradient(135deg, rgba(240,168,192,0.3), rgba(196,181,253,0.3))', border: '1px solid rgba(240,168,192,0.3)' }}
      whileHover={{ scale: 1.1 }}
      onClick={() => onNavigate('dashboard')}
    >
      <span className="font-bold text-[#d4789e] z-10">M</span>
    </motion.div>

    <div className="flex-1 overflow-y-auto w-full px-1.5 space-y-3 py-1 scrollbar-none">
      {sections.map((section) => (
        <div key={section.label} className="space-y-0.5">
          <div className="text-[8px] text-[#b8aec8] uppercase tracking-[0.15em] text-center pt-1">{section.label}</div>
          {section.items.map((item) => (
            <motion.button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-11 h-11 rounded-xl flex flex-col items-center justify-center transition-all duration-300 ${
                activePage === item.id
                  ? 'bg-[rgba(240,168,192,0.12)] text-[#d4789e] border border-[rgba(240,168,192,0.25)] shadow-[0_0_10px_rgba(240,168,192,0.1)]'
                  : 'text-[#b8aec8] hover:text-[#887c9e] hover:bg-[rgba(240,168,192,0.04)]'
              }`}
              whileHover={{ scale: 1.08 }}
              whileTap={{ scale: 0.92 }}
              title={item.label}
            >
              <span className="text-base">{item.icon}</span>
            </motion.button>
          ))}
        </div>
      ))}
    </div>

    <div className="mb-3">
      <div className="w-2 h-2 rounded-full bg-[#a7f3d0] shadow-[0_0_6px_rgba(167,243,208,0.4)] animate-pulse" />
    </div>
  </div>
);

export default Sidebar;
