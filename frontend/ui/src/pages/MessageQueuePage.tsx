// ============================================================
// 弥娅 消息队列 · 樱梦琉璃
// ============================================================
import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

interface QueueEvent { id: number; timestamp: string; type: 'enqueue'|'dispatch'|'complete'; note: string; duration_ms?: number; }

const colors: Record<string,string> = { enqueue:'text-[#fcd4b6] border-[rgba(252,212,182,0.2)]', dispatch:'text-[#93c5fd] border-[rgba(147,197,253,0.2)]', complete:'text-[#a7f3d0] border-[rgba(167,243,208,0.2)]' };
const icons: Record<string,string> = { enqueue:'↓入队', dispatch:'→发车', complete:'✓完成' };

const MessageQueuePage: React.FC = () => {
  const [events, setEvents] = useState<QueueEvent[]>([]);
  const [queueSize, setQueueSize] = useState(0);
  const [processing, setProcessing] = useState(false);
  const counterRef = useRef(0);

  useEffect(() => {
    const mockGroups = ['1092980378(索多玛)', '579433934(二元3队)'];
    const mockUsers = ['1523878699(佳)', '2911746585(咕)'];
    const addEvent = () => {
      const cid = ++counterRef.current;
      const baseId = cid * 100;  // unique block to prevent key overlap
      const now = new Date();
      const mkTs = () => `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}.${now.getMilliseconds().toString().padStart(3,'0')}`;
      const group = mockGroups[Math.floor(Math.random()*mockGroups.length)];
      const user = mockUsers[Math.floor(Math.random()*mockUsers.length)];
      const dur = Math.floor(Math.random()*28000)+2000;

      setProcessing(true);
      setQueueSize(1);
      setEvents(prev=>[...prev.slice(-200), {id:baseId,timestamp:mkTs(),type:'enqueue',note:`群聊: size=1 group=${group} user=${user}`}]);
      setTimeout(()=>setEvents(prev=>[...prev.slice(-200),{id:baseId+1,timestamp:new Date().toTimeString().slice(0,12),type:'dispatch',note:`群聊: group=${group} user=${user}`}]),300);
      setTimeout(()=>{setEvents(prev=>[...prev.slice(-200),{id:baseId+2,timestamp:new Date().toTimeString().slice(0,12),type:'complete',note:`群聊: ${(dur/1000).toFixed(2)}s group=${group} user=${user}`,duration_ms:dur}]);setQueueSize(0);setProcessing(false);},dur);
    };
    addEvent();
    const t = setInterval(addEvent, 5000);
    return ()=>clearInterval(t);
  }, []);

  return (
    <div className="flex flex-col h-full">
      <div className="grid grid-cols-4 gap-2 p-3 pb-1">
        {[['队列模型','default','text-[#c4b5fd]'],['队列大小',String(queueSize),queueSize>0?'text-[#fcd4b6]':'text-[#b8aec8]'],['发车间隔','1.0s','text-[#93c5fd]'],['处理状态',processing?'● PROCESSING':'○ IDLE',processing?'text-[#a7f3d0]':'text-[#b8aec8]']].map(([l,v,c])=>(
          <div key={l} className="frost-panel p-3"><div className="text-[10px] text-[#b8aec8] mb-1">{l}</div><div className={`text-sm font-bold font-mono ${c}`}>{v}</div></div>
        ))}
      </div>
      <div className="flex-1 p-3 pt-2">
        <div className="text-[10px] text-[#b8aec8] uppercase tracking-widest mb-1.5">≣ 事件时间线</div>
        <div className="frost-panel max-h-[calc(100vh-280px)] overflow-y-auto">
          {events.map(e=><motion.div key={e.id} initial={{opacity:0,x:-8}} animate={{opacity:1,x:0}} className={`flex items-center gap-2 px-2 py-1 border-b ${colors[e.type]} text-[10px] font-mono`}><span className="text-[#b8aec8] w-[80px]">{e.timestamp}</span><span className={`${colors[e.type]} w-[50px] font-bold`}>{icons[e.type]}</span><span className="text-[#887c9e]">[{e.type==='enqueue'?'default':''}]</span><span className="text-[#4a4058]">{e.note}</span><span className="text-[#b8aec8] text-[9px] ml-auto">{e.duration_ms?`${e.duration_ms}ms`:''}</span></motion.div>)}
        </div>
      </div>
    </div>
  );
};

export default MessageQueuePage;
