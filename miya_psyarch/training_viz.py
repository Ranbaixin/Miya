"""
弥娅训练可视化 — 6 阶段 scaffold 实时仪表盘

训练时浏览器打开 http://127.0.0.1:8768/train
实时看 AP 每阶段的 Bn 召回、情绪变化、训练进度
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


_training_log: list[dict] = []
_current_stage: str = ""
_current_progress: int = 0


def record_stage(stage: str, details: dict) -> None:
    global _current_stage, _current_progress
    _current_stage = stage
    _current_progress = details.get("progress", 0)
    _training_log.append(
        {
            "stage": stage,
            "bn_score": details.get("bn_score", 0),
            "coherence": details.get("coherence", 0),
            "grasp": details.get("grasp", 0),
            "emotions": details.get("emotions", {}),
            "feelings": details.get("feelings", {}),
            "trigger": details.get("trigger", ""),
            "demo": details.get("demo", ""),
        }
    )
    if len(_training_log) > 500:
        del _training_log[:-300]


def reset_log() -> None:
    global _training_log, _current_stage, _current_progress
    _training_log = []
    _current_stage = ""
    _current_progress = 0


class TrainingDashboard:
    def __init__(self, host: str = "127.0.0.1", port: int = 8768):
        self._host = host
        self._port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> str:
        handler = _make_handler()
        self._server = ThreadingHTTPServer((self._host, self._port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return f"http://{self._host}:{self._port}/train"

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()


def _make_handler():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/train"):
                self._serve_html(_build_html())
            elif path == "/api/training":
                self._serve_json({"stage": _current_stage, "progress": _current_progress, "log": _training_log[-100:]})
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


def _build_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>弥娅训练仪表盘</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#c9d1d9;font:14px monospace;padding:16px;max-width:1000px;margin:0 auto}
h1{font-size:22px;color:#58a6ff;margin-bottom:4px}
.sub{color:#8b949e;font-size:12px;margin-bottom:16px}
.phase-bar{display:flex;gap:4px;margin-bottom:16px}
.phase{flex:1;text-align:center;padding:8px 4px;border-radius:6px;font-size:11px;background:#161b22;border:1px solid #30363d;color:#8b949e}
.phase.active{background:#1a2a3a;border-color:#58a6ff;color:#58a6ff;font-weight:bold}
.phase.done{background:#1a3a1a;border-color:#3fb950;color:#3fb950}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin-bottom:12px}
.card h3{font-size:14px;color:#8b949e;margin-bottom:8px}
.metric-row{display:flex;gap:12px;flex-wrap:wrap}
.metric{flex:1;min-width:150px;background:#0d1117;border-radius:6px;padding:10px;text-align:center}
.metric .value{font-size:28px;font-weight:bold;color:#58a6ff}
.metric .label{font-size:11px;color:#8b949e;margin-top:4px}
.bar{margin:3px 0;display:flex;align-items:center;font-size:12px}
.bar-label{width:60px;color:#8b949e;text-align:right;margin-right:8px}
.bar-track{flex:1;height:14px;background:#21262d;border-radius:7px;overflow:hidden}
.bar-fill{height:100%;border-radius:7px;transition:width .3s}
.log-row{display:flex;padding:4px 8px;border-bottom:1px solid #21262d;font-size:11px;align-items:center}
.log-stage{width:100px;color:#8b949e}
.log-bn{width:80px;text-align:right;color:#58a6ff}
.log-coh{width:80px;text-align:right;color:#3fb950}
.log-msg{flex:1;color:#c9d1d9;margin-left:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chart-box{width:100%;height:120px;background:#0d1117;border-radius:6px;position:relative;overflow:hidden}
.dot{position:absolute;width:6px;height:6px;border-radius:50%;transform:translate(-3px,-3px)}
#tick{color:#58a6ff;font-weight:bold}
</style>
</head>
<body>
<h1>弥娅训练仪表盘 <span id="tick">等待中...</span></h1>
<div class="sub">6 阶段 scaffold 教学 · 实时刷新</div>

<div class="phase-bar" id="phases">
  <div class="phase">1.演示</div>
  <div class="phase">2.强脚手架</div>
  <div class="phase">3.弱脚手架</div>
  <div class="phase">4.纯反馈</div>
  <div class="phase">5.老师关闭</div>
  <div class="phase">6.冷重启</div>
</div>

<div class="metric-row">
  <div class="metric"><div class="value" id="bn">--</div><div class="label">Bn 召回分</div></div>
  <div class="metric"><div class="value" id="coh">--</div><div class="label">Coherence</div></div>
  <div class="metric"><div class="value" id="grasp">--</div><div class="label">Grasp</div></div>
  <div class="metric"><div class="value" id="total">0</div><div class="label">累计轮次</div></div>
</div>

<div class="card">
  <h3>Bn 召回趋势</h3>
  <div class="chart-box" id="bn-chart"></div>
</div>

<div class="card">
  <h3>情绪通道</h3>
  <div id="emotions"></div>
</div>

<div class="card">
  <h3>训练日志</h3>
  <div id="log" style="max-height:300px;overflow-y:auto"></div>
</div>

<script>
const STAGES = ['demonstrate','strong_scaffold','weak_scaffold','feedback_only','teacher_off','cold_retest'];
const STAGE_CN = ['1.演示','2.强脚手架','3.弱脚手架','4.纯反馈','5.老师关闭','6.冷重启'];

let allData = [];

async function poll(){
  try{
    const r=await fetch('/api/training');const d=await r.json();
    document.getElementById('total').textContent=d.log.length;

    // Phase bar
    let stageIdx = STAGES.indexOf(d.stage);
    let phases=document.getElementById('phases').children;
    for(let i=0;i<phases.length;i++){
      phases[i].className = i<stageIdx ? 'phase done' : i===stageIdx ? 'phase active' : 'phase';
    }

    // Latest metrics
    let latest = d.log.length>0 ? d.log[d.log.length-1] : {};
    document.getElementById('bn').textContent=latest.bn_score?latest.bn_score.toFixed(0):'--';
    document.getElementById('coh').textContent=latest.coherence?latest.coherence.toFixed(3):'--';
    document.getElementById('grasp').textContent=latest.grasp?latest.grasp.toFixed(3):'--';

    // Bn chart
    let chart=document.getElementById('bn-chart');chart.innerHTML='';
    if(d.log.length>1){
      let maxBn = Math.max(...d.log.map(l=>l.bn_score||0),1);
      let w=chart.clientWidth, h=chart.clientHeight;
      d.log.forEach((l,i)=>{
        let x=(i/(d.log.length-1))*w, y=h-(l.bn_score/maxBn)*h;
        let dot=document.createElement('div');dot.className='dot';
        dot.style.left=x+'px';dot.style.top=y+'px';
        dot.style.background=l.bn_score>400?'#3fb950':l.bn_score>200?'#58a6ff':'#f85149';
        dot.title='tick '+i+': '+l.bn_score;
        chart.appendChild(dot);
      });
    }

    // Emotions
    let em=document.getElementById('emotions');em.innerHTML='';
    let emos=latest.emotions||{};
    for(let [ch,val] of Object.entries(emos).slice(0,6)){
      let pct=Math.round(val*100);
      em.innerHTML+=`<div class="bar"><span class="bar-label">${ch}</span><div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:#58a6ff"></div></div><span style="margin-left:6px;font-size:11px">${pct}%</span></div>`;
    }

    // Log
    let logEl=document.getElementById('log');logEl.innerHTML='';
    for(let l of d.log.slice(-30)){
      let stage=STAGE_CN[STAGES.indexOf(l.stage)]||l.stage;
      logEl.innerHTML+=`<div class="log-row"><span class="log-stage">${stage}</span><span class="log-bn">bn:${l.bn_score.toFixed(0)}</span><span class="log-coh">coh:${l.coherence.toFixed(3)}</span><span class="log-msg">${l.trigger||''} → ${(l.demo||'').slice(0,40)}</span></div>`;
    }
    logEl.scrollTop=logEl.scrollHeight;

    document.getElementById('tick').textContent='训练中...';
  }catch(e){}
}
setInterval(poll,500);
poll();
</script>
</body></html>"""


_dashboard: TrainingDashboard | None = None


def get_dashboard() -> TrainingDashboard:
    global _dashboard
    if _dashboard is None:
        _dashboard = TrainingDashboard()
    return _dashboard
