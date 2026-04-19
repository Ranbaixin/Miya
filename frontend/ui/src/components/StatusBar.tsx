import { } from 'react';

interface StatusBarProps {
  connected: boolean;
  runtimeDuration: number;
  formatDuration: (s: number) => string;
}

const StatusBar: React.FC<StatusBarProps> = ({ connected, runtimeDuration, formatDuration }) => {
  return (
    <div className="h-7 bg-[#1a1a1a] flex items-center justify-between px-4 text-xs text-gray-500 border-t border-[#2a2a2a]">
      <div className="flex items-center gap-4">
        <span className={`flex items-center gap-1.5 ${connected ? 'text-green-500' : 'text-red-500'}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
          {connected ? '在线' : '离线'}
        </span>
      </div>

      <div className="flex items-center gap-4">
        <span>运行 {formatDuration(runtimeDuration)}</span>
        <span className="text-gray-600">v4.3.0</span>
      </div>
    </div>
  );
};

export default StatusBar;