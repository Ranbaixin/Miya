import { useState } from 'react';
import { motion } from 'framer-motion';
import SystemMonitorPanel from '../components/SystemMonitorPanel';
import DataRing from '../components/DataRing';

interface ProcessInfo {
  pid: number;
  name: string;
  cpu: number;
  memory: number;
}

const defaultProcesses: ProcessInfo[] = [
  { pid: 1, name: 'Miya Core', cpu: 12, memory: 245 },
  { pid: 2, name: 'QQ Bridge', cpu: 5, memory: 128 },
  { pid: 3, name: 'Web Server', cpu: 3, memory: 89 },
  { pid: 4, name: 'Memory Engine', cpu: 8, memory: 156 },
  { pid: 5, name: 'ToolNet', cpu: 2, memory: 67 },
];

const SystemsPage: React.FC = () => {
  const [processes] = useState<ProcessInfo[]>(defaultProcesses);

  return (
    <div className="p-4 overflow-auto h-full space-y-4">
      <div className="text-cyan-400 text-sm font-medium">系统监控</div>
      
      <div className="grid grid-cols-2 gap-4">
        <SystemMonitorPanel />
        
        <div className="glass-panel p-4 space-y-4">
          <div className="text-cyan-400 text-xs">进程状态</div>
          <div className="space-y-2">
            {processes.map((proc) => (
              <div key={proc.pid} className="flex items-center justify-between p-2 bg-black/20 rounded">
                <div>
                  <div className="text-sm text-gray-300">{proc.name}</div>
                  <div className="text-[10px] text-gray-500">PID: {proc.pid}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-cyan-400">CPU: {proc.cpu}%</div>
                  <div className="text-[10px] text-gray-500">MEM: {proc.memory}MB</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

       <div className="grid grid-cols-3 gap-4">
         <div className="glass-panel p-4">
           <div className="text-cyan-400 text-xs mb-2">CPU 使用率</div>
           <DataRing 
             value={38} 
             label="CPU" 
             color="rgba(0, 188, 212, 0.3)"
             size={100}
           />
         </div>
         
         <div className="glass-panel p-4">
           <div className="text-cyan-400 text-xs mb-2">内存使用</div>
           <DataRing 
             value={68} 
             label="内存" 
             color="rgba(156, 39, 176, 0.3)"
             size={100}
           />
         </div>
         
         <div className="glass-panel p-4">
           <div className="text-cyan-400 text-xs mb-2">网络 I/O</div>
           <DataRing 
             value={25} 
             label="网络" 
             color="rgba(255, 193, 7, 0.3)"
             size={100}
           />
         </div>
       </div>
    </div>
  );
};

export default SystemsPage;