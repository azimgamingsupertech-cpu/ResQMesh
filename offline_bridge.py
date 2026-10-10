	
from flask import Flask, request, jsonify, render_template_string
import sqlite3
import uuid
from datetime import datetime, timezone

app = Flask(__name__)
DB = "resqmesh.db"

PAGE = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ResQMesh Offline SOS</title>
<style>
body { font-family: Arial; max-width: 520px; margin: 25px auto;
       padding: 16px; background: #0b1424; color: white; }
.card { background: #16253b; padding: 20px; border-radius: 14px; }
input, select, textarea, button {
  width: 100%; box-sizing: border-box; padding: 13px;
  margin: 8px 0; border-radius: 8px; font-size: 16px;
}
button { background: #e63950; color: white; border: 0; font-weight: bold; }
small { color: #b7c8dd; }
</style>
</head>
<body>
<div class="card">
<h1>🆘 ResQMesh</h1>
<h3>Offline emergency message</h3>
<p id="status">Checking local receiver...</p>
<form id="sos">
<label>Emergency type</label>
<select name="emergency">
<option>Trapped</option>
<option>Medical emergency</option>
<option>Food / Water</option>
<option>Evacuation</option>
<option>Safe</option>
</select>
<label>Your location</label>
<input name="location" required placeholder="Village or landmark">
<label>Details</label>
<textarea name="details" placeholder="People affected, injuries..."></textarea>
<button type="submit">SEND SOS</button>
</form>
<div id="result"></div>
</div>
<script>
fetch('/health')
 .then(r => r.json())
 .then(() => document.getElementById('status').textContent =
       'Connected to local ResQMesh receiver')
 .catch(() => document.getElementById('status').textContent =
       'Receiver unavailable');

document.getElementById('sos').addEventListener('submit', async e => {
  e.preventDefault();
  const result = document.getElementById('result');
  result.textContent = 'Sending...';
  try {
    const data = Object.fromEntries(new FormData(e.target).entries());
    const response = await fetch('/api/sos', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    });
    const reply = await response.json();
    if (!response.ok) throw new Error(reply.error || 'Send failed');
    result.textContent = 'Received by laptop! Message ID: ' + reply.id;
  } catch (err) {
    result.textContent = 'Not delivered: ' + err.message;
  }
});
</script>
</body>
</html>
"""


def initialize_db():
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS offline_messages (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                emergency TEXT NOT NULL,
                location TEXT NOT NULL,
                details TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'RECEIVED'
            )
        """)


@app.get("/")
def home():
    return render_template_string(PAGE)


@app.get("/health")
def health():
    return jsonify({"status": "ready"})


@app.post("/api/sos")
def receive_sos():
    data = request.get_json(silent=True) or {}
    emergency = str(data.get("emergency", "")).strip()
    location = str(data.get("location", "")).strip()
    details = str(data.get("details", "")).strip()

    allowed = {
        "Trapped", "Medical emergency", "Food / Water",
        "Evacuation", "Safe"
    }

    if emergency not in allowed or not location:
        return jsonify({"error": "Valid emergency and location required"}), 400

    message_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB) as con:
        con.execute("""
            INSERT INTO offline_messages
            (id, created_at, emergency, location, details, status)
            VALUES (?, ?, ?, ?, ?, 'RECEIVED')
        """, (message_id, created_at, emergency, location, details))

    print(f"\nSOS RECEIVED: {message_id}")
    print(f"Type: {emergency} | Location: {location}")
    print(f"Details: {details}\n")

    return jsonify({
        "id": message_id,
        "status": "RECEIVED",
        "saved": True
    })


@app.get("/api/messages")
def messages():
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("""
            SELECT * FROM offline_messages ORDER BY created_at DESC
        """).fetchall()
    return jsonify([dict(row) for row in rows])


if __name__ == "__main__":
    initialize_db()
    print("ResQMesh local receiver starting...")
    print("Open http://127.0.0.1:5000 on this laptop")
    app.run(host="0.0.0.0", port=5000, debug=False)