import { motion } from 'framer-motion';
import RuntimeInfoPanel from '../components/RuntimeInfoPanel';
import ConnectionStatusPanel from '../components/ConnectionStatusPanel';
import QuickActionsPanel from '../components/QuickActionsPanel';
import MessageHistoryPanel from '../components/MessageHistoryPanel';
import ToolLogPanel from '../components/ToolLogPanel';
import useMiyaQQData from '../hooks/useMiyaQQData';

interface DashboardStats {
  messages: number;
  groups: number;
  friends: number;
  tools: number;
}

const DashboardPage: React.FC<{ stats: DashboardStats }> = ({ stats }) => {
  const miyaData = useMiyaQQData();
  
  const statCards = [
    { label: '消息', value: stats.messages, icon: '💬', color: 'text-cyan-400' },
    { label: '群聊', value: stats.groups, icon: '👥', color: 'text-purple-400' },
    { label: '好友', value: stats.friends, icon: '👤', color: 'text-pink-400' },
    { label: '工具', value: stats.tools, icon: '🔧', color: 'text-yellow-400' },
  ];

  return (
    <div className="p-4 overflow-auto h-full space-y-4">
      <div className="text-cyan-400 text-sm font-medium">仪表盘</div>
      
      <div className="grid grid-cols-4 gap-3">
        {statCards.map((card) => (
          <motion.div
            key={card.label}
            className="glass-panel p-4"
            whileHover={{ scale: 1.02 }}
          >
            <div className="text-2xl mb-1">{card.icon}</div>
            <div className="text-3xl font-bold text-white">{card.value}</div>
            <div className={`text-xs ${card.color}`}>{card.label}</div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <RuntimeInfoPanel />
        <ConnectionStatusPanel />
        <ToolLogPanel />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <QuickActionsPanel onSendMessage={miyaData.sendMessage} />
        <MessageHistoryPanel />
      </div>
    </div>
  );
};

export default DashboardPage;