// ============================================================
// 弥娅 App · 深蓝星渊 Abyssal Star
//   灵感: 鸣潮 共鸣者展示
// ============================================================
import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CosmicBackground from './components/CosmicBackground';
import Header from './components/Header';
import StatusBar from './components/StatusBar';
import NavTabs, { NavTab } from './components/NavTabs';
import DashboardPage from './pages/DashboardPage';
import ModelPoolPage from './pages/ModelPoolPage';
import AgentNetworkPage from './pages/AgentNetworkPage';
import MessageQueuePage from './pages/MessageQueuePage';
import LogViewerPage from './pages/LogViewerPage';
import SoulPage from './pages/SoulPage';
import { useMiyaConnection, useEmotion, useMemory, usePersonality } from './services/miyaApi';

const tabs: NavTab[] = [
  { id: 'dashboard', icon: '◈', label: '共鸣核心' },
  { id: 'models', icon: '◆', label: '模型矩阵' },
  { id: 'agents', icon: '▣', label: 'Agent' },
  { id: 'queue', icon: '≣', label: '消息流' },
  { id: 'soul', icon: '♥', label: '灵魂感知' },
  { id: 'logs', icon: '▷', label: '日志' },
  { id: 'settings', icon: '☰', label: '配置' },
];

const anim = {
  initial: { opacity: 0, y: 8, filter: 'blur(4px)' },
  animate: { opacity: 1, y: 0, filter: 'blur(0px)' },
  exit: { opacity: 0, y: -6, filter: 'blur(4px)' },
  transition: { duration: 0.3, ease: 'easeOut' as const },
};

function App() {
  const [activePage, setActivePage] = useState('dashboard');
  const { connected } = useMiyaConnection();
  const { emotion } = useEmotion();
  const { stats: memStats } = useMemory();
  const { personality } = usePersonality();
  const [runtimeDuration, setRuntimeDuration] = useState(0);
  const [subsystems] = useState({
    mlink: true, memorynet: true, toolnet: true,
    webnet: true, qqnet: true, tts: true,
    scheduler: true, proactive: true,
  });
  const [queueSize] = useState(0);
  const [modelCount] = useState(12);

  const fmt = useCallback((s: number) => {
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
  }, []);

  useEffect(() => {
    const t = setInterval(() => setRuntimeDuration(d => d + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const domEmotion = emotion?.dominant_emotion || '—';

  const renderPage = () => {
    switch (activePage) {
      case 'dashboard': return <motion.div key="dashboard" {...anim} className="h-full"><DashboardPage onNavigate={setActivePage} /></motion.div>;
      case 'models': return <motion.div key="models" {...anim} className="h-full"><ModelPoolPage /></motion.div>;
      case 'agents': return <motion.div key="agents" {...anim} className="h-full"><AgentNetworkPage /></motion.div>;
      case 'queue': return <motion.div key="queue" {...anim} className="h-full"><MessageQueuePage /></motion.div>;
      case 'soul': return <motion.div key="soul" {...anim} className="h-full"><SoulPage /></motion.div>;
      case 'logs': return <motion.div key="logs" {...anim} className="h-full"><LogViewerPage /></motion.div>;
      case 'settings': return (
        <motion.div key="settings" {...anim} className="flex items-center justify-center h-full">
          <div className="glass-panel p-8 text-center max-w-sm">
            <div className="text-aether text-3xl mb-3 font-bold">☰</div>
            <div className="text-text-primary text-sm mb-1">系统配置</div>
            <div className="text-text-secondary text-xs">设置模块即将开放，敬请期待</div>
          </div>
        </motion.div>
      );
      default: return null;
    }
  };

  return (
    <div className="flex flex-col h-screen relative text-text-primary bg-void-deep">
      <CosmicBackground />

      <Header
        connected={connected}
        modelCount={modelCount}
        queueSize={queueSize}
        currentEmotion={domEmotion}
        emotionIntensity={emotion?.intensity || 0}
        currentForm={personality?.current_form || '绯雪态'}
        uptime={fmt(runtimeDuration)}
      />

      {/* 导航标签栏 */}
      <div className="relative z-10 border-b border-border-glass bg-void-panel/50 backdrop-blur-md">
        <NavTabs tabs={tabs} activeTab={activePage} onTabChange={setActivePage} />
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-auto relative min-h-0">
        <AnimatePresence mode="wait">
          {renderPage()}
        </AnimatePresence>
      </div>

      <StatusBar
        connected={connected}
        runtimeDuration={runtimeDuration}
        subsystems={subsystems}
        memoryStats={memStats as any}
      />
    </div>
  );
}

export default App;
