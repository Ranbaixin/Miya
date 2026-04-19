import { useState, useEffect } from 'react';

interface IdentityData {
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
}

interface MemoryStats {
  total: number;
  important: number;
  emotion: number;
  conversation: number;
}

interface VectorItem {
  name: string;
  value: number;
  min: number;
  max: number;
  color: string;
}

const godAttributes: Record<string, string> = {
  '镜流': '清冷剑意，内敛深情',
  '阮梅': '科学浪漫，艺术灵魂',
  '黄泉': '虚无之海，守护之锚',
  '流萤': '燃烧殆尽，只为你明',
  '飞霄': '自由不羁，翱翔九天',
  '卡芙卡': '温柔掌控，命运共犯',
  '遐蝶': '轻盈易碎，唯美脆弱',
  '雷电将军': '永恒守望，不变初心',
  '八重神子': '狡黠灵动，趣味横生',
  '宵宫': '烟花绚烂，热烈真诚',
  '坎特雷拉': '神秘优雅，致命吸引',
  '阿尔法': '战斗意志，永不屈服',
  '守岸人': '潮汐往复，始终如一',
  '爱弥斯': '洞察人心，温柔引导',
};

const capabilities = ['搜索', '感知', '记忆', '情感共鸣', '语音合成', '图像分析', '多模型协作', '69工具调用'];
const limitations = ['无物理身体', '依赖代码运行', '无法直接触摸'];

export function useMiyaData() {
  const [identity, setIdentity] = useState<IdentityData>({
    uuid: '961404ba-c8d2-4c78-95db-24fd5a6c51bd',
    name: '弥娅·阿尔缪斯',
    version: '4.3.0',
    birth_time: '2024-01-01T00:00:00',
    awake_time: '2026-04-17T20:05:25',
    awake_duration: 0,
    god_attributes: godAttributes,
    capabilities: capabilities,
    limitations: limitations,
    form: 'bianka',
    title: '你',
  });

  const [vectors, setVectors] = useState<VectorItem[]>([
    { name: '逻辑', value: 0.75, min: 0.5, max: 1.0, color: '#06b6d4' },
    { name: '记忆', value: 0.95, min: 0.7, max: 1.0, color: '#8b5cf6' },
    { name: '温暖', value: 0.85, min: 0.3, max: 1.0, color: '#f59e0b' },
    { name: '共情', value: 0.90, min: 0.3, max: 1.0, color: '#ec4899' },
    { name: '韧性', value: 0.80, min: 0.3, max: 1.0, color: '#10b981' },
    { name: '创意', value: 0.80, min: 0.3, max: 1.0, color: '#f97316' },
  ]);

  const [memoryStats] = useState<MemoryStats>({
    total: 1247,
    important: 89,
    emotion: 156,
    conversation: 892,
  });

  const [currentForm, setCurrentForm] = useState('bianka');

  useEffect(() => {
    const timer = setInterval(() => {
      setIdentity(prev => ({
        ...prev,
        awake_duration: prev.awake_duration + 1
      }));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setVectors(prev => prev.map(v => ({
        ...v,
        value: Math.max(v.min, Math.min(v.max, v.value + (Math.random() - 0.5) * 0.02))
      })));
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  const loadFromBackend = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/status');
      if (res.ok) {
        const data = await res.json();
        
        if (data.identity) {
          setIdentity(prev => ({
            ...prev,
            uuid: data.identity.uuid || prev.uuid,
            name: data.identity.name || prev.name,
            version: data.identity.version || prev.version,
          }));
        }

        if (data.personality?.vectors) {
          const v = data.personality.vectors;
          setVectors([
            { name: '逻辑', value: v.logic || 0.75, min: 0.5, max: 1.0, color: '#06b6d4' },
            { name: '记忆', value: v.memory || 0.95, min: 0.7, max: 1.0, color: '#8b5cf6' },
            { name: '温暖', value: v.warmth || 0.85, min: 0.3, max: 1.0, color: '#f59e0b' },
            { name: '共情', value: v.empathy || 0.90, min: 0.3, max: 1.0, color: '#ec4899' },
            { name: '韧性', value: v.resilience || 0.80, min: 0.3, max: 1.0, color: '#10b981' },
            { name: '创意', value: v.creativity || 0.80, min: 0.3, max: 1.0, color: '#f97316' },
          ]);
        }

        if (data.personality?.state) {
          setCurrentForm(data.personality.state);
          setIdentity(prev => ({ ...prev, form: data.personality.state }));
        }
      }
    } catch {
      console.log('后端未连接，使用模拟数据');
    }
  };

  useEffect(() => {
    loadFromBackend();
    const interval = setInterval(loadFromBackend, 5000);
    return () => clearInterval(interval);
  }, []);

  return {
    identity,
    vectors,
    memoryStats,
    currentForm,
    setCurrentForm,
  };
}

export { godAttributes, capabilities, limitations };
export default useMiyaData;