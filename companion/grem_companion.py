#!/usr/bin/env python3
"""
G.R.E.M. companion (Windows).  Run it while the console is plugged in by USB.

  - sends the real time, now-playing, CPU/GPU/RAM load to the console's OLED
  - tells the console which app is in front (CapCut / After Effects) so it switches profile by itself
  - tells the console when a render looks finished
  - forwards Windows notifications (EXPERIMENTAL, see README)
  - serves a key-map editor at http://localhost:8765
"""
import asyncio, ctypes, http.server, json, os, queue, re, socketserver, subprocess, sys, threading, time
import psutil
import serial
from serial.tools import list_ports

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "grem_config.json")
PORT_HTTP = 8765

# ------------------------------------------------------------------ key tables
MODS = {"ctrl": 1, "shift": 2, "alt": 4, "win": 8}
KEYS = {}
for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    KEYS[ch] = 0x04 + i
for i, ch in enumerate("1234567890"):
    KEYS[ch] = 0x1E + i
KEYS.update({"ENTER": 0x28, "ESC": 0x29, "BACKSPACE": 0x2A, "TAB": 0x2B, "SPACE": 0x2C, "-": 0x2D, "=": 0x2E,
             "[": 0x2F, "]": 0x30, "\\": 0x31, ";": 0x33, "'": 0x34, "`": 0x35, ",": 0x36, ".": 0x37, "/": 0x38,
             "INSERT": 0x49, "HOME": 0x4A, "PAGEUP": 0x4B, "DELETE": 0x4C, "END": 0x4D, "PAGEDOWN": 0x4E,
             "RIGHT": 0x4F, "LEFT": 0x50, "DOWN": 0x51, "UP": 0x52})
for i in range(12):
    KEYS["F%d" % (i + 1)] = 0x3A + i
CONSUMER = {"VOL_UP": 0xE9, "VOL_DOWN": 0xEA, "MUTE": 0xE2, "PLAY_PAUSE": 0xCD, "NEXT_TRACK": 0xB5,
            "PREV_TRACK": 0xB6, "STOP": 0xB7}


def A(key, name, mods=(), kind="key"):
    return {"type": kind, "mods": list(mods), "key": key, "name": name}


def default_config():
    """Mirrors the defaults compiled into the firmware (actions.h)."""
    cap_keys = [A("Z", "UNDO", ["ctrl"]), A("Z", "REDO", ["ctrl", "shift"]), A("DELETE", "DELETE"),
                A("B", "SPLIT", ["ctrl"]), A("Q", "TRIM START"), A("W", "TRIM END"),
                A("C", "COPY", ["ctrl"]), A("V", "PASTE", ["ctrl"]), A("E", "EXPORT", ["ctrl"])]
    cap_dials = [
        {"cw": A("VOL_UP", "VOL +", kind="consumer"), "ccw": A("VOL_DOWN", "VOL -", kind="consumer"), "push": A("MUTE", "MUTE", kind="consumer")},
        {"cw": A("=", "ZOOM IN", ["ctrl"]), "ccw": A("-", "ZOOM OUT", ["ctrl"]), "push": A("HOME", "GO START")},
        {"cw": A("DOWN", "NEXT CLIP"), "ccw": A("UP", "PREV CLIP"), "push": A("END", "GO END")},
        {"cw": A("RIGHT", "+SHIFT >", ["shift"]), "ccw": A("LEFT", "< SHIFT", ["shift"]), "push": A("ENTER", "ENTER")},
        {"cw": A("RIGHT", "FRAME >"), "ccw": A("LEFT", "< FRAME"), "push": A("SPACE", "PLAY/PAUSE")}]
    ae_keys = [A("Z", "UNDO", ["ctrl"]), A("Z", "REDO", ["ctrl", "shift"]), A("DELETE", "DELETE"),
               A("D", "SPLIT LAYER", ["ctrl", "shift"]), A("B", "WORK AREA IN"), A("N", "WORK AREA OUT"),
               A("C", "PRECOMPOSE", ["ctrl", "shift"]), A("S", "SAVE", ["ctrl"]), A("M", "RENDER QUEUE", ["ctrl"])]
    ae_dials = [
        {"cw": A("VOL_UP", "VOL +", kind="consumer"), "ccw": A("VOL_DOWN", "VOL -", kind="consumer"), "push": A("MUTE", "MUTE", kind="consumer")},
        {"cw": A(".", "ZOOM IN"), "ccw": A(",", "ZOOM OUT"), "push": A("/", "FIT VIEW", ["shift"])},
        {"cw": A("DOWN", "NEXT LAYER", ["ctrl"]), "ccw": A("UP", "PREV LAYER", ["ctrl"]), "push": A("HOME", "GO START")},
        {"cw": A("PAGEDOWN", "+10 FRAMES", ["shift"]), "ccw": A("PAGEUP", "-10 FRAMES", ["shift"]), "push": A("END", "GO END")},
        {"cw": A("PAGEDOWN", "FRAME >"), "ccw": A("PAGEUP", "< FRAME"), "push": A("SPACE", "PLAY/PAUSE")}]
    return {
        "profiles": [{"name": "CAPCUT", "keys": cap_keys, "dials": cap_dials},
                     {"name": "AFTER EFFECTS", "keys": ae_keys, "dials": ae_dials}],
        "auto_profile": True,
        "app_map": {"capcut": ["capcut.exe", "capcut"], "ae": ["afterfx.exe"]},
        "render_detect": True,
        "notifications": True,
    }


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        base = default_config()
        base.update(cfg)
        return base
    except Exception:
        return default_config()


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def encode_action(a):
    """-> (mods_bitmask, usage_code, consumer_flag, name)"""
    name = re.sub(r"[^\x20-\x7E]", "?", str(a.get("name", ""))).strip()[:17] or "KEY"
    if a.get("type") == "consumer":
        return 0, CONSUMER.get(a.get("key"), 0), 1, name
    mods = 0
    for m in a.get("mods", []):
        mods |= MODS.get(m, 0)
    return mods, KEYS.get(str(a.get("key", "")).upper(), 0), 0, name


