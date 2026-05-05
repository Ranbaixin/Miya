import { useState } from 'react';
import { motion } from 'framer-motion';
import { useCognitiveProfiles, miyaAPI } from '../services/miyaApi';

interface CognitiveEvent {
  id: string;
  document: string;
  metadata: Record<string, any>;
  score?: number;
}

const CognitivePage: React.FC = () => {
  const { profiles, loading, refresh } = useCognitiveProfiles();
  const [entityType, setEntityType] = useState<'user' | 'group'>('user');
  const [entityId, setEntityId] = useState('');
  const [profileContent, setProfileContent] = useState('');
  const [events, setEvents] = useState<CognitiveEvent[]>([]);
  const [eventQuery, setEventQuery] = useState('');
  const [loadingProfile, setLoadingProfile] = useState(false);

  const defaultProfiles = [
    { id: '1', entity_type: 'user', entity_id: '123456', document: '昵称: 佳\nQQ: 123456\n标签: 主人,最爱的人', score: 0.95 },
    { id: '2', entity_type: 'group', entity_id: '987654321', document: '群名: 索多玛\n群号: 987654321\n标签: 核心群', score: 0.88 },
  ];

  const displayProfiles = profiles.length > 0 ? profiles : defaultProfiles;

  const handleSearchProfile = async () => {
    if (!entityId.trim()) return;
    setLoadingProfile(true);
    try {
      const result = await miyaAPI.getCognitiveProfile(entityType, entityId);
      if (result) {
        setProfileContent(typeof result === 'string' ? result : JSON.stringify(result, null, 2));
      } else {
        setProfileContent('未找到相关侧写');
      }
      
      const eventsResult = await miyaAPI.getCognitiveEvents({
        entity_type: entityType,
        entity_id: entityId,
        query: eventQuery || undefined,
        limit: 20,
      });
      if (eventsResult) setEvents(eventsResult);
    } catch (e: any) {
      setProfileContent(`加载失败: ${e.message}`);
    }
    setLoadingProfile(false);
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-cyan-400 text-sm font-bold">认知记忆</div>
        <button
          onClick={() => refresh()}
          className="px-2 py-1 text-xs rounded bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 transition-colors"
        >
          刷新
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="glass-panel p-4">
          <div className="text-white text-xs font-medium mb-3">用户/群侧写</div>
          {loading ? (
            <div className="text-center text-xs text-gray-500 py-8">加载中...</div>
          ) : (
            <div className="space-y-2 max-h-[50vh] overflow-y-auto pr-2">
              {displayProfiles.map((profile, idx) => (
                <motion.div
                  key={profile.id || idx}
                  className="p-2 rounded bg-black/20 border-l-2 border-purple-500/50 cursor-pointer"
                  style={{ borderLeftColor: profile.entity_type === 'user' ? '#06b6d4' : '#8b5cf6' }}
                  whileHover={{ x: 2, backgroundColor: 'rgba(255,255,255,0.05)' }}
                  onClick={() => {
                    setEntityType(profile.entity_type as 'user' | 'group');
                    setEntityId(profile.entity_id);
                    if (profile.document) setProfileContent(profile.document);
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-cyan-400">
                      {profile.entity_type === 'user' ? '👤' : '👥'} {profile.entity_id}
                    </span>
                    <span className="text-[10px] text-gray-600">
                      {profile.score?.toFixed(2)}
                    </span>
                  </div>
                  <div className="text-[10px] text-gray-400 mt-1 line-clamp-2">
                    {profile.document?.slice(0, 80)}...
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        <div className="glass-panel p-4">
          <div className="text-white text-xs font-bold mb-3">侧写查询</div>
          <div className="space-y-2">
            <div className="flex gap-2">
              <select
                value={entityType}
                onChange={(e) => setEntityType(e.target.value as 'user' | 'group')}
                className="bg-black/20 text-xs text-gray-300 rounded px-2 py-1 outline-none"
              >
                <option value="user">用户</option>
                <option value="group">群聊</option>
              </select>
              <input
                type="text"
                value={entityId}
                onChange={(e) => setEntityId(e.target.value)}
                placeholder="ID"
                className="flex-1 bg-black/20 text-xs text-gray-300 rounded px-2 py-1 outline-none placeholder-gray-600"
              />
            </div>
            <input
              type="text"
              value={eventQuery}
              onChange={(e) => setEventQuery(e.target.value)}
              placeholder="搜索事件..."
              className="w-full bg-black/20 text-xs text-gray-300 rounded px-2 py-1 outline-none placeholder-gray-600"
            />
            <button
              onClick={handleSearchProfile}
              disabled={loadingProfile || !entityId.trim()}
              className="w-full py-1.5 text-xs rounded bg-gradient-to-r from-cyan-500/30 to-purple-500/30 text-cyan-400 disabled:opacity-50 transition-all"
            >
              {loadingProfile ? '加载中...' : '查询'}
            </button>
          </div>

          {profileContent && (
            <div className="mt-3 p-2 bg-black/20 rounded text-[10px] text-gray-300 max-h-40 overflow-y-auto whitespace-pre-wrap">
              {profileContent}
            </div>
          )}
        </div>

        <div className="glass-panel p-4">
          <div className="text-white text-xs font-bold mb-3">相关事件</div>
          <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-2">
            {events.length > 0 ? (
              events.map((event, idx) => (
                <motion.div
                  key={event.id || idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.03 }}
                  className="p-2 rounded bg-black/20 border-l-2 border-cyan-500/30"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-gray-500">
                      {event.metadata?.timestamp_local || event.metadata?.timestamp_utc || '--'}
                    </span>
                    <span className="text-[10px] text-purple-400">
                      {event.score?.toFixed(2)}
                    </span>
                  </div>
                  <div className="text-[10px] text-gray-300 mt-1 line-clamp-2">
                    {event.document}
                  </div>
                  {event.metadata && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {event.metadata.perspective && (
                        <span className="text-[8px] px-1 rounded bg-purple-500/20 text-purple-400">
                          {event.metadata.perspective}
                        </span>
                      )}
                      {event.metadata.request_type && (
                        <span className="text-[8px] px-1 rounded bg-cyan-500/20 text-cyan-400">
                          {event.metadata.request_type}
                        </span>
                      )}
                    </div>
                  )}
                </motion.div>
              ))
            ) : (
              <div className="text-xs text-gray-600 text-center py-8">暂无事件</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CognitivePage;