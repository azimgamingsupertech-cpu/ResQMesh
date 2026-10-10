"""ResQMesh local-Wi-Fi mobile SOS interface.

Run on the laptop from the same folder as resqmesh.db:
    python resqmesh_mobile_sos.py
Then open http://LAPTOP_LAN_IP:5000 on the Android phone connected to the same Wi-Fi.
This service uses the local network only; it does not send messages to an internet service.
"""
from datetime import datetime, timezone
from pathlib import Path
import ipaddress
import json
import os
import socket
import sqlite3
import uuid

from flask import Flask, jsonify, request, Response

APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("RESQMESH_DB", str(APP_DIR / "resqmesh.db")))
app = Flask(__name__)


def db_connect():
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db_connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS offline_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                emergency TEXT NOT NULL,
                location TEXT NOT NULL,
                details TEXT,
                status TEXT NOT NULL DEFAULT 'Received',
                message_uuid TEXT UNIQUE
            )
        """)
        cols = {row[1] for row in con.execute("PRAGMA table_info(offline_messages)")}
        if "message_uuid" not in cols:
            con.execute("ALTER TABLE offline_messages ADD COLUMN message_uuid TEXT")
            con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_offline_messages_uuid ON offline_messages(message_uuid)")
        if "status" not in cols:
            con.execute("ALTER TABLE offline_messages ADD COLUMN status TEXT NOT NULL DEFAULT 'Received'")

        con.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT,
                emergency TEXT NOT NULL,
                location TEXT NOT NULL,
                details TEXT,
                status TEXT NOT NULL DEFAULT 'Open',
                latitude REAL,
                longitude REAL,
                priority TEXT NOT NULL DEFAULT 'High'
            )
        """)
        alert_cols = {row[1] for row in con.execute("PRAGMA table_info(alerts)")}
        # Safe migrations for databases created by older ResQMesh versions.
        migrations = {
            "name": "ALTER TABLE alerts ADD COLUMN name TEXT",
            "status": "ALTER TABLE alerts ADD COLUMN status TEXT NOT NULL DEFAULT 'Open'",
            "latitude": "ALTER TABLE alerts ADD COLUMN latitude REAL",
            "longitude": "ALTER TABLE alerts ADD COLUMN longitude REAL",
            "priority": "ALTER TABLE alerts ADD COLUMN priority TEXT NOT NULL DEFAULT 'High'",
        }
        for col, sql in migrations.items():
            if col not in alert_cols:
                con.execute(sql)


def local_ip_candidates():
    found = []
    try:
        # This only asks the OS which local interface it would use; no packets are sent to an external service.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 9))  # TEST-NET address; connect() does not send a packet.
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            found.append(ip)
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in found:
                found.append(ip)
    except OSError:
        pass
    return found


@app.get("/")
def home():
    return Response(PAGE, mimetype="text/html")


@app.get("/api/health")
def health():
    return jsonify(ok=True, service="ResQMesh local Wi-Fi SOS", database=str(DB_PATH.name), delivery="local-network-only")


