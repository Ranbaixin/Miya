import { useState } from 'react';
import { motion } from 'framer-motion';
import DataRing from '../components/DataRing';
import QQAccountPanel from '../components/QQAccountPanel';

interface FriendData {
  id: string;
  nickname: string;
  remark: string;
  status: string;
}

interface GroupData {
  id: string;
  name: string;
  role: string;
  lastActive: string;
}

const defaultFriends: FriendData[] = [
  { id: '1523878699', nickname: '然鑫', remark: '亲爱的', status: 'online' },
  { id: '123456789', nickname: '咕', remark: '咕咕', status: 'online' },
  { id: '987654321', nickname: '林', remark: '林', status: 'offline' },
  { id: '456789123', nickname: '测试小号', remark: '测试', status: 'online' },
];

const defaultGroups: GroupData[] = [
  { id: '123456789', name: '索多玛', role: '管理员', lastActive: '刚刚' },
  { id: '987654321', name: '水群摸鱼', role: '成员', lastActive: '5分钟前' },
  { id: '456789123', name: '原神交流', role: '成员', lastActive: '15分钟前' },
  { id: '321654987', name: '崩坏星穹', role: '成员', lastActive: '1小时前' },
  { id: '789123456', name: '测试群', role: '群主', lastActive: '昨天' },
];

const AccountPage: React.FC = () => {
  const [friends] = useState<FriendData[]>(defaultFriends);
  const [groups] = useState<GroupData[]>(defaultGroups);
  const [activeTab, setActiveTab] = useState<'friends' | 'groups'>('friends');

  const onlineCount = friends.filter(f => f.status === 'online').length;

    return (
      <div className="p-4 overflow-auto h-full space-y-4">
        <div className="text-cyan-400 text-sm font-medium">账号信息</div>
        
        <div className="grid grid-cols-3 gap-4">
          <QQAccountPanel />
          
          <div className="col-span-2 glass-panel p-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex gap-2">
                <button
                  onClick={() => setActiveTab('friends')}
                  className={`px-3 py-1 rounded text-sm ${
                    activeTab === 'friends' 
                      ? 'bg-cyan-500/20 text-cyan-400' 
                      : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  好友 ({friends.length})
                </button>
                <button
                  onClick={() => setActiveTab('groups')}
                  className={`px-3 py-1 rounded text-sm ${
                    activeTab === 'groups' 
                      ? 'bg-cyan-500/20 text-cyan-400' 
                      : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  群聊 ({groups.length})
                </button>
              </div>
              <div className="text-xs text-gray-500">
                在线: {onlineCount}
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mb-4">
              <DataRing 
                value={friends.length} 
                label="好友总数" 
                color="rgba(0, 188, 212, 0.3)"
                size={80}
              />
              <DataRing 
                value={groups.length} 
                label="群聊总数" 
                color="rgba(156, 39, 176, 0.3)"
                size={80}
              />
            </div>

          <div className="space-y-2 max-h-[calc(100vh-400px)] overflow-y-auto">
            {activeTab === 'friends' ? (
              friends.map((friend) => (
                <div 
                  key={friend.id} 
                  className="flex items-center justify-between p-3 bg-black/20 rounded hover:bg-black/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center text-white font-bold">
                        {friend.nickname[0]}
                      </div>
                      <motion.div
                        className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full ${
                          friend.status === 'online' ? 'bg-green-500' : 'bg-gray-500'
                        }`}
                        animate={friend.status === 'online' ? { scale: [1, 1.2, 1] } : {}}
                        transition={{ duration: 1.5, repeat: Infinity }}
                      />
                    </div>
                    <div>
                      <div className="text-white">{friend.remark || friend.nickname}</div>
                      <div className="text-xs text-gray-500">QQ: {friend.id}</div>
                    </div>
                  </div>
                  <div className={`text-xs px-2 py-1 rounded ${
                    friend.status === 'online' 
                      ? 'bg-green-500/20 text-green-400' 
                      : 'bg-gray-500/20 text-gray-500'
                  }`}>
                    {friend.status === 'online' ? '在线' : '离线'}
                  </div>
                </div>
              ))
            ) : (
              groups.map((group) => (
                <div 
                  key={group.id} 
                  className="flex items-center justify-between p-3 bg-black/20 rounded hover:bg-black/30 transition-colors"
                >
                  <div>
                    <div className="text-white">{group.name}</div>
                    <div className="text-xs text-gray-500">ID: {group.id}</div>
                  </div>
                  <div className="text-right">
                    <div className={`text-xs px-2 py-1 rounded ${
                      group.role === '群主' 
                        ? 'bg-yellow-500/20 text-yellow-400' :
                      group.role === '管理员'
                        ? 'bg-purple-500/20 text-purple-400'
                        : 'bg-gray-500/20 text-gray-500'
                    }`}>
                      {group.role}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">{group.lastActive}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AccountPage;