def config_to_lines(cfg):
    lines = []
    for p, prof in enumerate(cfg["profiles"][:2]):
        for i, a in enumerate(prof["keys"][:9]):
            m, c, k, n = encode_action(a)
            lines.append("K %d %d %d %d %d %s" % (p, i, m, c, k, n))
        for i, d in enumerate(prof["dials"][:5]):
            for w, which in enumerate(("cw", "ccw", "push")):
                m, c, k, n = encode_action(d[which])
                lines.append("D %d %d %d %d %d %d %s" % (p, i, w, m, c, k, n))
    lines.append("SAVE")
    return lines


# ------------------------------------------------------------------ shared state
class State:
    def __init__(self):
        self.cfg = load_config()
        self.outq = queue.Queue()
        self.linked = False
        self.port = ""
        self.device_log = []
        self.media = ""
        self.fg = ""
        self.stats = (0, 0, 0, 0)
        self.last_notify = ""
        self.notif_status = "not started"
        self.media_status = "not started"
        self.lock = threading.Lock()


ST = State()


def send(line):
    ST.outq.put(line)


def logdev(msg):
    with ST.lock:
        ST.device_log.append(time.strftime("%H:%M:%S ") + msg)
        del ST.device_log[:-30]


# ------------------------------------------------------------------ serial thread
def find_port():
    for p in list_ports.comports():
        if p.vid == 0x303A:                      # Espressif
            return p.device
    return None


def serial_thread():
    while True:
        port = find_port()
        if not port:
            ST.linked, ST.port = False, ""
            time.sleep(2)
            continue
        try:
            with serial.Serial(port, 115200, timeout=0.2, write_timeout=2) as s:
                ST.linked, ST.port = True, port
                logdev("connected on " + port)
                send_time()
                last_ping = time.time()
                while True:
                    try:
                        while True:
                            line = ST.outq.get_nowait()
                            s.write((line + "\n").encode("ascii", "replace"))
                            if line.startswith(("K ", "D ")):
                                time.sleep(0.01)
                    except queue.Empty:
                        pass
                    raw = s.readline()
                    if raw:
                        logdev("device: " + raw.decode("ascii", "replace").strip())
                    if time.time() - last_ping > 3:
                        s.write(b"PING\n"); last_ping = time.time()
        except Exception as e:
            ST.linked = False
            logdev("serial error: %s" % e)
            time.sleep(2)


def send_time():
    tz = -(time.altzone if time.localtime().tm_isdst > 0 else time.timezone) // 60
    send("T %d %d" % (int(time.time()), tz))


# ------------------------------------------------------------------ samplers
def gpu_stats():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=2,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip().splitlines()[0]
        u, t = [int(x) for x in out.split(",")]
        return u, t
    except Exception:
        return -1, -1