@app.post("/api/sos")
def receive_sos():
    data = request.get_json(silent=True) or request.form.to_dict()
    emergency = str(data.get("emergency", "Other")).strip()[:80]
    name = str(data.get("name", "Anonymous")).strip()[:100] or "Anonymous"
    location = str(data.get("location", "Location not provided")).strip()[:300] or "Location not provided"
    details = str(data.get("details", "")).strip()[:2000]
    message_uuid = str(data.get("message_uuid", "")).strip()[:80] or str(uuid.uuid4())
    lat = data.get("latitude")
    lon = data.get("longitude")
    try:
        lat = float(lat) if lat not in (None, "") else None
        lon = float(lon) if lon not in (None, "") else None
        if lat is not None and not -90 <= lat <= 90: raise ValueError
        if lon is not None and not -180 <= lon <= 180: raise ValueError
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Invalid GPS coordinates."), 400

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    priority = "Critical" if emergency in ("Trapped", "Medical emergency", "Fire", "Flood") else "High"
    try:
        with db_connect() as con:
            existing = con.execute("SELECT id FROM offline_messages WHERE message_uuid=?", (message_uuid,)).fetchone()
            if existing:
                return jsonify(ok=True, duplicate=True, message_id=existing["id"], status="Received")

            msg_cols = {row[1] for row in con.execute("PRAGMA table_info(offline_messages)")}
            msg_values = {
                "created_at": now, "emergency": emergency, "location": location,
                "details": details, "status": "Received", "message_uuid": message_uuid,
            }
            insert_cols = [c for c in msg_values if c in msg_cols]
            sql = f"INSERT INTO offline_messages ({','.join(insert_cols)}) VALUES ({','.join('?' for _ in insert_cols)})"
            cur = con.execute(sql, [msg_values[c] for c in insert_cols])
            message_id = cur.lastrowid

            # Also add to the dashboard's alerts table so the incident appears in the main incident list/map.
            alert_cols = {row[1] for row in con.execute("PRAGMA table_info(alerts)")}
            alert_values = {
                "created_at": now, "name": name, "emergency": emergency,
                "location": location, "details": details, "status": "Open",
                "latitude": lat, "longitude": lon, "priority": priority,
            }
            acols = [c for c in alert_values if c in alert_cols]
            asql = f"INSERT INTO alerts ({','.join(acols)}) VALUES ({','.join('?' for _ in acols)})"
            con.execute(asql, [alert_values[c] for c in acols])
        return jsonify(ok=True, message_id=message_id, status="Received", received_at=now)
    except sqlite3.Error as exc:
        app.logger.exception("Could not store SOS")
        return jsonify(ok=False, error="The laptop could not save the SOS. Keep it pending and retry.", detail=str(exc)), 500


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#020607"><title>ResQMesh SOS</title>
<style>
:root{color-scheme:dark;--bg:#020607;--panel:#07191d;--panel2:#0a2429;--cyan:#00f0ff;--cyan2:#00b8c8;--text:#eaffff;--muted:#9abcc0;--border:rgba(0,240,255,.22);--red:#ff355d}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 50% -10%,#07353c 0,transparent 45%),linear-gradient(160deg,#020607,#041316 55%,#020607);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--text);min-height:100vh}
.wrap{width:min(100%,520px);margin:auto;padding:calc(18px + env(safe-area-inset-top)) 17px calc(24px + env(safe-area-inset-bottom))}.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}.brand{font-size:1.25rem;font-weight:850;letter-spacing:.02em}.brand b{color:var(--cyan)}.pill{font-size:.7rem;color:#a3fff7;border:1px solid var(--border);background:#06252a;border-radius:999px;padding:7px 10px;letter-spacing:.08em}
.hero{padding:22px 19px;border:1px solid var(--border);border-radius:22px;background:linear-gradient(140deg,rgba(7,35,40,.98),rgba(4,15,18,.97));box-shadow:0 0 30px #00f0ff0d;margin-bottom:16px}.eyebrow{font-size:.69rem;letter-spacing:.17em;color:var(--cyan);font-weight:800}.hero h1{font-size:1.8rem;line-height:1.1;margin:9px 0}.hero p{color:var(--muted);font-size:.9rem;line-height:1.5;margin:0}
.sos-area{display:grid;place-items:center;padding:14px 0 20px}.sos{width:190px;height:190px;border-radius:50%;border:3px solid #ff9caf;background:radial-gradient(circle at 40% 28%,#ff607d,#d80032 65%,#780019);color:white;font-weight:950;font-size:2.2rem;letter-spacing:.04em;box-shadow:0 0 0 9px #ff355d12,0 0 40px #ff174c3d,inset 0 2px 9px #ffffff55;cursor:pointer;touch-action:manipulation;transition:transform .12s}.sos:active{transform:scale(.96)}.sos:disabled{opacity:.55}.sos-caption{font-size:.78rem;color:var(--muted);text-align:center;margin-top:12px}
.card{background:linear-gradient(145deg,#07191d,#041013);border:1px solid var(--border);border-radius:18px;padding:16px;margin:12px 0}.card h2{font-size:.95rem;margin:0 0 13px}.field{margin:12px 0}.field label{display:block;font-size:.77rem;color:#b6d9dc;margin-bottom:7px}.field input,.field textarea,.field select{width:100%;background:#02090b;color:var(--text);border:1px solid #1a464c;border-radius:11px;padding:12px;font:inherit;font-size:.92rem;outline:none}.field input:focus,.field textarea:focus,.field select:focus{border-color:var(--cyan);box-shadow:0 0 0 3px #00f0ff12}.field textarea{min-height:82px;resize:vertical}.row{display:flex;gap:9px}.row>*{flex:1;min-width:0}.btn{border:1px solid var(--border);background:linear-gradient(110deg,#064650,#087d89);color:white;padding:12px 14px;border-radius:12px;font-weight:750;font-size:.88rem;width:100%;cursor:pointer}.btn.secondary{background:#07171a;color:#b9faff}.btn:disabled{opacity:.5}.hint{color:var(--muted);font-size:.75rem;line-height:1.5}.status{padding:12px;border-radius:12px;font-size:.85rem;margin-top:12px;display:none;white-space:pre-wrap}.status.good{display:block;background:#06271e;border:1px solid #168d69;color:#a6ffda}.status.bad{display:block;background:#2c0b14;border:1px solid #a42a43;color:#ffc0cb}.status.wait{display:block;background:#08242a;border:1px solid #126d78;color:#a7f8ff}.foot{text-align:center;color:#6d969b;font-size:.7rem;line-height:1.5;margin-top:18px}
@media(min-width:430px){.sos{width:205px;height:205px}}@media(prefers-reduced-motion:reduce){*{transition:none!important}}
</style></head><body><main class="wrap">
<header class="top"><div class="brand">🆘 ResQ<b>Mesh</b></div><span class="pill">LOCAL WI-FI MODE</span></header>
<section class="hero"><div class="eyebrow">EMERGENCY RESPONSE NETWORK</div><h1>Send an SOS.<br>Reach the command centre.</h1><p>Messages are sent directly over your local Wi-Fi to the ResQMesh laptop. No internet service is used for delivery.</p></section>
<section class="sos-area"><button id="sos" class="sos" type="button">SEND<br>SOS</button><div class="sos-caption">Use only for a real emergency during field testing.<br>For demos, label your message as a test.</div></section>
<section class="card"><h2>Emergency details</h2>
<div class="field"><label for="name">Your name / ID</label><input id="name" maxlength="100" placeholder="e.g. Responder 01" autocomplete="name"></div>
<div class="field"><label for="emergency">Emergency type</label><select id="emergency"><option>Trapped</option><option>Medical emergency</option><option>Flood</option><option>Fire</option><option>Evacuation</option><option>Food / Water</option><option>Safe</option><option>Other</option><option>TEST MESSAGE</option></select></div>
<div class="field"><label for="location">Location description</label><input id="location" maxlength="300" placeholder="Street, building, shelter or landmark"></div>
<div class="row"><div class="field"><label for="lat">Latitude (optional)</label><input id="lat" inputmode="decimal" placeholder="10.5276"></div><div class="field"><label for="lon">Longitude (optional)</label><input id="lon" inputmode="decimal" placeholder="76.2144"></div></div>
<button class="btn secondary" id="gps" type="button">◎ Get phone GPS location</button><p class="hint">GPS permission may require HTTPS in Chrome. If GPS is blocked on the local HTTP address, type a landmark or enter coordinates manually.</p>
<div class="field"><label for="details">What help is needed?</label><textarea id="details" maxlength="2000" placeholder="Number of people, injuries, hazards, or other useful details"></textarea></div>
<button class="btn" id="send" type="button">Send emergency details</button><div id="status" class="status" role="status" aria-live="polite"></div>
</section>
<section class="card"><h2>Delivery queue</h2><div id="queue" class="hint">Checking saved messages…</div><button class="btn secondary" id="retry" type="button" style="margin-top:10px">Retry pending messages</button><p class="hint">If the laptop is unreachable, this page stores pending messages in this browser and retries when you tap retry or the page regains connectivity. Keep this page open for automatic retry.</p></section>
<div class="foot">ResQMesh prototype · Local-network communication only<br>Not a replacement for official emergency services.</div>
</main>
<script>
const $=id=>document.getElementById(id); const STORE='resqmesh_pending_sos_v1'; let sending=false;
function getQueue(){try{return JSON.parse(localStorage.getItem(STORE)||'[]')}catch(e){return []}}
function setQueue(q){localStorage.setItem(STORE,JSON.stringify(q));renderQueue()}
function renderQueue(){const q=getQueue();$('queue').textContent=q.length?`${q.length} pending message(s) saved on this phone.`:'No pending messages.'}
function notice(text,type='wait'){$('status').className='status '+type;$('status').textContent=text}
function makePayload(){const emergency=$('emergency').value;return {message_uuid:crypto.randomUUID?crypto.randomUUID():('rq-'+Date.now()+'-'+Math.random().toString(16).slice(2)),name:$('name').value.trim()||'Anonymous',emergency,location:$('location').value.trim()||'Location not provided',latitude:$('lat').value.trim()||null,longitude:$('lon').value.trim()||null,details:$('details').value.trim()}}
async function deliver(payload){const res=await fetch('/api/sos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),cache:'no-store'});let data={};try{data=await res.json()}catch(e){}if(!res.ok||!data.ok)throw new Error(data.error||`Laptop returned HTTP ${res.status}`);return data}
async function sendNew(){if(sending)return;sending=true;$('send').disabled=true;$('sos').disabled=true;const payload=makePayload();try{const result=await deliver(payload);notice(`SOS RECEIVED by laptop command centre. Message ID: ${result.message_id}`,'good');$('details').value='';}catch(e){const q=getQueue();q.push(payload);setQueue(q);notice('Laptop not reachable. SOS saved as PENDING on this phone. Check same Wi-Fi and laptop service, then retry.\n'+e.message,'bad')}finally{sending=false;$('send').disabled=false;$('sos').disabled=false;renderQueue()}}
async function retryQueue(){const q=getQueue();if(!q.length){notice('No pending messages to retry.','wait');return}let remaining=[];let delivered=0;for(const p of q){try{await deliver(p);delivered++}catch(e){remaining.push(p)}}setQueue(remaining);if(remaining.length)notice(`${delivered} delivered; ${remaining.length} still pending. Check Wi-Fi and laptop.`,'bad');else notice(`${delivered} pending message(s) delivered to the laptop.`,'good')}
$('send').addEventListener('click',sendNew);$('sos').addEventListener('click',()=>{if(confirm('Send an SOS to the ResQMesh laptop now?'))sendNew()});$('retry').addEventListener('click',retryQueue);
$('gps').addEventListener('click',()=>{if(!navigator.geolocation){notice('This browser does not provide GPS location. Enter the location manually.','bad');return}notice('Requesting phone location permission…');navigator.geolocation.getCurrentPosition(pos=>{$('lat').value=pos.coords.latitude.toFixed(6);$('lon').value=pos.coords.longitude.toFixed(6);if(!$('location').value.trim())$('location').value='Phone GPS location';notice('GPS coordinates added.','good')},err=>notice('GPS unavailable: '+err.message+'. On a local HTTP address, Chrome may block GPS. Enter a landmark or coordinates manually.','bad'),{enableHighAccuracy:true,timeout:12000,maximumAge:30000})});
window.addEventListener('online',retryQueue);renderQueue();fetch('/api/health',{cache:'no-store'}).then(r=>r.json()).then(()=>{}).catch(()=>notice('Cannot reach local SOS service. Check the laptop IP and Wi-Fi.','bad'));
</script></body></html>'''


if __name__ == "__main__":
    init_db()
    print("\nResQMesh Mobile SOS is starting (local network only).")
    print(f"Database: {DB_PATH}")
    print("Open one of these addresses on the laptop:")
    print("  http://127.0.0.1:5000")
    for ip in local_ip_candidates():
        try:
            ipaddress.ip_address(ip)
            print(f"  http://{ip}:5000  <-- try this on your Android phone (same Wi-Fi)")
        except ValueError:
            pass
    print("Keep this terminal open. Allow Python through Windows Firewall on Private networks if prompted.\n")
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
