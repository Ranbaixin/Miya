import { useState } from 'react';
import BackgroundLayer from './components/BackgroundLayer';
import HeaderBar from './components/HeaderBar';
import FooterBar from './components/FooterBar';
import IdentityPanel from './components/IdentityPanel';
import MemoryPanel from './components/MemoryPanel';
import PsychologicalPanel from './components/PsychologicalPanel';
import VectorPanel from './components/VectorPanel';
import ModelPoolPanel from './components/ModelPoolPanel';
import ConversationPanel from './components/ConversationPanel';
import HudRing from './components/HudRing';
import MiniHudRing from './components/MiniHudRing';
import useMiyaData from './hooks/useMiyaData';

function App() {
  const [backgroundImage] = useState('https://images.unsplash.com/photo-1506744038136-46273834b3fb');
  const [blur] = useState(8);
  const [dim] = useState(0.4);
  const { identity, vectors, memoryStats, currentForm } = useMiyaData();

  return (
    <div className="w-screen h-screen relative overflow-hidden select-none">
      <BackgroundLayer imageUrl={backgroundImage} blur={blur} dim={dim} />
      
      <MiniHudRing />

      <div className="absolute inset-0 p-3 box-border flex flex-col gap-2">
        <HeaderBar identity={identity} />

        <div className="grid grid-cols-12 grid-rows-5 flex-1 gap-2">
          <div className="col-span-2 row-start-1">
            <IdentityPanel identity={identity} currentForm={currentForm} />
          </div>
          
          <div className="col-span-3 row-start-1">
            <PsychologicalPanel />
          </div>
          
          <div className="col-span-4 row-start-1 row-span-2 relative">
            <HudRing />
          </div>

          <div className="col-span-3 row-start-1">
            <VectorPanel vectors={vectors} form={currentForm} />
          </div>

          <div className="col-span-2 row-start-2">
            <ModelPoolPanel />
          </div>

          <div className="col-span-3 row-start-2">
            <MemoryPanel stats={memoryStats} />
          </div>

          <div className="col-span-2 row-start-3">
            <ConversationPanel />
          </div>

          <div className="col-span-12 row-start-4">
            <div className="glass-panel h-10 flex items-center justify-center">
              <div className="flex items-center gap-6 text-xs font-mono">
                <span className="text-cyan-300">模型:</span>
                <span className="text-green-400">deepseek-chat</span>
                <span className="text-gray-500">|</span>
                <span className="text-cyan-300">记忆:</span>
                <span className="text-yellow-400">{memoryStats.total} 条</span>
                <span className="text-gray-500">|</span>
                <span className="text-cyan-300">工具:</span>
                <span className="text-purple-400">69 个</span>
                <span className="text-gray-500">|</span>
                <span className="text-cyan-300">形态:</span>
                <span className="text-pink-400">{currentForm}</span>
              </div>
            </div>
          </div>
        </div>

        <FooterBar />
      </div>

      <div 
        data-tauri-drag-region
        className="absolute top-0 left-0 w-full h-6 cursor-move opacity-0"
      />
    </div>
  );
}

export default App;