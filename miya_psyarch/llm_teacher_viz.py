"""
LLM 教学专用可视化 — 展示 LLM 教师的决策过程
与 miya_psyarch/training_viz.py 的数据源共享，
但显示 LLM 教学特有的指标：策略分布、教学决策流、AP 学习曲线
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from miya_psyarch.training_viz import _training_log, _current_stage, record_stage
from miya_psyarch.training_viz import _dashboard as _shared_dashboard


_llm_decisions: list[dict] = []
_llm_strategy: dict[str, int] = {}


def record_llm_decision(level: str, reward: float, note: str, bn_score: float, trigger: str) -> None:
    _llm_decisions.append(
        {
            "level": level,
            "reward": round(reward, 2),
            "note": note,
            "bn_score": round(bn_score, 1),
            "trigger": trigger,
        }
    )
    _llm_strategy[level] = _llm_strategy.get(level, 0) + 1
    if len(_llm_decisions) > 200:
        del _llm_decisions[:-100]


def reset_llm() -> None:
    _llm_decisions.clear()
    _llm_strategy.clear()


class LLMTeacherDashboard:
    def __init__(self, host: str = "127.0.0.1", port: int = 8769):
        self._host = host
        self._port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> str:
        handler = _make_llm_handler()
        self._server = ThreadingHTTPServer((self._host, self._port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return f"http://{self._host}:{self._port}/llm_teacher"

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()


def _make_llm_handler():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/llm_teacher"):
                self._serve_html(_build_llm_html())
            elif path == "/api/llm_teaching":
                self._serve_json(
                    {
                        "stage": _current_stage,
                        "decisions": _llm_decisions[-50:],
                        "strategy": _llm_strategy,
                        "training_log": _training_log[-50:],
                    }
                )
            else:
                self.send_response(404)
                self.end_headers()

        def _serve_html(self, html):
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_json(self, data):
            body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _build_llm_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LLM教师仪表盘</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#c9d1d9;font:14px monospace;padding:16px;max-width:1100px;margin:0 auto}
h1{font-size:22px;color:#58a6ff;margin-bottom:4px}
.sub{color:#8b949e;font-size:12px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px}
.card.full{grid-column:1/-1}
.card h3{font-size:14px;color:#8b949e;margin-bottom:8px}
.metric-row{display:flex;gap:8px}
.metric{flex:1;background:#0d1117;border-radius:6px;padding:8px;text-align:center}
.metric .value{font-size:24px;font-weight:bold;color:#58a6ff}
.metric .label{font-size:11px;color:#8b949e;margin-top:2px}
.decision-row{display:flex;padding:3px 8px;border-bottom:1px solid #21262d;font-size:11px;align-items:center}
.dec-num{width:40px;color:#484f58}
.dec-level{width:100px;font-weight:bold}
.dec-bn{width:70px;text-align:right;color:#58a6ff}
.dec-reward{width:60px;color:#3fb950}
.dec-note{flex:1;color:#8b949e;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chart-box{width:100%;height:130px;background:#0d1117;border-radius:6px;position:relative;overflow:hidden}
.strat-bar{margin:3px 0;display:flex;align-items:center;font-size:12px}
.strat-label{width:100px;color:#8b949e}
.strat-track{flex:1;height:20px;background:#21262d;border-radius:4px;overflow:hidden}
.strat-fill{height:100%;border-radius:4px;transition:width .3s;display:flex;align-items:center;padding-left:8px;font-size:11px}
.dot{position:absolute;width:8px;height:8px;border-radius:50%;transform:translate(-4px,-4px);transition:all .3s}
.legend{font-size:11px;color:#8b949e;margin-top:4px}
.legend span{margin-right:12px}
</style>
</head>
<body>
<h1>LLM教师仪表盘</h1>
<div class="sub">DeepSeek V4 观察AP → 自主决策教学策略 → 实时反馈</div>

<div class="metric-row">
  <div class="metric"><div class="value" id="total">0</div><div class="label">教学轮次</div></div>
  <div class="metric"><div class="value" id="bn">--</div><div class="label">当前Bn分</div></div>
  <div class="metric"><div class="value" id="level">--</div><div class="label">当前策略</div></div>
  <div class="metric"><div class="value" id="reward">--</div><div class="label">奖励值</div></div>
</div>

<div class="grid" style="margin-top:12px">
<div class="card">
  <h3>LLM教学策略分布</h3>
  <div id="strategy"></div>
</div>
<div class="card">
  <h3>教学决策实时流</h3>
  <div id="decisions" style="max-height:200px;overflow-y:auto"></div>
</div>
<div class="card full">
  <h3>Bn学习曲线 (LLM动态调整教学强度)</h3>
  <div class="chart-box" id="bn-chart"></div>
  <div class="legend">
    <span style="color:#3fb950">● Bn分</span>
    <span style="color:#58a6ff">蓝色背景=反馈阶段</span>
    <span style="color:#d2a8ff">紫色背景=提示阶段</span>
  </div>
</div>
</div>

<script>
const LEVEL_COLORS = {
  'full_demo':'#f85149','strong_hint':'#d2a8ff','light_hint':'#79c0ff',
  'feedback_only':'#3fb950','teacher_off':'#484f58'
};
const LEVEL_CN = {
  'full_demo':'完整示范','strong_hint':'强提示','light_hint':'轻提示',
  'feedback_only':'纯反馈','teacher_off':'老师关闭'
};

async function poll(){
  try{
    const r=await fetch('/api/llm_teaching');const d=await r.json();
    let decs=d.decisions||[];

    document.getElementById('total').textContent=decs.length;
    if(decs.length){
      let last=decs[decs.length-1];
      document.getElementById('bn').textContent=last.bn_score.toFixed(0);
      document.getElementById('level').textContent=LEVEL_CN[last.level]||last.level;
      document.getElementById('reward').textContent=last.reward.toFixed(2);
    }

    // Strategy bar
    let strat=d.strategy||{};
    let maxS=Math.max(1,...Object.values(strat));
    let sEl=document.getElementById('strategy');sEl.innerHTML='';
    for(let lv of ['full_demo','strong_hint','light_hint','feedback_only','teacher_off']){
      let cnt=strat[lv]||0, pct=Math.round(cnt/maxS*100);
      sEl.innerHTML+=`<div class="strat-bar"><span class="strat-label">${LEVEL_CN[lv]||lv}</span><div class="strat-track"><div class="strat-fill" style="width:${pct}%;background:${LEVEL_COLORS[lv]}">${cnt}次</div></div></div>`;
    }

    // Decisions
    let dEl=document.getElementById('decisions');dEl.innerHTML='';
    for(let d of decs.slice(-20).reverse()){
      dEl.innerHTML+=`<div class="decision-row"><span class="dec-num">#${dec.length-decs.indexOf(d)}</span><span class="dec-level" style="color:${LEVEL_COLORS[d.level]}">${LEVEL_CN[d.level]||d.level}</span><span class="dec-bn">Bn:${d.bn_score}</span><span class="dec-reward">R:${d.reward}</span><span class="dec-note">${d.note||''}</span></div>`;
    }

    // Bn chart
    let chart=document.getElementById('bn-chart');chart.innerHTML='';
    if(decs.length>1){
      let maxBn=Math.max(...decs.map(l=>l.bn_score||0),1);
      let w=chart.clientWidth, h=chart.clientHeight;
      // Background segments (level colors)
      for(let i=0;i<decs.length;i++){
        let x1=(i/decs.length)*w, x2=((i+1)/decs.length)*w;
        let bg=document.createElement('div');
        bg.style.cssText=`position:absolute;left:${x1}px;top:0;width:${x2-x1}px;height:${h}px;background:${LEVEL_COLORS[decs[i].level]}11;opacity:0.3`;
        chart.appendChild(bg);
      }
      // Dots
      decs.forEach((d,i)=>{
        let x=(i/(decs.length-1))*w, y=h-(d.bn_score/maxBn)*h;
        let dot=document.createElement('div');dot.className='dot';
        dot.style.left=x+'px';dot.style.top=y+'px';
        dot.style.background=LEVEL_COLORS[d.level]||'#58a6ff';
        dot.title='#'+(i+1)+' Bn:'+d.bn_score+' '+d.level;
        chart.appendChild(dot);
      });
    }

  }catch(e){}
}
setInterval(poll,1000);poll();
</script>
</body></html>"""


_llm_dashboard: LLMTeacherDashboard | None = None


def get_llm_dashboard() -> LLMTeacherDashboard:
    global _llm_dashboard
    if _llm_dashboard is None:
        _llm_dashboard = LLMTeacherDashboard()
    return _llm_dashboard
