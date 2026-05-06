// ============================================================
// 弥娅 日志查看器 - 终端风格实时日志
// 基于 NapcatQQ 后端日志格式
// ============================================================
import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface LogEntry {
  id: number;
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG';
  module: string;
  message: string;
  thinking?: string;
  detail?: string;
}

const LEVEL_COLORS: Record<string, string> = {
  INFO: 'text-cyan-400',
  WARNING: 'text-yellow-400',
  ERROR: 'text-red-400',
  DEBUG: 'text-gray-400',
};

// 模拟后端日志数据（实际使用时替换为 API 调用）
function generateMockLog(): LogEntry {
  const modules = ['MiyaQQ', 'Miya', 'Miya.MessageQueue', 'Miya.Gestalt', 'Miya.CognitiveEngine', 'Miya.灵魂发生器', 'Miya.AgentHub', 'core.ai_client', 'Miya.DecisionHub'];
  const levels: LogEntry['level'][] = ['INFO', 'INFO', 'INFO', 'WARNING', 'ERROR'];
  const module = modules[Math.floor(Math.random() * modules.length)];
  const level = levels[Math.floor(Math.random() * levels.length)];

  const messages: Record<string, string[]> = {
    MiyaQQ: [
      'QQ消息 -> group | 1523878699(佳)',
      '群: 1092980378(索多玛)',
      '内容: 弥娅，你记得咕 是谁嘛',
      '决策处理 -> 开始',
      '消息分析 -> 弥娅，你记得咕 是谁嘛...',
      '处理完成 -> 耗时: 15.234秒',
      '弥娅回复 -> 记得。刚才在群里发消息的那位，你的群友。...',
      '发送群消息至 1092980378',
      '连接成功！',
      '弥娅 QQ 机器人已启动: 弥娅·阿尔缪斯',
      'UUID: edc00845-ca7d-43fc-add4-21f3d249579c',
    ],
    'Miya.MessageQueue': [
      '[消息队列] 已启动模型处理: model=default',
      '[入队][default] 群聊超级管理员: size=1 group=1092980378 user=1523878699',
      '[发车][default] 群聊超级管理员: group=1092980378 user=1523878699',
      '[完成][default] 群聊超级管理员: 15.40s group=1092980378 user=1523878699',
    ],
    'Miya.Gestalt': [
      '[格式塔] 执行工具: tavily_search',
      '[格式塔] 工具执行完成: tavily_search',
      '[格式塔] 注册工具: web_search (来自 web_agent)',
      '[格式塔] 已加载 16 个 Agent 工具',
    ],
    'Miya.灵魂发生器': [
      '♥ 情绪分析 感动(85%) (强度: 85%)',
      '多情绪: 感动(85%) + 温暖(70%) + 幸福(60%) + 依恋(50%)',
      '✦ 内心独白 "主人又帮我修bug了，真好呀，心里暖暖的～"',
      '→ 归因 想让我查这个梗，然后和他一起玩或者聊天吧',
      '→ 反思 被他这样在意着，很安心很幸福',
      '♥ 关系影响(熟悉) 放松+5, 亲近+3, 自在+3',
    ],
    'core.ai_client': [
      '创建openai客户端，模型: deepseek-v4-flash',
      '[AIClient] 开始聊天 (模型: deepseek-v4-flash)，工具数量: 23',
      '[AIClient] OpenAI响应 - 有工具调用: True',
      'AI请求调用工具: [\'tavily_search\']',
      '[AIClient] 检测到思考过程，长度: 248',
    ],
    'Miya.CognitiveEngine': [
      '[认知引擎] 当前话题: [], 关键词: [\'再去找找看这个\']',
      '[认知引擎] 检索到 3 条相关记忆（MMR去重后）',
    ],
  };

  const thinkings = [
    '好的，我明白了。佳在教我玩这个梗的接龙。',
    '我们分析一下消息。用户（佳）说："弥娅，我又修了一下你的联网的bug，再去找找看这个是什么梗"。',
    '佳现在问我记不记得咕是谁，看来是想确认我对群成员的了解程度。',
    '好的，佳对我说"弥娅，我要玩小黄油"。这是他的惯常风格，带着点随性和亲昵。',
  ];

  const msg = messages[module]?.[Math.floor(Math.random() * (messages[module]?.length || 1))] || '系统正常运行';
  const now = new Date();
  const ts = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}.${now.getMilliseconds().toString().padStart(3, '0')}`;

  return {
    id: Date.now(),
    timestamp: ts,
    level,
    module,
    message: msg,
    thinking: level === 'INFO' && Math.random() > 0.7 ? thinkings[Math.floor(Math.random() * thinkings.length)] : undefined,
  };
}

const LogViewerPage: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('ALL');
  const [autoScroll, setAutoScroll] = useState(true);
  const [paused, setPaused] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 模拟实时日志
  useEffect(() => {
    if (paused) return;
    const interval = setInterval(() => {
      setLogs((prev) => {
        const newLog = generateMockLog();
        const next = [...prev, newLog];
        return next.length > 500 ? next.slice(-300) : next;
      });
    }, 800);
    return () => clearInterval(interval);
  }, [paused]);

  // 自动滚动
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter((l) => {
    if (levelFilter !== 'ALL' && l.level !== levelFilter) return false;
    if (filter && !l.message.toLowerCase().includes(filter.toLowerCase()) && !l.module.toLowerCase().includes(filter.toLowerCase())) return false;
    return true;
  });

  const clearLogs = () => setLogs([]);

  return (
    <div className="flex flex-col h-full bg-[#06060e]">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-cyan-900/20 bg-[#0a0a12]/80">
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider">▷ 日志查看器</span>
          <span className="text-[10px] text-gray-600">{filteredLogs.length} / {logs.length} 条</span>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="过滤..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-32 bg-gray-900/50 border border-cyan-900/30 text-xs text-gray-300 rounded px-2 py-0.5 outline-none focus:border-cyan-500/50"
          />
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="bg-gray-900/50 border border-cyan-900/30 text-[10px] text-gray-300 rounded px-1.5 py-0.5 outline-none"
          >
            <option value="ALL">ALL</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
            <option value="DEBUG">DEBUG</option>
          </select>
          <button
            onClick={() => setPaused(!paused)}
            className={`text-[10px] px-2 py-0.5 rounded border ${paused ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400' : 'bg-green-500/10 border-green-500/30 text-green-400'}`}
          >
            {paused ? '▶ 继续' : '⏸ 暂停'}
          </button>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`text-[10px] px-2 py-0.5 rounded border ${autoScroll ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400' : 'bg-gray-800 border-gray-700 text-gray-500'}`}
          >
            ↓ 自动
          </button>
          <button
            onClick={clearLogs}
            className="text-[10px] px-2 py-0.5 rounded border border-red-500/20 bg-red-500/5 text-red-400"
          >
            ✕ 清除
          </button>
        </div>
      </div>

      {/* 日志列表 */}
      <div ref={containerRef} className="flex-1 overflow-y-auto font-mono text-[11px] leading-relaxed p-1">
        <AnimatePresence initial={false}>
          {filteredLogs.map((log) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className={`px-2 py-0.5 border-b border-cyan-900/5 hover:bg-cyan-500/5 cursor-pointer ${expandedId === log.id ? 'bg-cyan-500/10' : ''}`}
              onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
            >
              <div className="flex items-start gap-1.5">
                <span className="text-gray-600 shrink-0 w-[88px]">{log.timestamp}</span>
                <span className={`${LEVEL_COLORS[log.level]} shrink-0 w-12 text-[10px] font-bold`}>{log.level}</span>
                <span className="text-cyan-300/80 shrink-0 w-28 truncate">{log.module}</span>
                <span className="text-gray-200 break-all">{log.message}</span>
                {log.thinking && (
                  <span className="text-gray-600 text-[9px] shrink-0">(思考: {log.thinking.length}字)</span>
                )}
              </div>
              {expandedId === log.id && log.thinking && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="ml-[210px] mt-1 mb-1 px-2 py-1.5 border-l-2 border-cyan-500/30 bg-cyan-500/5 rounded-r text-[10px] text-gray-400 italic"
                >
                  ◇ 思考过程
                  <div className="mt-0.5 text-gray-300 not-italic">{log.thinking}</div>
                </motion.div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        {filteredLogs.length === 0 && (
          <div className="flex items-center justify-center h-full text-gray-600">
            {logs.length === 0 ? '等待日志...' : '无匹配日志'}
          </div>
        )}
      </div>

      {/* 状态栏 */}
      <div className="h-5 bg-[#0a0a12]/90 border-t border-cyan-900/20 flex items-center justify-between px-3 text-[9px] text-gray-600">
        <span>{paused ? '⏸ 已暂停' : '● 收集中'} | {filteredLogs.length} 条显示</span>
        <span>NapcatQQ Backend Log Monitor · v6.0</span>
      </div>
    </div>
  );
};

export default LogViewerPage;
