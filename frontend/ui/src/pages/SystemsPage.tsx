import { useState, useEffect } from 'react';
import SystemMonitorPanel from '../components/SystemMonitorPanel';
import DataRing from '../components/DataRing';
import { useSystemInfo } from '../services/miyaApi';

interface ProcessInfo {
  pid: number;
  name: string;
  cpu: number;
  memory: number;
}

const SystemsPage: React.FC = () => {
  const systemInfo = useSystemInfo();
  const [processes, setProcesses] = useState<ProcessInfo[]>([]);

  useEffect(() => {
    if (systemInfo) {
      setProcesses([
        { pid: 1, name: 'Miya Core', cpu: systemInfo.cpu_usage_percent, memory: Math.round(systemInfo.memory_used_gb * 1024) },
        { pid: 2, name: 'QQ Bridge', cpu: Math.round(systemInfo.cpu_usage_percent * 0.4), memory: Math.round(systemInfo.memory_used_gb * 512) },
        { pid: 3, name: 'Web Server', cpu: Math.round(systemInfo.cpu_usage_percent * 0.25), memory: Math.round(systemInfo.memory_used_gb * 256) },
        { pid: 4, name: 'Memory Engine', cpu: Math.round(systemInfo.cpu_usage_percent * 0.6), memory: Math.round(systemInfo.memory_used_gb * 384) },
        { pid: 5, name: 'ToolNet', cpu: Math.round(systemInfo.cpu_usage_percent * 0.15), memory: Math.round(systemInfo.memory_used_gb * 128) },
      ]);
    }
  }, [systemInfo]);

  const cpuPercent = systemInfo?.cpu_usage_percent ?? 0;
  const memPercent = systemInfo?.memory_usage_percent ?? 0;

  return (
    <div className="p-4 overflow-auto h-full space-y-4">
      <div className="text-cyan-400 text-sm font-medium">系统监控</div>
      
      {systemInfo && (
        <div className="flex gap-3 text-xs text-gray-400">
          <span>系统: {systemInfo.system_version} ({systemInfo.system_arch})</span>
          <span>Python: {systemInfo.python_version}</span>
          <span>弥娅: {systemInfo.undefined_version}</span>
        </div>
      )}
      
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
             value={cpuPercent} 
             label="CPU" 
             color="rgba(0, 188, 212, 0.3)"
             size={100}
           />
           {systemInfo && (
             <div className="text-[10px] text-gray-500 text-center mt-1">{systemInfo.cpu_model?.slice(0, 30)}</div>
           )}
         </div>
         
         <div className="glass-panel p-4">
           <div className="text-cyan-400 text-xs mb-2">内存使用</div>
           <DataRing 
             value={memPercent} 
             label="内存" 
             color="rgba(156, 39, 176, 0.3)"
             size={100}
           />
           {systemInfo && (
             <div className="text-[10px] text-gray-500 text-center mt-1">
               {systemInfo.memory_used_gb?.toFixed(1)} / {systemInfo.memory_total_gb?.toFixed(1)} GB
             </div>
           )}
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