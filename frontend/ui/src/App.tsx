// ============================================================
// 弥娅运维中心 · MIYA Ops Center v7.0
//   灵感: 鸣潮 共鸣者展示 — 重构为信息监控与文件配置中心
// ============================================================
import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CosmicBackground from './components/CosmicBackground';
import Header from './components/Header';
import StatusBar from './components/StatusBar';
import NavTabs, { NavTab } from './components/NavTabs';
import SystemOverviewPage from './pages/SystemOverviewPage';
import PlatformPage from './pages/PlatformPage';
import HealthPage from './pages/HealthPage';
import ResourcePage from './pages/ResourcePage';
import ModelPoolPage from './pages/ModelPoolPage';
import AgentNetworkPage from './pages/AgentNetworkPage';
import MessageQueuePage from './pages/MessageQueuePage';
import MemoryPage from './pages/MemoryPage';
import SchedulerPage from './pages/SchedulerPage';
import TerminalPage from './pages/TerminalPage';
import LogViewerPage from './pages/LogViewerPage';
import ConfigCenterPage from './pages/ConfigCenterPage';
import PermissionsPage from './pages/PermissionsPage';
import { useMiyaConnection, useModels, useEmotion, useMemory, usePersonality, usePlatforms, useSystemMetrics } from './services/miyaApi';

const tabs: NavTab[] = [
  { id: 'overview', icon: '◈', label: '总览' },
  { id: 'health', icon: '♥', label: '健康' },
  { id: 'platforms', icon: '▣', label: '平台' },
  { id: 'resources', icon: '◉', label: '资源' },
  { id: 'models', icon: '◆', label: '模型' },
  { id: 'agents', icon: '⬡', label: 'Agent' },
  { id: 'flow', icon: '≣', label: '消息' },
  { id: 'memory', icon: '◎', label: '记忆' },
  { id: 'scheduler', icon: '↻', label: '调度' },
  { id: 'terminal', icon: '>', label: '终端' },
  { id: 'logs', icon: '▷', label: '日志' },
  { id: 'config', icon: '⚙', label: '配置' },
  { id: 'auth', icon: '☰', label: '权限' },
];

const anim = {
  initial: { opacity: 0, y: 8, filter: 'blur(4px)' },
  animate: { opacity: 1, y: 0, filter: 'blur(0px)' },
  exit: { opacity: 0, y: -6, filter: 'blur(4px)' },
  transition: { duration: 0.3, ease: 'easeOut' as const },
};

function App() {
  const [activePage, setActivePage] = useState('overview');
  const { connected } = useMiyaConnection();
  const { metrics } = useSystemMetrics();
  const { models } = useModels();
  const { emotion } = useEmotion();
  const { stats: memStats } = useMemory();
  const { personality } = usePersonality();
  const { platforms } = usePlatforms();
  const [runtimeDuration, setRuntimeDuration] = useState(0);

  const subsystemState = {
    mlink: true,
    memorynet: true,
    toolnet: true,
    webnet: true,
    qqnet: (platforms || []).some((p: any) => p.status === 'online'),
    tts: true,
    scheduler: true,
    proactive: true,
  };

  const fmt = useCallback((s: number) => {
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
  }, []);

  useEffect(() => {
    const t = setInterval(() => setRuntimeDuration(d => d + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const domEmotion = emotion?.dominant_emotion || '—';
  const queueSize = 0;

  const renderPage = () => {
    const wrap = (key: string, el: React.ReactNode) => (
      <motion.div key={key} {...anim} className="h-full">{el}</motion.div>
    );
    switch (activePage) {
      case 'overview': return wrap('overview', <SystemOverviewPage metrics={metrics} />);
      case 'health': return wrap('health', <HealthPage />);
      case 'platforms': return wrap('platforms', <PlatformPage />);
      case 'resources': return wrap('resources', <ResourcePage />);
      case 'models': return wrap('models', <ModelPoolPage />);
      case 'agents': return wrap('agents', <AgentNetworkPage />);
      case 'flow': return wrap('flow', <MessageQueuePage />);
      case 'memory': return wrap('memory', <MemoryPage />);
      case 'scheduler': return wrap('scheduler', <SchedulerPage />);
      case 'terminal': return wrap('terminal', <TerminalPage />);
      case 'logs': return wrap('logs', <LogViewerPage />);
      case 'config': return wrap('config', <ConfigCenterPage />);
      case 'auth': return wrap('auth', <PermissionsPage />);
      default: return null;
    }
  };

  return (
    <div className="flex flex-col h-screen relative text-text-primary bg-void-deep">
      <CosmicBackground />

      <Header
        connected={connected}
        modelCount={models?.length || 0}
        queueSize={queueSize}
        currentEmotion={domEmotion}
        emotionIntensity={emotion?.intensity || 0}
        currentForm={personality?.current_form || '绯雪态'}
        uptime={fmt(runtimeDuration)}
      />

      <div className="relative z-10 border-b border-border-glass bg-void-panel/50 backdrop-blur-md">
        <NavTabs tabs={tabs} activeTab={activePage} onTabChange={setActivePage} />
      </div>

      <div className="flex-1 overflow-auto relative min-h-0">
        <AnimatePresence mode="wait">
          {renderPage()}
        </AnimatePresence>
      </div>

      <StatusBar
        connected={connected}
        runtimeDuration={metrics?.uptime_seconds || runtimeDuration}
        subsystems={subsystemState}
        memoryStats={{
          total: memStats?.total || 0,
          long_term: memStats?.long_term || 0,
          short_term: memStats?.short_term || 0,
          emotional: memStats?.emotional || 0,
        }}
      />
    </div>
  );
}

export default App;
