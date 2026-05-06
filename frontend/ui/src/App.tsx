// ============================================================
// 弥娅 App · 樱梦琉璃
// ============================================================
import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import StatusBar from './components/StatusBar';
import StarOceanBackground from './components/StarOceanBackground';
import DashboardPage from './pages/DashboardPage';
import ModelPoolPage from './pages/ModelPoolPage';
import AgentNetworkPage from './pages/AgentNetworkPage';
import MessageQueuePage from './pages/MessageQueuePage';
import LogViewerPage from './pages/LogViewerPage';
import SoulPage from './pages/SoulPage';
import { useMiyaConnection, useEmotion, useMemory, usePersonality } from './services/miyaApi';

const pageTitles: Record<string, string> = {
  dashboard: '仪表盘', models: '模型池', agents: 'Agent网络',
  platform: '平台', queue: '消息队列', soul: '灵魂监控',
  personality: '人格向量', memory: '记忆', cognitive: '认知',
  logs: '日志查看', tools: '工具', settings: '设置',
};

const anim = {
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -4 },
  transition: { duration: 0.22, ease: [0.4, 0, 0.2, 1] },
};

function App() {
  const [activePage, setActivePage] = useState('dashboard');
  const { connected } = useMiyaConnection();
  const { emotion } = useEmotion();
  const { stats: memStats } = useMemory();
  const { personality } = usePersonality();
  const [runtimeDuration, setRuntimeDuration] = useState(0);
  const [subsystems] = useState({ mlink: true, memorynet: true, toolnet: true, webnet: true, qqnet: true, tts: true, scheduler: true, proactive: true });
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
    const k = activePage;
    switch (activePage) {
      case 'dashboard': return <motion.div key={k} {...anim}><DashboardPage /></motion.div>;
      case 'models': return <motion.div key={k} {...anim}><ModelPoolPage /></motion.div>;
      case 'agents': return <motion.div key={k} {...anim}><AgentNetworkPage /></motion.div>;
      case 'queue': return <motion.div key={k} {...anim}><MessageQueuePage /></motion.div>;
      case 'soul': return <motion.div key={k} {...anim}><SoulPage /></motion.div>;
      case 'logs': return <motion.div key={k} {...anim}><LogViewerPage /></motion.div>;
      default: return (
        <motion.div key={k} {...anim} className="flex items-center justify-center h-full">
          <div className="frost-panel p-8 text-center">
            <div className="text-3xl mb-3">✦</div>
            <div className="text-[#d4789e] text-sm mb-1">{pageTitles[activePage] || activePage}</div>
            <div className="text-[#b8aec8] text-xs">模块对接后端 API，实时拉取中...</div>
          </div>
        </motion.div>
      );
    }
  };

  return (
    <div className="flex h-screen text-[#4a4058] relative">
      <StarOceanBackground />
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <div className="flex-1 flex flex-col min-w-0 relative z-10">
        <Header
          title={`弥娅 · ${pageTitles[activePage] || activePage}`}
          connected={connected}
          modelCount={modelCount}
          queueSize={queueSize}
          currentEmotion={domEmotion}
          emotionIntensity={emotion?.intensity || 0}
          currentForm={personality?.current_form || '绯雪态'}
          uptime={fmt(runtimeDuration)}
        />
        <div className="flex-1 overflow-auto relative">
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
    </div>
  );
}

export default App;
