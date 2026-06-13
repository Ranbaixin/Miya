import { useState } from 'react';
import DataRing from '../components/DataRing';
import type { FriendData } from '../hooks/useMiyaQQData';

interface FriendsPageProps {
  friends?: FriendData[];
}

const defaultFriends: FriendData[] = [
  { id: '1523878699', nickname: '然鑫', remark: '亲爱的', last_msg: '晚安', last_active: '5分钟前' },
  { id: '123456789', nickname: '测试小号', remark: '测试', last_msg: '你好', last_active: '1小时前' },
  { id: '987654321', nickname: '咕', remark: '咕咕', last_msg: '在吗', last_active: '3小时前' },
  { id: '456789123', nickname: '林', remark: '林', last_msg: '来了', last_active: '昨天' },
];

const FriendsPage: React.FC<FriendsPageProps> = ({ friends = defaultFriends }) => {
  const [search, setSearch] = useState('');
  const [selectedFriend, setSelectedFriend] = useState<string | null>(null);

  const filtered = search.trim()
    ? friends.filter(f => 
        f.nickname.toLowerCase().includes(search.toLowerCase()) ||
        f.remark.toLowerCase().includes(search.toLowerCase())
      )
    : friends;

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <DataRing 
          value={friends.length} 
          label="好友数" 
          color="rgba(0, 188, 212, 0.3)"
          size={100}
        />
        <DataRing 
          value={friends.filter(f => f.last_active.includes('分钟')).length} 
          label="在线" 
          color="rgba(76, 175, 80, 0.3)"
          size={100}
        />
      </div>

      <div className="glass-panel p-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索好友..."
          className="w-full bg-black/20 rounded px-3 py-2 text-sm text-gray-300 outline-none"
        />
      </div>

      <div className="space-y-2 max-h-[calc(100vh-320px)] overflow-y-auto">
        {filtered.map(friend => (
          <div
            key={friend.id}
            onClick={() => setSelectedFriend(friend.id)}
            className={`glass-panel p-4 cursor-pointer transition-all ${
              selectedFriend === friend.id ? 'border-cyan-500' : ''
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-cyan-500/20 flex items-center justify-center text-cyan-400">
                  {friend.nickname[0]}
                </div>
                <div>
                  <div className="text-white font-medium">{friend.remark || friend.nickname}</div>
                  <div className="text-xs text-gray-500">QQ: {friend.id}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-gray-500">{friend.last_active}</div>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-cyan-500/10">
              <div className="text-xs text-gray-400 truncate">{friend.last_msg}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default FriendsPage;