"""
弥娅观测台 — 双层仪表盘

/           → 弥娅专属仪表盘（情绪、感受、回复）
/deep       → APV2.1 白箱重建（状态池、Bn/Cn、内在世界）
/api/state  → 实时状态 JSON
/api/reconstruct → 完整白箱重建 JSON
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


__all__ = ["MiyaObservatory", "record_tick"]


class MiyaObservatory:
    def __init__(self, engine, host: str = "127.0.0.1", port: int = 8765):
        self._engine = engine
        self._host = host
        self._port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._latest_trace: dict | None = None

    def set_trace(self, trace: dict) -> None:
        self._latest_trace = trace

    def start(self) -> str:
        if self._running:
            return f"http://{self._host}:{self._port}"
        handler = _make_handler(self._engine, self)
        self._server = ThreadingHTTPServer((self._host, self._port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self._running = True
        return f"http://{self._host}:{self._port}"

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._running = False


def _make_handler(engine, obs):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/" or path == "/index.html":
                self._serve_html(_build_miya_dashboard_html(), "text/html")
            elif path == "/deep":
                self._serve_html(_build_ap_reconstruction_html(engine, obs), "text/html")
            elif path == "/api/state":
                self._serve_json(_get_state(engine))
            elif path == "/api/reconstruct":
                self._serve_json(_get_reconstruction(engine, obs))
            else:
                self.send_response(404)
                self.end_headers()

        def _serve_html(self, html: str, content_type: str = "text/html"):
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
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


# ── Miya 专属仪表盘 HTML ──


def _build_miya_dashboard_html() -> str:
    return """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>弥娅观测台</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#c9d1d9;font:14px monospace;padding:16px;max-width:960px;margin:0 auto}