def foreground_exe():
    try:
        u = ctypes.windll.user32
        hwnd = u.GetForegroundWindow()
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return psutil.Process(pid.value).name().lower()
    except Exception:
        return ""


def app_hint(exe):
    for tag, names in ST.cfg.get("app_map", {}).items():
        if any(n.lower() in exe for n in names):
            return tag
    return "other"


EDIT_APPS = ("capcut", "afterfx", "aerender", "media encoder", "resolve", "premiere")


def sampler_thread():
    psutil.cpu_percent()
    last_hint, tick = None, 0
    busy_s, low_s, armed, aerender_seen = 0, 0, False, False
    while True:
        time.sleep(1)
        tick += 1
        cpu = int(psutil.cpu_percent())
        ram = int(psutil.virtual_memory().percent)
        gpu, gt = gpu_stats()
        ST.stats = (cpu, gpu, ram, gt)
        send("S %d %d %d %d" % (cpu, gpu, ram, gt))
        exe = foreground_exe()
        ST.fg = exe
        hint = app_hint(exe)
        if hint != last_hint and ST.cfg.get("auto_profile", True):
            send("A " + hint)
        last_hint = hint
        if tick % 30 == 0:
            send_time()
        # ---- render-finished detection (a heuristic, not a promise) ----
        if ST.cfg.get("render_detect", True):
            try:
                names = [p.name().lower() for p in psutil.process_iter(["name"]) if p.info["name"]]
            except Exception:
                names = []
            ae_now = any("aerender" in n for n in names)
            if aerender_seen and not ae_now:
                send("R After Effects render finished")
            aerender_seen = ae_now
            editing = any(any(e in n for e in EDIT_APPS) for n in names)
            load = max(cpu, gpu)
            if editing and load >= 60:
                busy_s += 1; low_s = 0
                if busy_s >= 45:
                    armed = True
            elif armed and load < 20:
                low_s += 1
                if low_s >= 8:
                    send("R Render looks finished (load dropped)")
                    armed, busy_s, low_s = False, 0, 0
            elif not armed:
                busy_s = 0


def media_thread():
    try:
        from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Mgr
    except Exception as e:
        ST.media_status = "unavailable (install winsdk): %s" % e
        return

    async def now_playing():
        mgr = await Mgr.request_async()
        s = mgr.get_current_session()
        if not s:
            return ""
        info = s.get_playback_info()
        if info.playback_status != 4:            # 4 = playing
            return ""
        p = await s.try_get_media_properties_async()
        return "%s|%s" % (p.title or "", p.artist or "")

    ST.media_status = "ok"
    last, last_t = None, 0
    while True:
        try:
            m = asyncio.run(now_playing())
        except Exception as e:
            ST.media_status = "error: %s" % e
            m = ""
        if m != last or time.time() - last_t > 10:
            send("M " + re.sub(r"[^\x20-\x7E]", "?", m))
            last, last_t = m, time.time()
        ST.media = m
        time.sleep(2)


def notif_thread():
    """EXPERIMENTAL. Windows only lets *packaged* apps read other apps' notifications, so this may
    be denied for plain Python. The test button in the web page always works."""
    if not ST.cfg.get("notifications", True):
        ST.notif_status = "disabled in config"
        return
    try:
        from winsdk.windows.ui.notifications.management import UserNotificationListener, UserNotificationListenerAccessStatus
        from winsdk.windows.ui.notifications import NotificationKinds
    except Exception as e:
        ST.notif_status = "unavailable: %s" % e
        return

    async def poll(seen, first):
        lst = UserNotificationListener.current
        if first[0]:
            st = await lst.request_access_async()
            if st != UserNotificationListenerAccessStatus.ALLOWED:
                return "access " + str(st)
        items = await lst.get_notifications_async(NotificationKinds.TOAST)
        for n in items:
            if n.id in seen:
                continue
            seen.add(n.id)
            if first[0]:
                continue
            try:
                app = n.app_info.display_info.display_name
                binding = n.notification.visual.get_binding("ToastGeneric")
                texts = [t.text for t in binding.get_text_elements()]
                send("N %s|%s" % (app[:14], " - ".join(texts)[:98]))
                ST.last_notify = "%s: %s" % (app, " - ".join(texts))
            except Exception:
                pass
        first[0] = False
        return "ok"

    seen, first = set(), [True]
    while True:
        try:
            ST.notif_status = asyncio.run(poll(seen, first))
        except Exception as e:
            ST.notif_status = "error: %s" % e
            time.sleep(10)
        time.sleep(2)


