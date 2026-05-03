import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import DataRing from '../components/DataRing';

interface AutonomySettings {
  enabled: boolean;
  auto_response: boolean;
  auto_memory: boolean;
  auto_reflection: boolean;
  proactive_initiative: number;
  decision_threshold: number;
  response_delay: number;
  max_autonomy_loops: number;
}

interface AutonomyLog {
  id: string;
  type: 'decision' | 'action' | 'reflection';
  content: string;
  time: string;
  confidence: number;
}

const AutonomyPage: React.FC = () => {
  const [settings, setSettings] = useState<AutonomySettings>({
    enabled: true,
    auto_response: true,
    auto_memory: true,
    auto_reflection: true,
    proactive_initiative: 50,
    decision_threshold: 0.7,
    response_delay: 2,
    max_autonomy_loops: 3,
  });

  const [logs, setLogs] = useState<AutonomyLog[]>([
    { id: '1', type: 'decision', content: '检测到用户情绪低落，主动提供安慰', time: '14:30:25', confidence: 0.92 },
    { id: '2', type: 'action', content: '自动保存重要对话到记忆系统', time: '14:28:15', confidence: 0.88 },
    { id: '3', type: 'reflection', content: '分析对话模式: 用户最近偏好安静的环境', time: '14:25:00', confidence: 0.85 },
    { id: '4', type: 'decision', content: '选择更温柔的语气回应', time: '14:20:45', confidence: 0.90 },
    { id: '5', type: 'action', content: '触发情感共鸣模块', time: '14:15:30', confidence: 0.87 },
  ]);

  const [stats, setStats] = useState({
    decisions: 156,
    actions: 89,
    reflections: 42,
    autonomousRate: 68,
  });

  const [expanded, setExpanded] = useState(true);

  const getLogIcon = (type: string) => {
    switch (type) {
      case 'decision': return '🧠';
      case 'action': return '⚡';
      case 'reflection': return '🤔';
      default: return '💭';
    }
  };

  const getLogColor = (type: string) => {
    switch (type) {
      case 'decision': return 'border-cyan-500/30';
      case 'action': return 'border-purple-500/30';
      case 'reflection': return 'border-amber-500/30';
      default: return 'border-gray-500/30';
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div className="glass-panel p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🧠</span>
            <div>
              <div className="text-white font-medium">自主决策系统</div>
              <div className="text-gray-400 text-sm">Adaptive Autonomy System</div>
            </div>
          </div>
          <label className="flex items-center gap-2">
            <span className="text-gray-300 text-sm">启用</span>
            <input
              type="checkbox"
              checked={settings.enabled}
              onChange={(e) => setSettings({ ...settings, enabled: e.target.checked })}
              className="w-5 h-5 accent-cyan-500"
            />
          </label>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="bg-gray-800/30 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-cyan-400">{stats.decisions}</div>
            <div className="text-gray-400 text-xs">决策次数</div>
          </div>
          <div className="bg-gray-800/30 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-purple-400">{stats.actions}</div>
            <div className="text-gray-400 text-xs">执行动作</div>
          </div>
          <div className="bg-gray-800/30 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-amber-400">{stats.reflections}</div>
            <div className="text-gray-400 text-xs">反思次数</div>
          </div>
          <div className="bg-gray-800/30 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-green-400">{stats.autonomousRate}%</div>
            <div className="text-gray-400 text-xs">自主率</div>
          </div>
        </div>
      </div>

      {settings.enabled && (
        <>
          <div className="glass-panel p-4">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-xl">⚙️</span>
              <div className="text-white font-medium">决策配置</div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-gray-300">自动回复</div>
                  <div className="text-gray-500 text-xs">无需等待直接响应</div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.auto_response}
                  onChange={(e) => setSettings({ ...settings, auto_response: e.target.checked })}
                  className="w-5 h-5 accent-cyan-500"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="text-gray-300">自动记忆</div>
                  <div className="text-gray-500 text-xs">自动存储重要信息</div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.auto_memory}
                  onChange={(e) => setSettings({ ...settings, auto_memory: e.target.checked })}
                  className="w-5 h-5 accent-cyan-500"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="text-gray-300">自动反思</div>
                  <div className="text-gray-500 text-xs">周期性自我反思</div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.auto_reflection}
                  onChange={(e) => setSettings({ ...settings, auto_reflection: e.target.checked })}
                  className="w-5 h-5 accent-cyan-500"
                />
              </div>
            </div>
          </div>

          <div className="glass-panel p-4">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-xl">📊</span>
              <div className="text-white font-medium">参数调整</div>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">主动程度</span>
                  <span className="text-cyan-400">{settings.proactive_initiative}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={settings.proactive_initiative}
                  onChange={(e) => setSettings({ ...settings, proactive_initiative: parseInt(e.target.value) })}
                  className="w-full accent-cyan-500"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>保守</span>
                  <span>激进</span>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">决策置信度阈值</span>
                  <span className="text-cyan-400">{settings.decision_threshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="0.95"
                  step="0.05"
                  value={settings.decision_threshold}
                  onChange={(e) => setSettings({ ...settings, decision_threshold: parseFloat(e.target.value) })}
                  className="w-full accent-cyan-500"
                />
              </div>

              <div>
                <div className="text-gray-400 text-sm mb-2">响应延迟 (秒)</div>
                <input
                  type="number"
                  min="0"
                  max="10"
                  value={settings.response_delay}
                  onChange={(e) => setSettings({ ...settings, response_delay: parseInt(e.target.value) })}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>

              <div>
                <div className="text-gray-400 text-sm mb-2">最大自主循环</div>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={settings.max_autonomy_loops}
                  onChange={(e) => setSettings({ ...settings, max_autonomy_loops: parseInt(e.target.value) })}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
            </div>
          </div>

          <div className="glass-panel p-4">
            <div 
              className="flex items-center justify-between cursor-pointer"
              onClick={() => setExpanded(!expanded)}
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">📝</span>
                <div className="text-white font-medium">决策日志</div>
                <span className="text-gray-500 text-sm">({logs.length})</span>
              </div>
              <span className={`transform transition-transform ${expanded ? 'rotate-180' : ''}`}>▼</span>
            </div>

            {expanded && (
              <div className="mt-4 space-y-2 max-h-64 overflow-y-auto">
                {logs.map(log => (
                  <div 
                    key={log.id}
                    className={`p-3 bg-gray-800/30 rounded-lg border-l-2 ${getLogColor(log.type)}`}
                  >
                    <div className="flex items-start gap-2">
                      <span>{getLogIcon(log.type)}</span>
                      <div className="flex-1">
                        <div className="text-gray-200 text-sm">{log.content}</div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-gray-500 text-xs">{log.time}</span>
                          <span className="text-cyan-500 text-xs">
                            置信度: {(log.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {!settings.enabled && (
        <div className="glass-panel p-8 text-center">
          <span className="text-4xl">💤</span>
          <div className="text-gray-400 mt-4">自主决策系统已禁用</div>
          <div className="text-gray-500 text-sm mt-2">启用后将开始自主学习和决策</div>
        </div>
      )}
    </div>
  );
};

export default AutonomyPage;