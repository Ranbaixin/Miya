// ============================================================
// 深蓝星渊 · NavTabs — 顶部分类导航标签栏
//   灵感: 鸣潮共鸣者页面的属性筛选标签
// ============================================================
import { motion } from 'framer-motion';
import { cn } from '../utils';

export interface NavTab {
  id: string;
  icon: string;
  label: string;
}

interface NavTabsProps {
  tabs: NavTab[];
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const NavTabs: React.FC<NavTabsProps> = ({ tabs, activeTab, onTabChange }) => {
  return (
    <div className="flex items-center gap-1 px-4 py-2 overflow-x-auto scrollbar-none">
      {tabs.map((tab) => (
        <motion.button
          key={tab.id}
          className={cn(
            'nav-tab rounded-lg whitespace-nowrap select-none',
            activeTab === tab.id ? 'active' : '',
          )}
          onClick={() => onTabChange(tab.id)}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.96 }}
        >
          <span className="text-sm mr-1.5">{tab.icon}</span>
          {tab.label}
        </motion.button>
      ))}
    </div>
  );
};

export default NavTabs;