# ------------------------------------------------------------------ web editor
PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>G.R.E.M. key map</title>
<style>
:root{--bg:#101114;--card:#1a1c21;--ink:#e9eaee;--mut:#8b8f9a;--acc:#ff7a1a;--line:#2a2d35}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px system-ui,sans-serif;padding:16px;max-width:1100px;margin-inline:auto}
h1{font-size:20px;margin:0 0 4px}h2{font-size:15px;margin:22px 0 8px;color:var(--acc)}
.mut{color:var(--mut)}.bar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
button{background:var(--acc);color:#111;border:0;border-radius:8px;padding:9px 14px;font-weight:600;cursor:pointer}
button.alt{background:var(--card);color:var(--ink);border:1px solid var(--line)}
.tabs button{background:var(--card);color:var(--ink);border:1px solid var(--line)}.tabs button.on{background:var(--acc);color:#111}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.dials{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}
.cell{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}
.cell b{display:block;margin-bottom:6px;font-size:12px;color:var(--mut)}
.row{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:6px}
input[type=text],select{background:#0d0e11;color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:6px;width:100%}
label.m{font-size:12px;color:var(--mut);display:flex;gap:3px;align-items:center}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px;margin:8px 0;font-size:13px}
@media(max-width:640px){.grid{grid-template-columns:1fr}}
</style></head><body>
<h1>G.R.E.M. key map</h1><div class="mut">Change what every key and dial does, then press <b>Send to console</b>. It is stored on the console, so it survives unplugging.</div>
<div class="stat" id="stat">loading...</div>
<div class="tabs bar" id="tabs"></div>
<h2>Keys (as seen from the front: top row is next to the screen)</h2><div class="grid" id="keys"></div>
<h2>Dials</h2><div class="dials" id="dials"></div>
<div class="bar"><button onclick="sendDev()">Send to console</button><button class="alt" onclick="saveOnly()">Save on PC only</button><button class="alt" onclick="resetAll()">Reset to defaults</button></div>
<h2>Options</h2>
<div class="bar"><label class="m"><input type="checkbox" id="auto"> auto-switch profile by app</label>
<label class="m"><input type="checkbox" id="rdet"> render-finished detection</label></div>
<h2>Test the screen</h2>
<div class="bar"><input type="text" id="ntxt" placeholder="Test notification text" style="max-width:420px"><button class="alt" onclick="testNotify()">Send notification</button><button class="alt" onclick="testRender()">Send "render done"</button></div>
<script>
let cfg=null,KEYS=[],CONS=[],cur=0;
const MODS=['ctrl','shift','alt','win'];
async function j(u,o){const r=await fetch(u,o);return r.json()}
function actEditor(a,path){
  const id=path;const d=document.createElement('div');
  const opts='<optgroup label="Keys">'+KEYS.map(k=>`<option ${a.type=='key'&&a.key==k?'selected':''}>${k}</option>`).join('')+'</optgroup><optgroup label="Media">'+CONS.map(k=>`<option value="c:${k}" ${a.type=='consumer'&&a.key==k?'selected':''}>${k}</option>`).join('')+'</optgroup>';
  d.innerHTML=`<div class="row"><input type="text" maxlength="17" value="${a.name.replace(/"/g,'')}" data-f="name" placeholder="label on screen"></div>
  <div class="row">${MODS.map(m=>`<label class="m"><input type="checkbox" data-m="${m}" ${a.mods.includes(m)?'checked':''}>${m}</label>`).join('')}</div>
  <div class="row"><select data-f="key">${opts}</select></div>`;
  d.addEventListener('input',()=>{
    a.name=d.querySelector('[data-f=name]').value;
    a.mods=MODS.filter(m=>d.querySelector(`[data-m=${m}]`).checked);
    const v=d.querySelector('[data-f=key]').value;
    if(v.startsWith('c:')){a.type='consumer';a.key=v.slice(2)}else{a.type='key';a.key=v}
  });return d}
function render(){
  const p=cfg.profiles[cur];
  document.getElementById('tabs').innerHTML=cfg.profiles.map((x,i)=>`<button class="${i==cur?'on':''}" onclick="cur=${i};render()">${x.name}</button>`).join('');
  const kg=document.getElementById('keys');kg.innerHTML='';
  p.keys.forEach((a,i)=>{const c=document.createElement('div');c.className='cell';c.innerHTML=`<b>KEY ${i+1}</b>`;c.appendChild(actEditor(a));kg.appendChild(c)});
  const dg=document.getElementById('dials');dg.innerHTML='';
  const names=['Small dial 1 (left)','Small dial 2','Small dial 3','Small dial 4','BIG dial'];
  p.dials.forEach((d,i)=>{const c=document.createElement('div');c.className='cell';c.innerHTML=`<b>${names[i]}</b>`;
    [['cw','turn clockwise'],['ccw','turn counter-clockwise'],['push','push']].forEach(([w,t])=>{const h=document.createElement('div');h.className='mut';h.textContent=t;h.style.fontSize='12px';c.appendChild(h);c.appendChild(actEditor(d[w]))});dg.appendChild(c)});
  document.getElementById('auto').checked=cfg.auto_profile;document.getElementById('rdet').checked=cfg.render_detect;
}
function collect(){cfg.auto_profile=document.getElementById('auto').checked;cfg.render_detect=document.getElementById('rdet').checked}
async function saveOnly(){collect();await j('/api/config',{method:'POST',body:JSON.stringify(cfg)});alert('Saved on this PC')}
async function sendDev(){collect();const r=await j('/api/push',{method:'POST',body:JSON.stringify(cfg)});alert(r.ok?'Sent to the console':'Console not connected: '+r.error)}
async function resetAll(){if(!confirm('Reset every key and dial to the defaults?'))return;cfg=await j('/api/reset',{method:'POST'});render()}
async function testNotify(){await j('/api/notify',{method:'POST',body:JSON.stringify({app:'TEST',text:document.getElementById('ntxt').value||'Hello from your PC'})})}
async function testRender(){await j('/api/render',{method:'POST'})}
async function stat(){const s=await j('/api/status');document.getElementById('stat').innerHTML=
 `Console: <b>${s.linked?'connected on '+s.port:'not found (plug it in with USB)'}</b> &middot; Front app: ${s.fg||'-'} &middot; CPU ${s.stats[0]}% GPU ${s.stats[1]}% RAM ${s.stats[2]}%<br>Now playing: ${s.media_status=='ok'?(s.media||'nothing'):s.media_status} &middot; Notifications: ${s.notif_status}<br><span class="mut">${s.log.slice(-3).join(' | ')}</span>`}
(async()=>{const k=await j('/api/keys');KEYS=k.keys;CONS=k.consumer;cfg=await j('/api/config');render();stat();setInterval(stat,2000)})();
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def _local_only(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("localhost", "127.0.0.1")

    def do_GET(self):
        if not self._local_only():
            self.send_error(403); return
        if self.path in ("/", "/index.html"):
            body = PAGE.encode()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        elif self.path == "/api/config":
            self._json(ST.cfg)
        elif self.path == "/api/keys":
            self._json({"keys": list(KEYS.keys()), "consumer": list(CONSUMER.keys())})
        elif self.path == "/api/status":
            with ST.lock:
                log = list(ST.device_log)
            self._json({"linked": ST.linked, "port": ST.port, "fg": ST.fg, "stats": ST.stats, "media": ST.media,
                        "media_status": ST.media_status, "notif_status": ST.notif_status, "log": log})
        else:
            self.send_error(404)

    def do_POST(self):
        if not self._local_only():
            self.send_error(403); return
        try:
            data = self._body()
        except Exception:
            self._json({"ok": False, "error": "bad json"}, 400); return
        if self.path == "/api/config":
            ST.cfg = data; save_config(data); self._json({"ok": True})
        elif self.path == "/api/push":
            ST.cfg = data; save_config(data)
            if not ST.linked:
                self._json({"ok": False, "error": "console not connected"}); return
            for line in config_to_lines(data):
                send(line)
            self._json({"ok": True})
        elif self.path == "/api/reset":
            ST.cfg = default_config(); save_config(ST.cfg)
            if ST.linked:
                send("RESET")
            self._json(ST.cfg)
        elif self.path == "/api/notify":
            send("N %s|%s" % (str(data.get("app", "NOTICE"))[:14], str(data.get("text", ""))[:98]))
            self._json({"ok": True})
        elif self.path == "/api/render":
            send("R Test render finished"); self._json({"ok": True})
        else:
            self.send_error(404)


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    for fn in (serial_thread, sampler_thread, media_thread, notif_thread):
        threading.Thread(target=fn, daemon=True).start()
    srv = Server(("127.0.0.1", PORT_HTTP), Handler)
    print("G.R.E.M. companion running. Key-map editor: http://localhost:%d   (Ctrl+C to quit)" % PORT_HTTP)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
