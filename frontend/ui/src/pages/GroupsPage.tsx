import { useState } from 'react';
import DataRing from '../components/DataRing';
import type { GroupData } from '../hooks/useMiyaQQData';

interface GroupsPageProps {
  groups?: GroupData[];
}

const defaultGroups: GroupData[] = [
  { id: '123456789', name: '索多玛', member_count: 487, message_count: 12450, last_active: '2分钟前' },
  { id: '987654321', name: '水群摸鱼', member_count: 234, message_count: 8923, last_active: '5分钟前' },
  { id: '456789123', name: '原神交流', member_count: 156, message_count: 4521, last_active: '15分钟前' },
  { id: '321654987', name: '崩坏星穹', member_count: 89, message_count: 1234, last_active: '1小时前' },
  { id: '789123456', name: '测试群', member_count: 12, message_count: 89, last_active: '昨天' },
];

const GroupsPage: React.FC<GroupsPageProps> = ({ groups = defaultGroups }) => {
  const [search, setSearch] = useState('');
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);

  const filtered = search.trim()
    ? groups.filter(g => 
        g.name.toLowerCase().includes(search.toLowerCase())
      )
    : groups;

  const totalMembers = groups.reduce((sum, g) => sum + g.member_count, 0);
  const totalMessages = groups.reduce((sum, g) => sum + g.message_count, 0);

  return (
    <div className="p-4 space-y-4">
       <div className="grid grid-cols-3 gap-4">
         <DataRing 
           value={groups.length} 
           label="群数量" 
           color="rgba(0, 188, 212, 0.3)"
           size={100}
         />
         <DataRing 
           value={totalMembers} 
           label="总成员" 
           color="rgba(156, 39, 176, 0.3)"
           size={100}
         />
         <DataRing 
           value={totalMessages} 
           label="消息数" 
           color="rgba(255, 193, 7, 0.3)"
           size={100}
         />
       </div>

      <div className="glass-panel p-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索群..."
          className="w-full bg-black/20 rounded px-3 py-2 text-sm text-gray-300 outline-none"
        />
      </div>

      <div className="space-y-2 max-h-[calc(100vh-320px)] overflow-y-auto">
        {filtered.map(group => (
          <div
            key={group.id}
            onClick={() => setSelectedGroup(group.id)}
            className={`glass-panel p-4 cursor-pointer transition-all ${
              selectedGroup === group.id ? 'border-cyan-500' : ''
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="text-white font-medium">{group.name}</div>
                <div className="text-xs text-gray-500 mt-1">ID: {group.id}</div>
              </div>
              <div className="text-right">
                <div className="text-sm text-cyan-400">{group.member_count}人</div>
                <div className="text-xs text-gray-500">{group.last_active}</div>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-cyan-500/10">
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">消息: {group.message_count.toLocaleString()}</span>
                <span className="text-purple-500">人均 {Math.round(group.message_count / group.member_count)}条</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default GroupsPage;