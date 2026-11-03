"""Live dashboard for the running simulation (stdlib only, no extra packages).

How it is connected
  run_simulation.py --dashboard starts a small HTTP server in a background thread. The mission loop calls
  LiveDashboard.publish(mission) about every 16 physics steps; that copies the robot state into a dict.
  The browser page (served from /) polls /state every 200 ms and draws it. Nothing is simulated in the page:
  every number is read from the same objects that are being recorded.

How it is recorded
  Telemetry.log() is called once per physics step (0.002 s = 500 Hz) inside InspectionMission.run().
  The dashboard shows the row count ("rows recorded"), the achieved rate (rows per simulated second), and the CSV path.
  The CSV is written when the mission ends (to_csv).
"""
from __future__ import annotations

import json
import math
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from telemetry import STATE_NAMES

_PAGE = r"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Live AMR dashboard</title><style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#14181f;--mut:#667085;--line:#e3e6eb;--ok:#1a9e55;--bad:#d92d20;--acc:#2563eb;--amb:#d98a00}
@media(prefers-color-scheme:dark){:root{--bg:#0e1116;--card:#171b22;--ink:#e8ebf0;--mut:#98a2b3;--line:#2a303a;--ok:#3ccf82;--bad:#ff6b5e;--acc:#6ea0ff;--amb:#f5b942}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}h1{font-size:18px;margin:0 0 4px}.sub{color:var(--mut);margin-bottom:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.k{color:var(--mut);font-size:12px}.v{font-size:22px;font-weight:600;font-variant-numeric:tabular-nums}
.two{display:grid;grid-template-columns:1.4fr 1fr;gap:10px}@media(max-width:800px){.two{grid-template-columns:1fr}}
canvas{width:100%;display:block}#log{font:12px ui-monospace,monospace;height:170px;overflow:auto;white-space:pre-wrap}
.pill{display:inline-block;padding:2px 10px;border-radius:99px;background:var(--acc);color:#fff;font-weight:600}
.rec{display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--bad);margin-right:6px;animation:b 1s infinite}
@keyframes b{50%{opacity:.25}}.off{background:var(--mut);animation:none}
.legend span{margin-right:12px;font-size:12px;color:var(--mut)}
</style></head><body><main>
<h1>Autonomous Solar PV Inspection AMR: live</h1>
<div class=sub id=sub>connecting...</div>
<div class=grid>
<div class=card><div class=k>FSM state</div><div class=v><span class=pill id=st>-</span></div></div>
<div class=card><div class=k>Sim time</div><div class=v id=t>0.0 s</div></div>
<div class=card><div class=k>Cross-track error</div><div class=v id=cte>-</div></div>
<div class=card><div class=k>Pose error (est vs true)</div><div class=v id=pe>-</div></div>
<div class=card><div class=k>Modules inspected</div><div class=v id=vis>-</div></div>
<div class=card><div class=k>Flagged</div><div class=v id=flg>-</div></div>
<div class=card><div class=k><span class="rec" id=recdot></span>Telemetry rows</div><div class=v id=rows>-</div><div class=k id=rate></div></div>
</div>
<div class=two>
<div class=card><div class=k>Array (world frame) <span class=legend><span style="color:var(--ok)">&#9632; healthy</span><span style="color:var(--bad)">&#9632; flagged</span><span style="color:var(--amb)">&#9632; shadow rejected</span><span style="color:var(--acc)">&#9679; robot true / &#9675; estimate</span></span></div><canvas id=map width=720 height=330></canvas></div>
<div class=card><div class=k>Cross-track error [cm], last 20 s</div><canvas id=ch1 width=360 height=150></canvas>
<div class=k style="margin-top:8px">Wheel torque L / R [N m]</div><canvas id=ch2 width=360 height=150></canvas></div>
</div>
<div class=card style="margin-top:10px"><div class=k>Recording</div><div id=recinfo class=v style="font-size:14px;font-weight:500"></div>
<div class=k style="margin-top:8px">FSM events</div><div id=log></div></div>
</main><script>
const $=i=>document.getElementById(i);
function line(c,ys,cols,unit){const x=c.getContext('2d'),W=c.width,H=c.height;x.clearRect(0,0,W,H);
 let all=ys.flat();if(!all.length)return;let lo=Math.min(...all,0),hi=Math.max(...all,0.01);if(hi-lo<1e-6)hi=lo+1;
 const st=getComputedStyle(document.body);x.strokeStyle=st.getPropertyValue('--line');x.beginPath();let z=H-(0-lo)/(hi-lo)*H;x.moveTo(0,z);x.lineTo(W,z);x.stroke();
 ys.forEach((y,k)=>{x.strokeStyle=cols[k];x.lineWidth=1.6;x.beginPath();y.forEach((v,i)=>{const px=i/(Math.max(y.length-1,1))*W,py=H-(v-lo)/(hi-lo)*H;i?x.lineTo(px,py):x.moveTo(px,py)});x.stroke()});
 x.fillStyle=st.getPropertyValue('--mut');x.font='11px system-ui';x.fillText(hi.toFixed(1)+unit,4,12);x.fillText(lo.toFixed(1)+unit,4,H-4)}
function map(s){const c=$('map'),x=c.getContext('2d'),W=c.width,H=c.height,g=s.geom,st=getComputedStyle(document.body);x.clearRect(0,0,W,H);
 const X=(v)=>(v-g.xmin)/(g.xmax-g.xmin)*W,Y=(v)=>H-(v-g.ymin)/(g.ymax-g.ymin)*H;
 s.panels.forEach(p=>{const col=p.s==2?st.getPropertyValue('--bad'):p.s==3?st.getPropertyValue('--amb'):p.s==1?st.getPropertyValue('--ok'):st.getPropertyValue('--line');
  x.fillStyle=col;x.globalAlpha=p.s?0.85:1;x.fillRect(X(p.x0),Y(p.y1),X(p.x1)-X(p.x0)-1,Y(p.y0)-Y(p.y1)-1);x.globalAlpha=1});
 x.strokeStyle=st.getPropertyValue('--mut');x.setLineDash([4,4]);s.path.length&&(x.beginPath(),s.path.forEach((q,i)=>i?x.lineTo(X(q[0]),Y(q[1])):x.moveTo(X(q[0]),Y(q[1]))),x.stroke());x.setLineDash([]);
 x.fillStyle=st.getPropertyValue('--acc');x.beginPath();x.arc(X(s.x),Y(s.y),6,0,7);x.fill();
 x.strokeStyle=st.getPropertyValue('--acc');x.beginPath();x.arc(X(s.xe),Y(s.ye),9,0,7);x.stroke();
 x.beginPath();x.moveTo(X(s.x),Y(s.y));x.lineTo(X(s.x+0.9*Math.cos(s.yaw)),Y(s.y+0.9*Math.sin(s.yaw)));x.lineWidth=2.5;x.stroke();x.lineWidth=1}
async function tick(){try{const s=await (await fetch('/state')).json();
 $('sub').textContent=`${s.condition} controller | seed ${s.seed} | ${s.n_defects} hidden defects (the robot is not told where) | wall ${s.wall.toFixed(0)} s`;
 $('st').textContent=s.state;$('t').textContent=s.t.toFixed(1)+' s';$('cte').textContent=(s.cte*100).toFixed(1)+' cm';
 $('pe').textContent=(s.pose_err*100).toFixed(1)+' cm';$('vis').textContent=s.visited+' / '+s.total;
 $('flg').textContent=s.flagged+(s.flagged_correct!==null?'  ('+s.flagged_correct+' true)':'');
 $('rows').textContent=s.rows.toLocaleString();$('rate').textContent=s.rate_hz.toFixed(0)+' rows per simulated second';
 $('recdot').className='rec'+(s.recording&&!s.done?'':' off');
 $('recinfo').textContent=s.recording?`Every physics step (dt = 0.002 s, 500 Hz) is logged: ${s.cols} columns. Saved on finish to ${s.csv||'(no --csv given: kept in memory only)'}`:'Telemetry not being recorded (start with --csv PATH to keep it)';
 line($('ch1'),[s.h_cte.map(v=>v*100)],['#2563eb'],' cm');line($('ch2'),[s.h_tl,s.h_tr],['#d98a00','#1a9e55'],'');
 map(s);const L=$('log');L.textContent=s.events.join('\n');L.scrollTop=L.scrollHeight;
 if(s.done)$('st').textContent='DONE';}catch(e){$('sub').textContent='waiting for the simulation...'}setTimeout(tick,200)}
tick();</script></body></html>"""


class LiveDashboard:
    def __init__(self, mission, port: int = 8765, csv_path: str | None = None):
        self.ms = mission
        self.port = port
        self.csv = csv_path
        self.lock = threading.Lock()
        self.state: dict = {}
        self.t_wall0 = time.time()
        self.h_cte = deque(maxlen=100)
        self.h_tl = deque(maxlen=100)
        self.h_tr = deque(maxlen=100)
        self.path = deque(maxlen=400)
        self.done = False
        self._truth = set(mission.gt.defect_panel_ids())
        cfg = mission.reg.cfg
        self._cfg = cfg
        self._last_t = 0.0
        self._last_rows = 0
        self._rate = 0.0
        self._geom = dict(xmin=cfg.dock_x - 1.0, xmax=cfg.x0 + cfg.n_cols * cfg.col_pitch + cfg.headland + 1.0,
                          ymin=cfg.y0 - cfg.lane_offset - 1.5,
                          ymax=cfg.y0 + (cfg.n_rows - 1) * cfg.row_pitch + cfg.panel_l * math.cos(math.radians(cfg.tilt_deg)) + 1.0)
        self._panel_boxes = []
        for p in mission.reg.panels:
            cx = p.center[0]
            y0 = mission.reg.row_low_y(p.row)
            self._panel_boxes.append((p.pid, cx - cfg.panel_w / 2, cx + cfg.panel_w / 2, y0,
                                      y0 + cfg.panel_l * math.cos(math.radians(cfg.tilt_deg))))
        self._server = None

    def start(self):
        dash = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.path.startswith("/state"):
                    with dash.lock:
                        body = json.dumps(dash.state).encode()
                    ctype = "application/json"
                else:
                    body, ctype = _PAGE.encode(), "text/html; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), H)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{self.port}/"

    def publish(self, ms, finished: bool = False):
        d = ms.d
        p = d.xpos[ms.chassis]
        R = d.xmat[ms.chassis].reshape(3, 3)
        yaw = math.atan2(R[1, 0], R[0, 0])
        leg = ms.legs[min(ms.leg_i, len(ms.legs) - 1)]
        cte = float(p[1] - leg["lane_y"])
        pose_err = math.hypot(ms.est.x - p[0], ms.est.y - p[1])
        w = ms.wheels
        tl = tr = 0.0
        if ms.tel is not None and ms.tel.n:
            row = ms.tel.buf[ms.tel.n - 1]
            from telemetry import COLUMNS
            tl, tr = float(row[COLUMNS.index("tau_left")]), float(row[COLUMNS.index("tau_right")])
        self.h_cte.append(cte)
        self.h_tl.append(tl)
        self.h_tr.append(tr)
        self.path.append((float(p[0]), float(p[1])))
        shadow = {r["panel_id_est"] for r in ms.detections if r.get("kind_est") == "SHADOW_CONFOUNDER"}
        flagged = {r["panel_id_est"] for r in ms.detections if r.get("kind_est") not in (None, "NONE", "SHADOW_CONFOUNDER")}
        visited = set(ms.visited)
        rows = ms.tel.n if ms.tel is not None else 0
        dt = d.time - self._last_t
        if dt > 0.5:
            self._rate = (rows - self._last_rows) / dt
            self._last_t, self._last_rows = d.time, rows
        panels = []
        for pid, x0, x1, y0, y1 in self._panel_boxes:
            s = 2 if pid in flagged else (3 if pid in shadow else (1 if pid in visited else 0))
            panels.append(dict(x0=x0, x1=x1, y0=y0, y1=y1, s=s))
        from telemetry import COLUMNS
        st = dict(condition=ms.cfg.condition, seed=ms.cfg.seed, n_defects=len(self._truth), t=float(d.time),
                  wall=time.time() - self.t_wall0, state=STATE_NAMES[ms.state], x=float(p[0]), y=float(p[1]), yaw=yaw,
                  xe=float(ms.est.x), ye=float(ms.est.y), cte=cte, pose_err=pose_err, visited=len(visited),
                  total=len(ms.reg.panels), flagged=len(flagged),
                  flagged_correct=len(flagged & self._truth), rows=int(rows), rate_hz=self._rate,
                  recording=ms.tel is not None, csv=self.csv, cols=len(COLUMNS), done=finished or ms.state == len(STATE_NAMES) - 1,
                  h_cte=list(self.h_cte), h_tl=list(self.h_tl), h_tr=list(self.h_tr), path=list(self.path)[::4],
                  panels=panels, geom=self._geom, events=ms.events[-40:])
        with self.lock:
            self.state = st
