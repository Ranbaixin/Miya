import { useState } from 'react';
import DataRing from '../components/DataRing';
import MemoryPanel from '../components/MemoryPanel';
import MessageHistoryPanel from '../components/MessageHistoryPanel';
import ToolLogPanel from '../components/ToolLogPanel';
import { useMiyaMemory } from '../services/miyaApi';

const MemoryPage: React.FC = () => {
  const { stats } = useMiyaMemory();
  const [activeTab, setActiveTab] = useState<'memory' | 'messages' | 'logs'>('memory');

  return (
    <div className="p-4 overflow-auto h-full space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-cyan-400 text-sm font-bold">记忆与数据</div>
        <div className="flex gap-2">
          {(['memory', 'messages', 'logs'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                activeTab === tab 
                  ? 'bg-cyan-500/20 text-cyan-400' 
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {tab === 'memory' ? '记忆' : tab === 'messages' ? '消息' : '日志'}
            </button>
          ))}
        </div>
      </div>

       {activeTab === 'memory' && (
         <div className="grid grid-cols-2 gap-4">
           <MemoryPanel />
           
           <div className="glass-panel p-4">
             <div className="text-cyan-400 text-xs mb-3">记忆类型分布</div>
             <div className="grid grid-cols-2 gap-4">
               <DataRing 
                 value={stats.important} 
                 label="重要" 
                 color="rgba(255, 193, 7, 0.3)"
                 size={100}
               />
               <DataRing 
                 value={stats.emotion} 
                 label="情感" 
                 color="rgba(233, 30, 99, 0.3)"
                 size={100}
               />
               <DataRing 
                 value={stats.conversation} 
                 label="对话" 
                 color="rgba(156, 39, 176, 0.3)"
                 size={100}
               />
               <DataRing 
                 value={Math.max(0, stats.total - (stats.important + stats.emotion + stats.conversation))} 
                 label="其他" 
                 color="rgba(158, 158, 158, 0.3)"
                 size={100}
               />
             </div>
           </div>
         </div>
       )}

      {activeTab === 'messages' && (
        <MessageHistoryPanel />
      )}

      {activeTab === 'logs' && (
        <div className="space-y-4">
          <ToolLogPanel />
        </div>
      )}
    </div>
  );
};

export default MemoryPage;