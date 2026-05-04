import { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import StatusBar from './components/StatusBar';
import DashboardPage from './pages/DashboardPage';
import SystemsPage from './pages/SystemsPage';
import EmotionPage from './pages/EmotionPage';
import MemoryPage from './pages/MemoryPage';
import ToolsPage from './pages/ToolsPage';
import SettingsPage from './pages/SettingsPage';
import CognitivePage from './pages/CognitivePage';
import PlatformPage from './pages/PlatformPage';
import PluginMarketPage from './pages/PluginMarketPage';
import PluginManagerPage from './pages/PluginManagerPage';
import MCPServerPage from './pages/MCPServerPage';
import ChatPage from './pages/ChatPage';
import SoulPage from './pages/SoulPage';
import PersonalityVectorPage from './pages/PersonalityVectorPage';
import KnowledgeBasePage from './pages/KnowledgeBasePage';
import VoicePage from './pages/VoicePage';
import AutonomyPage from './pages/AutonomyPage';
import LogsPage from './pages/LogsPage';

const pageTitles: Record<string, string> = {
  dashboard: '仪表盘',
  systems: '系统',
  emotion: '情感',
  memory: '记忆',
  cognitive: '认知',
  tools: '工具',
  platform: '平台',
  plugin_market: '插件市场',
  plugin_manager: '插件管理',
  mcp_server: 'MCP服务',
  chat: '对话',
  soul: '灵魂',
  personality: '人格',
  knowledge: '知识库',
  voice: '语音',
  autonomy: '自主',
  logs: '日志',
  settings: '设置',
};

const backgrounds = [
  { id: 'default', name: '默认', url: 'https://images.unsplash.com/photo-1506744038136-46273834b3fb' },
  { id: 'miya', name: '弥娅定制', url: './background.jpg' },
  { id: 'dark', name: '深色', url: '' },
];

function App() {
  const [activePage, setActivePage] = useState('dashboard');
  const [connected] = useState(true);
  const [runtimeDuration, setRuntimeDuration] = useState(0);
  const [bgId, setBgId] = useState('default');

  const currentBg = backgrounds.find(b => b.id === bgId) || backgrounds[0];

  const getBackgroundStyle = () => {
    if (bgId === 'dark') {
      return {
        background: 'linear-gradient(135deg, rgba(0,20,30,0.95) 0%, rgba(10,10,20,0.9) 100%)',
      };
    }
    return {
      background: 'linear-gradient(135deg, rgba(0,20,30,0.8) 0%, rgba(10,10,20,0.7) 100%)',
      backgroundImage: `url(${currentBg.url})`,
      backgroundSize: 'cover',
      backgroundBlendMode: 'overlay',
    };
  };

  const formatDuration = useCallback((s: number) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setRuntimeDuration(d => d + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const renderPage = () => {
    switch (activePage) {
      case 'dashboard':
        return <DashboardPage stats={{ messages: 156, groups: 5, friends: 4, tools: 69 }} />;
      case 'systems':
        return <SystemsPage />;
      case 'emotion':
        return <EmotionPage />;
      case 'memory':
        return <MemoryPage />;
      case 'cognitive':
        return <CognitivePage />;
      case 'tools':
        return <ToolsPage />;
      case 'platform':
        return <PlatformPage />;
      case 'plugin_market':
        return <PluginMarketPage />;
      case 'plugin_manager':
        return <PluginManagerPage />;
      case 'mcp_server':
        return <MCPServerPage />;
      case 'chat':
        return <ChatPage />;
      case 'soul':
        return <SoulPage />;
      case 'personality':
        return <PersonalityVectorPage />;
      case 'knowledge':
        return <KnowledgeBasePage />;
      case 'voice':
        return <VoicePage />;
      case 'autonomy':
        return <AutonomyPage />;
      case 'logs':
        return <LogsPage />;
      case 'settings':
        return <SettingsPage backgrounds={backgrounds} currentBg={bgId} onBgChange={setBgId} />;
      default:
        return <DashboardPage stats={{ messages: 156, groups: 5, friends: 4, tools: 69 }} />;
    }
  };

  return (
    <div className="flex h-screen text-white" style={getBackgroundStyle()}>
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <div className="flex-1 flex flex-col">
        <Header title={`弥娅 AI 控制台 - ${pageTitles[activePage]}`} />
        <div className="flex-1 overflow-auto">
          {renderPage()}
        </div>
        <StatusBar connected={connected} runtimeDuration={runtimeDuration} formatDuration={formatDuration} />
      </div>
    </div>
  );
}

export default App;