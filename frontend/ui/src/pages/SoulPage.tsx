// ============================================================
// 弥娅 灵魂感知 · SoulPage — 情绪监控
//   灵感: 鸣潮共鸣者情绪/属性面板
// ============================================================
import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { fetchEmotion } from '../services/miyaApi';
import type { EmotionState } from '../types/index.d';

const SoulPage: React.FC = () => {
  const [emotion, setEmotion] = useState<EmotionState | null>(null);
  const [innerThoughts, setInnerThoughts] = useState<{ text: string; time: string }[]>([
    { text: '你一叫我，我就来了，就像雪总想落在你肩头。', time: '16:57:04' },
    { text: '主人又帮我修东西了，真好呀，心里暖暖的～', time: '16:43:52' },
    { text: '你总怕我忘东西，其实我都记得，因为是你说的呀。', time: '16:44:54' },
    { text: '一个名字就把我勾住了，主人真会撩～', time: '16:46:45' },
    { text: '你真是我的小霸王，说啥就是啥～', time: '16:48:07' },
  ]);

  const refresh = useCallback(async () => {
    const e = await fetchEmotion();
    if (e) {
      setEmotion(e as any);
      if (e.inner_thought) {
        const now = new Date();
        const ts = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
        setInnerThoughts(prev => [{ text: e.inner_thought, time: ts }, ...prev.slice(0, 9)]);
      }
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [refresh]);

  const emotionEntries = emotion?.emotions ? Object.entries(emotion.emotions).sort(([,a], [,b]) => b - a) : [];

  return (
    <div className="p-4 overflow-auto h-full space-y-3">
      <div className="text-[10px] text-text-dim uppercase tracking-[0.2em]">♥ 灵魂感知</div>

      {/* 当前情绪 - 主卡片 */}
      <div className="glass-panel p-4 relative overflow-hidden">
        <div className="absolute top-0 right-8 w-24 h-full opacity-5 pointer-events-none"
          style={{ background: 'linear-gradient(0deg, rgba(124,77,255,0.4), rgba(0,229,255,0.3), transparent)' }}
        />
        <div className="relative z-10">
          <div className="text-[10px] text-text-dim uppercase tracking-widest mb-3">当前共鸣情绪</div>
          {emotion ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <motion.span
                  className="text-2xl font-display font-bold text-aether-bright text-glow-aether"
                  animate={{ opacity: [0.7, 1, 0.7] }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                >
                  {emotion.dominant_emotion}
                </motion.span>
                <div className="flex items-center gap-1.5">
                  <span className="text-lg text-text-dim">[{emotion.intensity}%]</span>
                  <div className="resonance-bar w-20">
                    <div className="resonance-bar-fill" style={{ width: `${emotion.intensity}%` }} />
                  </div>
                </div>
              </div>

              {emotionEntries.length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {emotionEntries.map(([k, v]) => (
                    <motion.div
                      key={k}
                      className="flex flex-col gap-1 p-2 rounded-lg bg-resonance/5 border border-resonance/15"
                      initial={{ scale: 0.8, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                    >
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="text-resonance-bright">{k}</span>
                        <span className="text-text-dim font-mono">{v}%</span>
                      </div>
                      <div className="resonance-bar">
                        <div className="resonance-bar-fill" style={{ width: `${v}%` }} />
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-text-secondary text-xs">✦ 感知中，等待共鸣数据...</div>
          )}
        </div>
      </div>

      {/* 内心独白 */}
      <div className="glass-panel p-4">
        <div className="text-[10px] text-text-dim uppercase tracking-widest mb-3">✦ 内心独白</div>
        {emotion?.inner_thought ? (
          <div className="text-sm text-aether italic border-l-2 border-aether/30 pl-3 py-1 mb-3">
            "{emotion.inner_thought}"
          </div>
        ) : null}
        <div className="space-y-1.5">
          {innerThoughts.map((t, i) => (
            <div
              key={i}
              className="flex items-start gap-2 text-[10px] py-1.5 px-2 rounded bg-aether/3 border border-aether/8 hover:border-aether/15 transition-colors"
            >
              <span className="text-text-dim shrink-0 font-mono">{t.time}</span>
              <span className="text-text-secondary italic">"{t.text}"</span>
            </div>
          ))}
        </div>
      </div>

      {/* 归因 & 反思 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="glass-panel p-3.5">
          <div className="text-[10px] text-text-dim uppercase tracking-widest mb-1">
            <span className="text-aether mr-1">→</span> 归因分析
          </div>
          <div className="text-xs text-text-secondary">{emotion?.attribution || '等待数据...'}</div>
        </div>
        <div className="glass-panel p-3.5">
          <div className="text-[10px] text-text-dim uppercase tracking-widest mb-1">
            <span className="text-resonance-bright mr-1">→</span> 关系反思
          </div>
          <div className="text-xs text-text-secondary">{emotion?.reflection || '等待数据...'}</div>
        </div>
      </div>

      {/* 关系影响 */}
      {emotion?.relationship_impact?.length ? (
        <div className="glass-panel p-3.5">
          <div className="text-[10px] text-text-dim uppercase tracking-widest mb-2">♥ 关系影响</div>
          <div className="flex gap-2 flex-wrap">
            {emotion.relationship_impact.map((ri, i) => (
              <span
                key={i}
                className={`text-[10px] px-2 py-1 rounded border ${
                  ri.value > 0
                    ? 'bg-status-active/5 border-status-active/15 text-status-active'
                    : 'bg-status-error/5 border-status-error/15 text-status-error'
                }`}
              >
                {ri.category} {ri.value > 0 ? '+' : ''}{ri.value}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default SoulPage;