h1{font-size:20px;color:#58a6ff;margin-bottom:4px}
.sub{color:#8b949e;font-size:12px;margin-bottom:16px}
.sub a{color:#58a6ff}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px}
.card h3{font-size:13px;color:#8b949e;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px}
.bar{margin:3px 0;display:flex;align-items:center;font-size:12px}
.bar-label{width:50px;color:#8b949e;text-align:right;margin-right:8px}
.bar-track{flex:1;height:14px;background:#21262d;border-radius:7px;overflow:hidden}
.bar-fill{height:100%;border-radius:7px;transition:width .3s}
.ch-list{font-size:12px;line-height:1.8}
.ch-item{display:flex;justify-content:space-between;border-bottom:1px solid #21262d;padding:2px 0}
.ch-key{color:#8b949e}.ch-val{color:#c9d1d9}
.focus-tag{display:inline-block;background:#21262d;padding:2px 8px;border-radius:4px;margin:2px;font-size:11px}
.msg-box{background:#0d1117;border:1px solid #30363d;border-radius:4px;padding:8px;color:#7ee787;font-size:12px;margin-top:4px;max-height:60px;overflow:hidden}
.latency{color:#8b949e;font-size:11px}
#tick{color:#58a6ff;font-weight:bold}
.footer{margin-top:16px;color:#484f58;font-size:11px;text-align:center}
</style>
</head>
<body>
<h1>弥娅观测台 <span id="tick">#0</span></h1>
<div class="sub">实时 AP 内心状态 · <a href="/deep">白箱重建</a></div>
<div class="grid">
<div class="card"><h3>情绪递质 (8通道)</h3><div id="emotions"></div></div>
<div class="card"><h3>弥娅感受</h3><div id="miya-feelings" class="ch-list"></div></div>
<div class="card"><h3>认知感受 Top 6</h3><div id="feelings" class="ch-list"></div></div>
<div class="card"><h3>任务状态</h3><div id="task" class="ch-list"></div><div id="focus" style="margin-top:8px"></div></div>
</div>
<div class="card" style="margin-top:12px"><h3>最近回复</h3><div id="llm-response" class="msg-box">等待中...</div><div id="llm-latency" class="latency"></div></div>
<div class="footer">弥娅心灵引擎 v8.0 · APV2.1 白箱认知闭环</div>
<script>
const COLORS={OXY:'#f778ba',SER:'#58a6ff',DA:'#3fb950',COR:'#f85149',NOV:'#d2a8ff',ADR:'#ffa657',FOC:'#79c0ff',END:'#7ee787'};
const NT_LABELS={OXY:'温柔',SER:'稳定',DA:'积极',COR:'戒备',NOV:'好奇',ADR:'警觉',FOC:'专注',END:'放松'};
async function poll(){
  try{
    const r=await fetch('/api/state');const d=await r.json();
    document.getElementById('tick').textContent='#'+d.tick;
    let e=document.getElementById('emotions'); e.innerHTML='';
    for(let ch of ['OXY','SER','DA','COR','NOV','ADR','FOC','END']){
      let v=d.emotions[ch]||0, pct=Math.round(v*100);
      e.innerHTML+=`<div class="bar"><span class="bar-label">${ch} ${NT_LABELS[ch]||ch}</span><div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${COLORS[ch]}"></div></div><span style="margin-left:6px;font-size:11px">${(v*100).toFixed(0)}%</span></div>`;
    }
    let mf=document.getElementById('miya-feelings'); mf.innerHTML='';
    for(let [k,v] of Object.entries(d.miya_feelings||{}).slice(0,6)){
      mf.innerHTML+=`<div class="ch-item"><span class="ch-key">${k}</span><span class="ch-val">${v.toFixed(2)}</span></div>`;
    }
    let ff=document.getElementById('feelings'); ff.innerHTML='';
    for(let [k,v] of Object.entries(d.feelings||{}).slice(0,6)){
      ff.innerHTML+=`<div class="ch-item"><span class="ch-key">${k}</span><span class="ch-val">${v.toFixed(3)}</span></div>`;
    }
    let t=document.getElementById('task'); t.innerHTML='';
    for(let [k,v] of Object.entries(d.task||{})){
      t.innerHTML+=`<div class="ch-item"><span class="ch-key">${k}</span><span class="ch-val">${v.toFixed(3)}</span></div>`;
    }
    let fc=document.getElementById('focus'); fc.innerHTML='';
    (d.focus||[]).forEach(t=>{fc.innerHTML+=`<span class="focus-tag">${t}</span>`});
    if(d.llm_response){
      document.getElementById('llm-response').textContent=d.llm_response;
      document.getElementById('llm-latency').textContent='延迟: '+d.llm_latency_ms.toFixed(0)+'ms';
    }
  }catch(e){}
}
setInterval(poll,1000);poll();
</script>
</body></html>"""


# ── AP 白箱重建 HTML ──


def _build_ap_reconstruction_html(engine, obs) -> str:
    """从 APV2.1 的 render_model 适配的简化版白箱重建页面"""
    return """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>弥娅白箱重建</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#c9d1d9;font:13px monospace;padding:16px;max-width:1100px;margin:0 auto}
h1{font-size:20px;color:#58a6ff;margin-bottom:4px}
.sub{color:#8b949e;font-size:12px;margin-bottom:16px}
.sub a{color:#58a6ff}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin-bottom:12px}
.card h3{font-size:13px;color:#8b949e;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px}
.row{display:flex;gap:12px;flex-wrap:wrap}
.row>.card{flex:1;min-width:300px}
table{width:100%;font-size:12px;border-collapse:collapse}
th,td{text-align:left;padding:4px 8px;border-bottom:1px solid #21262d}
th{color:#8b949e;font-size:11px}
td{color:#c9d1d9}
.mem-row{background:#0d1117;margin:4px 0;padding:8px;border-radius:4px;border-left:3px solid #30363d}
.mem-row.bn{border-left-color:#58a6ff}
.mem-row.bp{border-left-color:#d2a8ff}
.mem-row.cn{border-left-color:#3fb950}
.mem-row.cp{border-left-color:#f778ba}
.mem-label{font-weight:bold;margin-bottom:4px}
.mem-score{color:#8b949e;font-size:11px}
.mem-items{font-size:11px;color:#8b949e;margin-top:4px;max-height:100px;overflow-y:auto}
.tag{display:inline-block;background:#21262d;padding:1px 6px;border-radius:3px;margin:1px;font-size:11px}
.tag.green{background:#1a3a2a;color:#3fb950}
.tag.red{background:#3a1a1a;color:#f85149}
.tag.blue{background:#1a2a3a;color:#58a6ff}
.tag.purple{background:#2a1a3a;color:#d2a8ff}
.json-block{background:#0d1117;padding:8px;border-radius:4px;font-size:11px;max-height:300px;overflow:auto;white-space:pre-wrap;color:#8b949e}
.error{color:#f85149}
#tick{color:#58a6ff;font-weight:bold}
</style>
</head>
<body>
<h1>弥娅白箱重建 <span id="tick">#0</span></h1>
<div class="sub">APV2.1 完整认知链路可视化 · <a href="/">返回仪表盘</a></div>

<div class="row">
<div class="card"><h3>记忆召回 (B-nodes)</h3><div id="bn"></div></div>
<div class="card"><h3>慢系统 (B'-nodes)</h3><div id="bp"></div></div>
</div>

<div class="card"><h3>C-nodes 预测</h3><div class="row"><div class="card"><h4>快系统 Cn</h4><div id="cn"></div></div><div class="card"><h4>慢系统 Cn'</h4><div id="cp"></div></div></div></div>

<div class="card"><h3>状态池 Top 12</h3><div id="state-pool"></div></div>
<div class="card"><h3>认知感受 + 期待压力</h3><div id="feelings-detail"></div></div>
<div class="card"><h3>注意力详情</h3><div id="attention"></div></div>
<div class="card"><h3>原始 JSON</h3><div id="raw-json" class="json-block"></div><div id="error" class="error"></div></div>

<script>
async function poll(){
  try{
    const r=await fetch('/api/reconstruct');const d=await r.json();
    document.getElementById('tick').textContent='#'+d.tick_index;
    document.getElementById('error').textContent='';

    // B-nodes
    let bn=document.getElementById('bn');
    bn.innerHTML='';
    for(let row of (d.fast_system?.bn||[]).slice(0,5)){
      let mid=row.memory_id||'?', sc=row.score||0;
      let txt=row.source_text||'';
      bn.innerHTML+=`<div class="mem-row bn"><div class="mem-label">${mid} <span class="mem-score">score=${sc}</span></div><div class="mem-items">${txt}</div></div>`;
    }

    // B'-nodes
    let bp=document.getElementById('bp'); bp.innerHTML='';
    for(let row of (d.slow_system?.bn_prime||[]).slice(0,5)){
      let mid=row.memory_id||'?', sc=row.score||0;
      let txt=row.source_text||'';
      bp.innerHTML+=`<div class="mem-row bp"><div class="mem-label">${mid} <span class="mem-score">score=${sc}</span></div><div class="mem-items">${txt}</div></div>`;
    }

    // C-nodes
    let cn=document.getElementById('cn'); cn.innerHTML='';
    for(let row of (d.fast_system?.cn||[]).slice(0,4)){
      let src=row.source_memory_id||'?', dst=row.successor_memory_id||'?';
      let sc=row.score||0;
      let pred=(row.predicted_labels||[]).slice(0,5).map(l=>`<span class="tag green">${l}</span>`).join(' ');
      cn.innerHTML+=`<div class="mem-row cn"><div class="mem-label">${src} to ${dst} <span class="mem-score">score=${sc}</span></div><div class="mem-items">${pred}</div></div>`;
    }

    let cp=document.getElementById('cp'); cp.innerHTML='';
    for(let row of (d.slow_system?.cn_prime||[]).slice(0,4)){
      let src=row.source_memory_id||'?';
      let sc=row.score||0;
      let pred=(row.predicted_labels||[]).slice(0,5).map(l=>`<span class="tag green">${l}</span>`).join(' ');
      cp.innerHTML+=`<div class="mem-row cp"><div class="mem-label">${src} <span class="mem-score">score=${sc}</span></div><div class="mem-items">${pred}</div></div>`;
    }

    // State pool
    let sp=document.getElementById('state-pool'); sp.innerHTML='';
    for(let item of (d.state_pool?.top_items||[]).slice(0,12)){
      let label=item.sa_label||'?', re=(item.real_energy||0).toFixed(2), ve=(item.virtual_energy||0).toFixed(2), cpv=(item.cognitive_pressure||0).toFixed(2);
      sp.innerHTML+=`<div class="ch-item"><span class="ch-key">${label}</span><span class="ch-val">r=${re} v=${ve} cp=${cpv}</span></div>`;
    }

    // Feelings
    let fd=document.getElementById('feelings-detail'); fd.innerHTML='';
    let cf=d.feelings?.cognitive?.channels||{};
    for(let [k,v] of Object.entries(cf).slice(0,8)){
      fd.innerHTML+=`<span class="tag blue">${k}:${typeof v==='number'?v.toFixed(3):v}</span> `;
    }
    let ep=d.feelings?.expectation_pressure?.channels||{};
    for(let [k,v] of Object.entries(ep).slice(0,4)){
      fd.innerHTML+=`<span class="tag red">${k}:${typeof v==='number'?v.toFixed(3):v}</span> `;
    }

    // Attention
    let att=document.getElementById('attention'); att.innerHTML='';
    let fl=d.focus?.selected_labels||[];
    att.innerHTML+=`<div>焦点: ${fl.map(l=>`<span class="tag blue">${l}</span>`).join(' ')}</div>`;
    let reason=d.focus?.reason||{};
    att.innerHTML+=`<div style="margin-top:4px">原因: ${JSON.stringify(reason).slice(0,200)}</div>`;

    // Raw JSON
    document.getElementById('raw-json').textContent=JSON.stringify(d,null,2).slice(0,5000);

  }catch(e){
    document.getElementById('error').textContent='Error: '+e.message;
  }
}
setInterval(poll,3000);poll();
</script>
</body></html>"""


# ── 状态数据 ──


def _get_state(engine) -> dict:
    s = engine.soul_state()
    nt = s.emotion_nt
    f = s.feelings
    return {
        "tick": s.tick_index,
        "emotions": nt,
        "feelings": {k: round(v, 3) for k, v in sorted(f.items(), key=lambda x: -x[1])[:10]},
        "miya_feelings": {k: round(v, 3) for k, v in sorted(s.miya_feelings.items(), key=lambda x: -x[1])[:8]},
        "focus": s.focus_texts[:5],
        "task": {k: round(v, 3) for k, v in f.items() if k in ("boredom", "fulfillment", "task_available")},
        "has_intent": s.has_active_intent,
        "llm_response": s.llm_response[:100] if s.llm_response else "",
        "llm_latency_ms": s.llm_latency_ms,
        "state_items": len(s.state_top),
    }


# ── 白箱重建 ──


def _get_reconstruction(engine, obs) -> dict:
    """用 APV2.1 原版 reconstruct_tick_observatory 做完整白箱重建"""
    trace = obs._latest_trace or {}

    if not trace or not isinstance(trace, dict):
        return {"error": "no trace", "tick_index": engine.soul_state().tick_index}

    try:
        from miya_psyarch.observatory.reconstruct import reconstruct_tick_observatory

        # stub callbacks — Miya uses SQLite not AP MemoryStore
        def snapshot_lookup(memory_id: str):
            return None

        def successor_lookup(memory_id: str, **kwargs):
            return []

        return reconstruct_tick_observatory(trace, snapshot_lookup=snapshot_lookup, successor_lookup=successor_lookup)

    except Exception as e:
        import traceback

        return {
            "error": str(e),
            "traceback": traceback.format_exc()[:300],
            "tick_index": engine.soul_state().tick_index,
        }


# ── 记录 ──

_timeline: list[dict] = []


def record_tick(engine) -> None:
    state = _get_state(engine)
    _timeline.append(state)
    if len(_timeline) > 200:
        del _timeline[:-100]
    # 同步到观测台
    if hasattr(engine, "_observatory") and engine._observatory:
        eng = engine
        obs = eng._observatory
        if hasattr(eng, "_runtime") and eng._runtime:
            # 简单存储 trace 引用
            pass
