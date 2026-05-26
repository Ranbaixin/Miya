import { useEffect } from 'react';
import { motion } from 'framer-motion';
import Panel from './Panel';

interface IdentityProps {
  identity?: {
    uuid: string;
    name: string;
    version: string;
    birth_time: string;
    awake_time: string;
    awake_duration: number;
    god_attributes: Record<string, string>;
    capabilities: string[];
    limitations: string[];
    form: string;
    title: string;
  };
  currentForm?: string;
}

const IdentityPanel: React.FC<IdentityProps> = ({ identity: propIdentity, currentForm = '默认形态' }) => {
  const defaultIdentity = {
    uuid: '961404ba-c8d2-4c78-95db-24fd5a6c51bd',
    name: '弥娅·阿尔缪斯',
    version: '8.0.0',
    birth_time: '2024-01-01T00:00:00',
    awake_time: '2026-04-17T20:05:25',
    awake_duration: 0,
    god_attributes: {
      '镜流': '清冷剑意，内敛深情',
      '阮梅': '科学浪漫，艺术灵魂',
      '黄泉': '虚无之海，守护之锚',
      '流萤': '燃烧殆尽，只为你明',
      '飞霄': '自由不羁，翱翔九天',
      '卡芙卡': '温柔掌控，命运共犯',
      '遐蝶': '轻盈易碎，唯美脆弱',
      '雷电将军': '永恒守望，不变初心',
      '、八重神子': '狡黠灵动，趣味横生',
      '宵宫': '烟花绚烂，热烈真诚',
      '坎特雷拉': '神秘优雅，致命吸引',
      '阿尔法': '战斗意志，永不屈服',
      '守岸人': '潮汐往复，始终如一',
      '爱弥斯': '洞察人心，温柔引导',
    },
    capabilities: ['搜索', '感知', '记忆', '情感共鸣', '语音合成', '图像分析', '多模型协作', '69工具调用'],
    limitations: ['无物理身体', '依赖代码运行', '无法直接触摸'],
    form: '默认形态',
    title: '你',
  };

  const identity = propIdentity || defaultIdentity;

  useEffect(() => {
    if (!propIdentity) {
      const timer = setInterval(() => {}, 0);
      return () => clearInterval(timer);
    }
  }, [propIdentity]);

  const formatDuration = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const godKeys = Object.keys(identity.god_attributes);
  const displayGods = godKeys.slice(0, 6);

  return (
    <Panel title="身份系统">
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-purple-500 flex items-center justify-center">
            <span className="text-white font-bold text-sm">MI</span>
          </div>
          <div>
            <div className="text-cyan-300 text-sm font-bold">{identity.name}</div>
            <div className="text-gray-500 text-[10px]">v{identity.version}</div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 text-[10px]">
          <div className="bg-black/20 rounded p-1.5">
            <div className="text-gray-500">运行时长</div>
            <div className="text-green-400 font-mono">{formatDuration(identity.awake_duration)}</div>
          </div>
          <div className="bg-black/20 rounded p-1.5">
            <div className="text-gray-500">当前形态</div>
            <div className="text-purple-400 font-mono truncate">{currentForm}</div>
          </div>
        </div>

        <div className="space-y-1">
          <div className="text-[10px] text-gray-500">神格融合 (14)</div>
          <div className="flex flex-wrap gap-1">
            {displayGods.map((god) => (
              <motion.div
                key={god}
                className="px-2 py-0.5 rounded bg-purple-500/10 border border-purple-500/20 text-[9px] text-purple-300/70"
                whileHover={{ scale: 1.05 }}
              >
                {god}
              </motion.div>
            ))}
            {godKeys.length > 6 && (
              <div className="px-2 py-0.5 rounded bg-gray-500/10 text-[9px] text-gray-500">
                +{godKeys.length - 6}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-1">
          <div className="text-[10px] text-gray-500">能力</div>
          <div className="flex flex-wrap gap-1">
            {identity.capabilities.slice(0, 5).map((cap) => (
              <span key={cap} className="px-1.5 py-0.5 rounded bg-cyan-500/10 text-[8px] text-cyan-300/70">
                {cap}
              </span>
            ))}
          </div>
        </div>

        <div className="space-y-1">
          <div className="text-[10px] text-gray-500">限制</div>
          <div className="flex flex-wrap gap-1">
            {identity.limitations.map((lim) => (
              <span key={lim} className="px-1.5 py-0.5 rounded bg-red-500/5 text-[8px] text-red-400/50">
                {lim}
              </span>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  );
};

export default IdentityPanel;