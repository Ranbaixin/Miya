// ============================================================
// 弥娅运维中心 · 运行终端 — TerminalPage
//   对接 /api/terminal/chat 的实时 AI 终端
// ============================================================
import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { terminalChat } from '../services/miyaApi';
import { cn } from '../utils';

interface TerminalLine {
  id: number;
  type: 'input' | 'output' | 'error' | 'system';
  content: string;
  timestamp: string;
}

const TerminalPage: React.FC = () => {
  const [lines, setLines] = useState<TerminalLine[]>([
    { id: 0, type: 'system', content: '◆ MIYA 弥娅 · 运维终端 v7.0', timestamp: new Date().toLocaleTimeString() },
    { id: 1, type: 'system', content: '  输入命令或自然语言与弥娅核心交互', timestamp: '' },
    { id: 2, type: 'system', content: '  示例: "查看系统状态" · "列出所有平台" · "查询记忆统计"', timestamp: '' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const nextId = useRef(2);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [lines]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const addLine = useCallback((type: TerminalLine['type'], content: string) => {
    const id = ++nextId.current;
    setLines(prev => {
      const next = [...prev, { id, type, content, timestamp: new Date().toLocaleTimeString() }];
      return next.length > 500 ? next.slice(-300) : next;
    });
  }, []);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    addLine('input', `> ${text}`);
    setInput('');
    setLoading(true);

    if (!history.includes(text)) {
      setHistory(prev => [...prev, text]);
    }
    setHistoryIdx(-1);

    try {
      const res = await terminalChat(text, sessionId || undefined);
      if (res) {
        if (!sessionId && res.session_id) setSessionId(res.session_id);
        if (res.response) {
          const responses = res.response.split('\n');
          for (const r of responses) {
            if (r.trim()) addLine('output', r);
          }
        }
        if (res.status === 'error') addLine('error', res.error || '请求失败');
      } else {
        addLine('error', '终端无响应 — 弥娅后端可能未启动');
      }
    } catch {
      addLine('error', '通信异常');
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [input, loading, sessionId, addLine, history]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (history.length > 0) {
        const idx = historyIdx === -1 ? history.length - 1 : Math.max(0, historyIdx - 1);
        setHistoryIdx(idx);
        setInput(history[idx]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIdx >= 0) {
        const idx = historyIdx + 1;
        if (idx >= history.length) {
          setHistoryIdx(-1);
          setInput('');
        } else {
          setHistoryIdx(idx);
          setInput(history[idx]);
        }
      }
    }
  };

  const typeColor = (type: TerminalLine['type']) => {
    switch (type) {
      case 'input': return 'text-aether-bright';
      case 'output': return 'text-text-primary';
      case 'error': return 'text-status-error';
      case 'system': return 'text-text-dim';
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* ---- 标题栏 ---- */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border-glass bg-void-panel/80 shrink-0">
        <span className="text-[10px] text-text-dim">◈ 运行终端</span>
        <div className="flex items-center gap-3 text-[9px] text-text-dim">
          <span>{sessionId ? `会话: ${sessionId.slice(0, 8)}...` : '新会话'}</span>
          <button
            className="text-aether hover:text-aether-bright"
            onClick={() => {
              setLines([
                { id: 0, type: 'system', content: '◆ 会话已重置', timestamp: new Date().toLocaleTimeString() },
              ]);
              nextId.current = 0;
              setSessionId('');
            }}
          >
            重置
          </button>
          <button
            className="text-text-dim hover:text-text-primary"
            onClick={() => setLines([])}
          >
            清除
          </button>
        </div>
      </div>

      {/* ---- 终端输出区 ---- */}
      <div ref={containerRef} className="flex-1 overflow-y-auto p-3 font-mono text-[11px] leading-relaxed" onClick={() => inputRef.current?.focus()}>
        <AnimatePresence initial={false}>
          {lines.map((line) => (
            <motion.div
              key={line.id}
              className="flex"
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.1 }}
            >
              <span className="text-text-dim shrink-0 w-16 text-[9px] select-none mr-1 mt-px">{line.timestamp}</span>
              <span className={cn(
                'break-all',
                typeColor(line.type),
                line.type === 'system' && 'italic'
              )}>
                {line.content}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>

        {loading && (
          <motion.div className="flex items-center gap-2 text-aether text-[11px] mt-1" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <span className="animate-pulse">◆</span>
            <span className="animate-pulse">处理中...</span>
          </motion.div>
        )}

        {lines.length <= 3 && !loading && (
          <div className="text-text-dim text-[10px] mt-4 text-center opacity-50">输入消息并按 Enter 发送...</div>
        )}
      </div>

      {/* ---- 输入区 ---- */}
      <div className="border-t border-border-glass p-2 bg-void-panel/90 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-aether text-sm font-mono shrink-0">{'>'}</span>
          <input
            ref={inputRef}
            className="flex-1 bg-transparent text-text-primary text-[12px] font-mono outline-none placeholder:text-text-dim"
            placeholder={loading ? '等待响应...' : '输入命令或自然语言...'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            spellCheck={false}
            autoComplete="off"
          />
          <button
            className={cn(
              'px-3 py-1 text-[10px] rounded-lg font-mono transition-colors shrink-0',
              loading || !input.trim()
                ? 'bg-void-deep/60 text-text-dim cursor-not-allowed'
                : 'bg-aether/10 text-aether border border-aether/20 hover:bg-aether/20'
            )}
            onClick={send}
            disabled={loading || !input.trim()}
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
};

export default TerminalPage;
