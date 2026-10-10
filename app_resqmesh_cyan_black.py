
import sqlite3
import uuid
from datetime import datetime

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

DB_NAME = "resqmesh.db"

st.set_page_config(
    page_title="ResQMesh Command Center",
    page_icon="🆘",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- DATABASE ----------

def connect_db():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT,
                emergency TEXT NOT NULL,
                location TEXT NOT NULL,
                details TEXT
            )
        """)

        columns = {
            row[1] for row in
            db.execute("PRAGMA table_info(alerts)").fetchall()
        }

        if "status" not in columns:
            db.execute(
                "ALTER TABLE alerts ADD COLUMN status "
                "TEXT NOT NULL DEFAULT 'Open'"
            )

        if "latitude" not in columns:
            db.execute("ALTER TABLE alerts ADD COLUMN latitude REAL")

        if "longitude" not in columns:
            db.execute("ALTER TABLE alerts ADD COLUMN longitude REAL")

        if "priority" not in columns:
            db.execute(
                "ALTER TABLE alerts ADD COLUMN priority "
                "TEXT NOT NULL DEFAULT 'High'"
            )


def load_alerts():
    with connect_db() as db:
        return pd.read_sql_query(
            "SELECT * FROM alerts ORDER BY id DESC", db
        )


def add_alert(name, emergency, location, details, lat, lon, priority):
    with connect_db() as db:
        db.execute("""
            INSERT INTO alerts
            (created_at, name, emergency, location, details,
             status, latitude, longitude, priority)
            VALUES (?, ?, ?, ?, ?, 'Open', ?, ?, ?)
        """, (
            datetime.now().isoformat(timespec="seconds"),
            name, emergency, location, details, lat, lon, priority
        ))


def update_status(alert_id, status):
    with connect_db() as db:
        db.execute(
            "UPDATE alerts SET status = ? WHERE id = ?",
            (status, int(alert_id))
        )


def seed_demo_data():
    # Clearly labeled fictional incidents around a sample Kerala region.
    examples = [
        ("Demo Victim A", "Trapped", "Demo Riverside",
         "Two people need evacuation.", 10.5276, 76.2144, "Critical"),
        ("Demo Victim B", "Medical emergency", "Demo Hill Area",
         "Urgent medical assistance requested.", 10.5350, 76.2250, "Critical"),
        ("Demo Victim C", "Food / Water", "Demo School Shelter",
         "Drinking water required.", 10.5150, 76.2050, "Medium"),
        ("Demo Victim D", "Evacuation", "Demo Bridge",
         "Family requesting evacuation.", 10.5450, 76.2000, "High"),
        ("Demo Victim E", "Safe", "Demo Community Hall",
         "Reporting safe at shelter.", 10.5200, 76.2300, "Low"),
    ]

    with connect_db() as db:
        for name, emergency, location, details, lat, lon, priority in examples:
            db.execute("""
                INSERT INTO alerts
                (created_at, name, emergency, location, details,
                 status, latitude, longitude, priority)
                VALUES (?, ?, ?, ?, ?, 'Open', ?, ?, ?)
            """, (
                datetime.now().isoformat(timespec="seconds"),
                name, emergency, location, details, lat, lon, priority
            ))


initialize_database()

# ---------- STYLING ----------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root {
  --rq-bg: #07111f;
  --rq-panel: rgba(15, 31, 52, .82);
  --rq-border: rgba(117, 173, 220, .20);
  --rq-cyan: #58e1f5;
  --rq-blue: #5c8dff;
  --rq-text: #eaf4ff;
  --rq-muted: #9db2c9;
}
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp {
  color: var(--rq-text);
  background:
    radial-gradient(ellipse at 8% 0%, rgba(23, 105, 158, .22), transparent 35%),
    radial-gradient(ellipse at 92% 12%, rgba(72, 77, 190, .17), transparent 32%),
    linear-gradient(145deg, #07111f 0%, #091729 48%, #07111f 100%);
}
.stApp:before {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  opacity: .16;
  background-image: linear-gradient(rgba(120,180,220,.09) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(120,180,220,.09) 1px, transparent 1px);
  background-size: 42px 42px;
  mask-image: linear-gradient(to bottom, black, transparent 82%);
}
[data-testid="stAppViewContainer"] { background: transparent; }
[data-testid="stHeader"] { background: rgba(7,17,31,.65); }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0b1b2e 0%, #081421 100%);
  border-right: 1px solid var(--rq-border);
}
[data-testid="stSidebar"] > div { padding-top: 1.25rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { border-radius: 10px; }
[data-testid="stMetric"] {
  background: linear-gradient(145deg, rgba(21,44,70,.94), rgba(12,28,47,.94));
  border: 1px solid var(--rq-border); padding: 20px 20px 17px;
  border-radius: 18px; box-shadow: 0 10px 30px rgba(0,0,0,.14);
  transition: transform .22s ease, border-color .22s ease, box-shadow .22s ease;
  animation: rq-rise .65s ease both;
}
[data-testid="stMetric"]:hover { transform: translateY(-4px); border-color: rgba(88,225,245,.55); box-shadow: 0 14px 34px rgba(0,0,0,.24); }
[data-testid="stMetricLabel"] { color: #9eb6cf !important; letter-spacing: .09em; font-size: .73rem; font-weight: 700; }
[data-testid="stMetricValue"] { color: #f4f9ff !important; font-family: 'Space Grotesk', sans-serif; }
div[data-testid="stForm"], [data-testid="stExpander"] {
  background: rgba(13, 30, 50, .78); border: 1px solid var(--rq-border);
  border-radius: 18px; padding: 12px; box-shadow: 0 12px 32px rgba(0,0,0,.12);
}
.stButton > button, [data-testid="stFormSubmitButton"] > button {
  border: 1px solid rgba(88,225,245,.42); border-radius: 12px;
  background: linear-gradient(115deg, #126b91, #3159a9); color: white;
  font-weight: 700; transition: transform .2s ease, box-shadow .2s ease, filter .2s ease;
  box-shadow: 0 5px 18px rgba(27,117,171,.16);
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
  transform: translateY(-2px); filter: brightness(1.12);
  box-shadow: 0 9px 24px rgba(47,160,220,.25); border-color: var(--rq-cyan);
}
.stButton > button:active { transform: translateY(0) scale(.99); }
input, textarea, [data-baseweb="select"] > div {
  background-color: rgba(7, 19, 33, .82) !important;
  border-color: rgba(117,173,220,.25) !important; border-radius: 10px !important;
}
[data-testid="stDataFrame"], [data-testid="stPlotlyChart"], iframe {
  border: 1px solid var(--rq-border); border-radius: 16px; overflow: hidden;
}
h1, h2, h3 { color: #f2f7ff; font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -.025em; }
h1 { font-size: clamp(1.9rem, 3vw, 2.65rem) !important; }
h2 { margin-top: .4rem; }
p, [data-testid="stCaptionContainer"] { color: var(--rq-muted); }
hr { border-color: rgba(117,173,220,.18); }
[data-testid="stAlert"] { border-radius: 13px; }
.rq-hero {
  position: relative; overflow: hidden; isolation: isolate;
  padding: 25px 28px; margin: 4px 0 24px;
  border: 1px solid rgba(88,225,245,.26); border-radius: 22px;
  background: linear-gradient(115deg, rgba(13,42,66,.96), rgba(20,34,69,.91) 58%, rgba(20,43,62,.9));
  box-shadow: 0 18px 55px rgba(0,0,0,.2);
  animation: rq-rise .7s cubic-bezier(.2,.75,.25,1) both;
}
.rq-hero:before {
  content: ""; position: absolute; z-index: -1; width: 330px; height: 330px;
  right: -85px; top: -190px; border-radius: 50%;
  background: radial-gradient(circle, rgba(88,225,245,.28), rgba(92,141,255,.06) 60%, transparent 70%);
  animation: rq-breathe 5s ease-in-out infinite alternate;
}
.rq-hero:after {
  content: ""; position: absolute; z-index: -1; right: 25%; top: -70%; width: 1px; height: 240%;
  background: linear-gradient(transparent, rgba(88,225,245,.18), transparent); transform: rotate(32deg);
}
.rq-eyebrow { color: #78e7f7; font-size: .72rem; font-weight: 700; letter-spacing: .19em; text-transform: uppercase; }
.rq-hero-title { color: #f4f8ff; font: 700 clamp(1.55rem, 3vw, 2.35rem)/1.15 'Space Grotesk', sans-serif; margin: 8px 0 9px; }
.rq-hero-copy { color: #b8cde2; font-size: .95rem; max-width: 720px; }
.rq-status { display: inline-flex; align-items: center; gap: 9px; margin-top: 14px; padding: 7px 11px; border: 1px solid rgba(92,230,177,.25); border-radius: 999px; background: rgba(18,125,94,.13); color: #9df0ce; font-size: .75rem; font-weight: 700; letter-spacing: .04em; }
.rq-pulse { width: 7px; height: 7px; border-radius: 50%; background: #54e6a8; box-shadow: 0 0 0 0 rgba(84,230,168,.6); animation: rq-pulse 1.8s infinite; }
@keyframes rq-pulse { 0% { box-shadow: 0 0 0 0 rgba(84,230,168,.55); } 70% { box-shadow: 0 0 0 8px rgba(84,230,168,0); } 100% { box-shadow: 0 0 0 0 rgba(84,230,168,0); } }
@keyframes rq-breathe { from { transform: translate3d(-8px,8px,0) scale(.92); opacity: .65; } to { transform: translate3d(8px,-5px,0) scale(1.08); opacity: 1; } }
@keyframes rq-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@media (prefers-reduced-motion: reduce) { *, *:before, *:after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; scroll-behavior: auto !important; } }

/* ---------- RESQmesh VISUAL UPGRADE ---------- */
.stApp {
  background:
    radial-gradient(ellipse at 4% 8%, rgba(0, 221, 255, .15), transparent 30%),
    radial-gradient(ellipse at 95% 22%, rgba(127, 72, 255, .17), transparent 33%),
    linear-gradient(135deg, #050b16 0%, #0a1830 48%, #07101f 100%) !important;
}
[data-testid="stAppViewContainer"] .main .block-container {
  max-width: 1600px;
  padding-top: 1.6rem;
  padding-bottom: 3rem;
}
.rq-hero {
  min-height: 220px;
  padding: 34px 38px;
  margin: 8px 0 30px;
  border: 1px solid rgba(87, 226, 255, .45);
  border-radius: 26px;
  background:
    linear-gradient(110deg, rgba(5, 25, 47, .97), rgba(15, 36, 77, .94) 56%, rgba(25, 27, 73, .92));
  box-shadow: 0 24px 70px rgba(0, 0, 0, .34), inset 0 1px 0 rgba(255,255,255,.06);
}
.rq-hero-title {
  max-width: 900px;
  font-size: clamp(2rem, 4vw, 3.3rem);
  letter-spacing: -.045em;
  text-shadow: 0 0 32px rgba(88, 225, 245, .15);
}
.rq-hero-copy { max-width: 800px; font-size: 1rem; line-height: 1.7; }
.rq-eyebrow { display: inline-block; padding: 7px 11px; border-radius: 7px; background: rgba(88,225,245,.09); border: 1px solid rgba(88,225,245,.2); }
[data-testid="stMetric"] {
  min-height: 130px;
  position: relative;
  overflow: hidden;
  background: linear-gradient(145deg, rgba(18, 43, 73, .98), rgba(9, 23, 42, .98)) !important;
  border: 1px solid rgba(105, 187, 235, .27) !important;
  border-radius: 20px !important;
  box-shadow: 0 15px 35px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.035);
}
[data-testid="stMetric"]:after {
  content: "";
  position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: linear-gradient(180deg, #53e5f5, #637bff);
}
[data-testid="stMetricValue"] { font-size: clamp(1.8rem, 2.4vw, 2.7rem) !important; letter-spacing: -.04em; }
[data-testid="stMetric"]:hover { transform: translateY(-5px); border-color: rgba(88,225,245,.75) !important; box-shadow: 0 20px 44px rgba(0,0,0,.32), 0 0 25px rgba(36,176,229,.09); }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #081a30 0%, #07111f 70%, #0a1226 100%) !important;
  border-right: 1px solid rgba(88,225,245,.22);
}
[data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: 7px; }
[data-testid="stSidebar"] [data-testid="stRadio"] label {
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 12px;
  transition: all .2s ease;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
  background: rgba(88,225,245,.09);
  border-color: rgba(88,225,245,.22);
}
h1, h2, h3 { letter-spacing: -.035em !important; }
h2, h3 { padding-bottom: 5px; }
[data-testid="stAlert"] { border-radius: 14px; border-width: 1px; }
[data-testid="stPlotlyChart"], iframe {
  box-shadow: 0 15px 35px rgba(0,0,0,.17);
}
div[data-testid="stForm"], [data-testid="stExpander"], [data-testid="stDataFrame"] {
  border-color: rgba(105,187,235,.24) !important;
  border-radius: 18px !important;
}
.stButton > button, [data-testid="stFormSubmitButton"] > button {
  min-height: 44px;
  letter-spacing: .01em;
}
[data-testid="stDataFrame"] { background: rgba(8,20,36,.65); }
@keyframes rq-grid-shift { from { background-position: 0 0, 0 0; } to { background-position: 42px 42px, 42px 42px; } }
.stApp:before { animation: rq-grid-shift 18s linear infinite; }
@media (max-width: 768px) {
  .rq-hero { padding: 23px 20px; min-height: unset; }
  .rq-hero-title { font-size: 1.9rem; }
  [data-testid="stMetric"] { min-height: 105px; padding: 15px !important; }
}


/* RESQMESH VISUAL OVERHAUL — intentionally high contrast */
:root {
  --rq-bg: #edf3f8;
  --rq-panel: #ffffff;
  --rq-border: #d5e0eb;
  --rq-cyan: #007f99;
  --rq-blue: #2457d6;
  --rq-text: #12243a;
  --rq-muted: #53677d;
}
.stApp {
  color: #12243a !important;
  background: #edf3f8 !important;
}
.stApp:before { display: none !important; }
[data-testid="stAppViewContainer"], section.main, .main .block-container {
  background: #edf3f8 !important;
}
.main .block-container {
  max-width: 1600px !important;
  padding-top: 1.3rem !important;
  padding-left: 2.2rem !important;
  padding-right: 2.2rem !important;
}
[data-testid="stHeader"] { background: #edf3f8 !important; }
[data-testid="stSidebar"] {
  background: #101f33 !important;
  border-right: 4px solid #ef4444 !important;
}
[data-testid="stSidebar"] * { color: #edf6ff !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label {
  background: #1b3049;
  border: 1px solid #314862;
  padding: 11px 13px;
  margin: 5px 0;
  border-radius: 10px;
  transition: .2s ease;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
  background: #263f5d;
  border-color: #38d9ef;
  transform: translateX(4px);
}
.rq-hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(115deg, #101f33 0%, #173e60 58%, #006c81 100%) !important;
  border: none !important;
  border-left: 8px solid #ef4444 !important;
  border-radius: 22px !important;
  padding: 35px 38px !important;
  margin: 0 0 28px !important;
  min-height: 220px !important;
  box-shadow: 0 18px 45px rgba(17, 39, 64, .2) !important;
}
.rq-hero:after {
  content: "SOS";
  position: absolute;
  right: 36px;
  top: 28px;
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  font-size: clamp(3.5rem, 8vw, 7.2rem);
  letter-spacing: -.08em;
  color: rgba(255,255,255,.09);
  line-height: 1;
  pointer-events: none;
}
.rq-eyebrow {
  color: #6ff0ff !important;
  font-size: .82rem !important;
  letter-spacing: .19em !important;
  font-weight: 800 !important;
}
.rq-hero-title {
  color: #ffffff !important;
  max-width: 780px;
  font-size: clamp(2.1rem, 4vw, 3.5rem) !important;
  line-height: 1.06 !important;
  letter-spacing: -.045em !important;
}
.rq-hero-copy {
  color: #d8e9f8 !important;
  max-width: 720px;
  font-size: 1.03rem !important;
  line-height: 1.7 !important;
}
.rq-status {
  display: inline-flex !important;
  background: rgba(2, 14, 28, .48) !important;
  border: 1px solid rgba(111,240,255,.4) !important;
  padding: 9px 13px !important;
  border-radius: 999px !important;
  color: #dffbff !important;
  margin-top: 14px !important;
}
h1, h2, h3, [data-testid="stHeader"] * {
  color: #12243a !important;
  font-family: 'Space Grotesk', sans-serif !important;
}
h1 { font-size: 2.2rem !important; letter-spacing: -.04em !important; }
h2, h3 { letter-spacing: -.025em !important; }
p, label, .stCaption, [data-testid="stMarkdownContainer"] {
  color: #30465d;
}
[data-testid="stMetric"] {
  background: #ffffff !important;
  border: 1px solid #d5e0eb !important;
  border-top: 5px solid #0787a1 !important;
  border-radius: 16px !important;
  padding: 20px 20px 18px !important;
  min-height: 138px;
  box-shadow: 0 8px 22px rgba(25, 48, 75, .07) !important;
  animation: rq-rise .55s ease both;
}
[data-testid="stMetric"]:nth-child(1) { border-top-color: #0787a1 !important; }
[data-testid="stMetricLabel"] { color: #60748a !important; font-size: .78rem !important; letter-spacing: .11em !important; }
[data-testid="stMetricValue"] { color: #12243a !important; font-size: 2.5rem !important; font-weight: 800 !important; }
div[data-testid="stForm"], [data-testid="stExpander"] {
  background: #ffffff !important;
  border: 1px solid #d5e0eb !important;
  border-radius: 16px !important;
  padding: 18px !important;
  box-shadow: 0 8px 22px rgba(25,48,75,.06) !important;
}
[data-testid="stDataFrame"], [data-testid="stPlotlyChart"], iframe {
  border: 1px solid #d5e0eb !important;
  border-radius: 14px !important;
  overflow: hidden !important;
  box-shadow: 0 7px 20px rgba(25,48,75,.06) !important;
}
.stButton > button, [data-testid="stFormSubmitButton"] > button {
  background: linear-gradient(110deg, #e83d4f, #bd2039) !important;
  color: #ffffff !important;
  border: 0 !important;
  border-radius: 10px !important;
  padding: .68rem 1.2rem !important;
  font-weight: 800 !important;
  box-shadow: 0 7px 16px rgba(232,61,79,.22) !important;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
  filter: brightness(1.08) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 10px 22px rgba(232,61,79,.3) !important;
}
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input, [data-testid="stSelectbox"] > div,
[data-baseweb="select"] > div {
  background: #ffffff !important;
  color: #12243a !important;
  border-color: #c8d5e3 !important;
  border-radius: 9px !important;
}
[data-testid="stAlert"] { border-radius: 12px !important; }
hr { border-color: #d5e0eb !important; }
@media (max-width: 768px) {
  .main .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
  .rq-hero { padding: 24px 20px !important; }
  .rq-hero:after { right: 15px; top: 15px; font-size: 3.5rem; }
  [data-testid="stMetric"] { min-height: 100px; }
}


/* RESQMESH CYAN + BLACK THEME */
:root {
  --rq-bg: #020607;
  --rq-panel: rgba(4, 24, 28, .94);
  --rq-border: rgba(0, 240, 255, .38);
  --rq-cyan: #00f0ff;
  --rq-blue: #00aebe;
  --rq-text: #eaffff;
  --rq-muted: #9bc9cd;
}
.stApp {
  color: var(--rq-text) !important;
  background:
    radial-gradient(ellipse at 12% 5%, rgba(0, 240, 255, .30), transparent 38%),
    radial-gradient(ellipse at 88% 42%, rgba(0, 155, 175, .18), transparent 36%),
    linear-gradient(135deg, #000304 0%, #03191d 42%, #020607 72%, #001216 100%) !important;
}
[data-testid="stAppViewContainer"] { background: transparent !important; }
[data-testid="stHeader"] { background: rgba(0, 8, 10, .82) !important; }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #04272c 0%, #010809 88%) !important;
  border-right: 1px solid rgba(0, 240, 255, .45) !important;
}
[data-testid="stMetric"] {
  background: linear-gradient(145deg, rgba(4, 42, 48, .97), rgba(2, 15, 18, .98)) !important;
  border: 1px solid rgba(0, 240, 255, .42) !important;
  box-shadow: 0 8px 28px rgba(0, 0, 0, .34), inset 0 1px 0 rgba(0, 240, 255, .08) !important;
}
[data-testid="stMetric"]:hover {
  border-color: #00f0ff !important;
  box-shadow: 0 0 24px rgba(0, 240, 255, .19) !important;
}
div[data-testid="stForm"], [data-testid="stExpander"] {
  background: linear-gradient(145deg, rgba(3, 31, 35, .96), rgba(1, 12, 15, .97)) !important;
  border: 1px solid rgba(0, 240, 255, .30) !important;
}
.rq-hero {
  background: linear-gradient(115deg, rgba(0, 49, 56, .98), rgba(1, 19, 23, .98) 62%, rgba(0, 65, 72, .95)) !important;
  border: 1px solid rgba(0, 240, 255, .58) !important;
  box-shadow: 0 0 30px rgba(0, 240, 255, .10), 0 18px 55px rgba(0, 0, 0, .5) !important;
}
.rq-eyebrow { color: #00f0ff !important; }
.stButton > button, [data-testid="stFormSubmitButton"] > button {
  background: linear-gradient(115deg, #00aebe, #00636d) !important;
  border: 1px solid #00f0ff !important;
  color: #f0ffff !important;
  box-shadow: 0 0 16px rgba(0, 240, 255, .14) !important;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
  background: linear-gradient(115deg, #00d9e8, #008b99) !important;
  box-shadow: 0 0 22px rgba(0, 240, 255, .30) !important;
}
input, textarea, [data-baseweb="select"] > div {
  background-color: rgba(0, 12, 15, .96) !important;
  border-color: rgba(0, 240, 255, .34) !important;
}
h1, h2, h3 { color: #eaffff !important; }

</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="rq-hero">
  <div class="rq-eyebrow">ResQMesh · Emergency response network</div>
  <div class="rq-hero-title">When networks go down, response moves on.</div>
  <div class="rq-hero-copy">A local-first disaster response command center for organizing SOS reports, tracking incidents, and demonstrating resilient store-and-forward coordination.</div>
  <div class="rq-status"><span class="rq-pulse"></span> LOCAL DASHBOARD ACTIVE · PROTOTYPE MODE</div>
</div>
""", unsafe_allow_html=True)

# ---------- SIDEBAR ----------

with st.sidebar:
    st.markdown("# 🆘 ResQMesh")
    st.caption("OFFLINE DISASTER RESPONSE")
    st.success("LOCAL MODE · Database available")
    st.markdown("---")

    page = st.radio(
        "NAVIGATION",
        [
            "Command Center",
            "Report Emergency",
            "Incident Management",
            "Mesh Simulator",
        ],
    )

    st.markdown("---")
    st.caption("Prototype status")
    st.write("🟢 Local database")
    st.write("🟡 Mesh network simulated")
    st.write("⚪ Physical device relay not connected")
    st.caption("ResQMesh prototype v2.0")


# ---------- DATA + PRIORITY ----------

df = load_alerts()

PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

if not df.empty:
    df["priority_rank"] = (
        df["priority"].map(PRIORITY_ORDER).fillna(4)
    )
    df = df.sort_values(
        ["priority_rank", "id"], ascending=[True, False]
    )

# ---------- COMMAND CENTER ----------

if page == "Command Center":
    st.title("Rescue Command Center")
    st.caption(
        "Monitor emergency reports, prioritize incidents and coordinate response."
    )

    st.info(
        "DEMO MODE: map locations marked as demo are fictional. "
        "This dashboard does not contact real rescue services."
    )

    total = len(df)
    open_count = int((df["status"] == "Open").sum()) if total else 0
    critical_count = (
        int(((df["priority"] == "Critical") &
             (df["status"] != "Resolved")).sum())
        if total else 0
    )
    resolved_count = (
        int((df["status"] == "Resolved").sum()) if total else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TOTAL REPORTS", total)
    c2.metric("OPEN REPORTS", open_count)
    c3.metric("CRITICAL OPEN", critical_count)
    c4.metric("RESOLVED", resolved_count)

    left, right = st.columns([1.65, 1])

    with left:
        st.subheader("📍 Incident Map")

        m = folium.Map(
            location=[10.5276, 76.2144],
            zoom_start=12,
            tiles="OpenStreetMap",
        )

        if not df.empty:
            mapped = df.dropna(subset=["latitude", "longitude"])

            colors = {
                "Critical": "red",
                "High": "orange",
                "Medium": "blue",
                "Low": "green",
            }

            for _, row in mapped.iterrows():
                popup = (
                    f"Report #{row['id']} | {row['emergency']} | "
                    f"{row['priority']} | {row['status']}"
                )
                folium.Marker(
                    [row["latitude"], row["longitude"]],
                    tooltip=f"{row['priority']}: {row['emergency']}",
                    popup=popup,
                    icon=folium.Icon(
                        color=colors.get(row["priority"], "gray"),
                        icon="info-sign",
                    ),
                ).add_to(m)

        st_folium(m, height=460, use_container_width=True)

        st.caption(
            "Map tiles may require internet. Reports without verified "
            "coordinates are not placed on the map."
        )

    with right:
        st.subheader("🚨 Priority Overview")

        if total:
            chart_df = df["priority"].value_counts().rename_axis(
                "Priority"
            ).reset_index(name="Reports")

            fig = px.bar(
                chart_df,
                x="Priority",
                y="Reports",
                color="Priority",
                color_discrete_map={
                    "Critical": "#ff4057",
                    "High": "#ff9638",
                    "Medium": "#3498ff",
                    "Low": "#20bd83",
                },
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                margin=dict(l=5, r=5, t=20, b=5),
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Latest Reports")
            for _, row in df.head(5).iterrows():
                st.markdown(
                    f"**#{row['id']} · {row['emergency']}**  \n"
                    f"{row['location']} · {row['priority']} · "
                    f"{row['status']}"
                )
                st.divider()
        else:
            st.info("No reports yet. Add demo data or submit an SOS.")

    with st.expander("Demo controls"):
        st.write(
            "Add fictional incidents to demonstrate the map and "
            "priority system to hackathon judges."
        )
        if st.button("Load sample disaster reports"):
            seed_demo_data()
            st.success("Fictional demo reports added.")
            st.rerun()

        if st.button("Refresh dashboard"):
            st.rerun()


# ---------- REPORT EMERGENCY ----------

elif page == "Report Emergency":
    st.title("🆘 Submit an Emergency Report")
    st.write("Enter a request for the local prototype database.")

    with st.form("emergency_form", clear_on_submit=True):
        name = st.text_input("Name (optional)")

        emergency = st.selectbox(
            "Emergency type",
            [
                "Trapped",
                "Medical emergency",
                "Food / Water",
                "Evacuation",
                "Other",
                "Safe",
            ],
        )

        priority_default = (
            "Critical" if emergency in ["Trapped", "Medical emergency"]
            else "Low" if emergency == "Safe"
            else "High" if emergency == "Evacuation"
            else "Medium"
        )

        priority = st.selectbox(
            "Requested priority",
            ["Critical", "High", "Medium", "Low"],
            index=["Critical", "High", "Medium", "Low"].index(
                priority_default
            ),
        )

        location = st.text_input(
            "Location / landmark",
            placeholder="Village, street or shelter name",
        )

        lat_text = st.text_input(
            "Latitude (optional)",
            placeholder="Example: 10.5276",
        )

        lon_text = st.text_input(
            "Longitude (optional)",
            placeholder="Example: 76.2144",
        )

        details = st.text_area(
            "Situation details",
            placeholder="Number of people, injuries, immediate risks...",
        )

        submitted = st.form_submit_button(
            "Save SOS Report",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            if not location.strip():
                st.error("Enter a location or nearby landmark.")
            else:
                try:
                    lat = float(lat_text) if lat_text.strip() else None
                    lon = float(lon_text) if lon_text.strip() else None

                    if (lat is None) != (lon is None):
                        raise ValueError(
                            "Enter both latitude and longitude, or leave both blank."
                        )

                    if lat is not None and not (
                        -90 <= lat <= 90 and -180 <= lon <= 180
                    ):
                        raise ValueError("Coordinates are outside valid ranges.")

                    if emergency == "Safe":
                        priority = "Low"

                    add_alert(
                        name.strip(),
                        emergency,
                        location.strip(),
                        details.strip(),
                        lat,
                        lon,
                        priority,
                    )
                    st.success(
                        "Report saved locally. It has NOT been transmitted "
                        "to rescuers."
                    )
                except ValueError as error:
                    st.error(str(error))


# ---------- INCIDENT MANAGEMENT ----------

elif page == "Incident Management":
    st.title("📋 Incident Management")
    st.caption("Review reports and update their local status.")

    if df.empty:
        st.info("No incidents available. Submit a report or load demo data.")
    else:
        status_filter = st.selectbox(
            "Filter by status",
            ["All", "Open", "In Progress", "Resolved"],
        )

        view_df = df.copy()
        if status_filter != "All":
            view_df = view_df[view_df["status"] == status_filter]

        st.dataframe(
            view_df[
                [
                    "id", "created_at", "emergency", "priority",
                    "location", "status", "details"
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Update a report")
        ids = df["id"].astype(int).tolist()

        with st.form("update_status_form"):
            selected_id = st.selectbox("Report ID", ids)
            new_status = st.selectbox(
                "New status",
                ["Open", "In Progress", "Resolved"],
            )

            update = st.form_submit_button("Update status")

            if update:
                update_status(selected_id, new_status)
                st.success(f"Report #{selected_id} updated.")
                st.rerun()


# ---------- MESH NETWORK SIMULATOR ----------

elif page == "Mesh Simulator":
    st.title("📡 Mesh Network Lab")
    st.caption("Demonstrate store-and-forward routing with simulated devices.")

    st.warning(
        "SIMULATION ONLY: these virtual devices do not communicate with "
        "real phones. Physical Bluetooth/Wi-Fi relay will be a later milestone."
    )

    nodes = [
        "Victim Phone A",
        "Volunteer Phone B",
        "Volunteer Phone C",
        "Rescue Station",
    ]

    st.subheader("Virtual device network")
    st.graphviz_chart("""
    graph G {
        layout=neato;
        overlap=false;
        bgcolor="transparent";
        node [shape=box, style="rounded,filled",
              fillcolor="#12314b", fontcolor="white",
              color="#35b8f4"];
        edge [color="#20bd83", penwidth=2];
        "Victim A" -- "Volunteer B";
        "Volunteer B" -- "Volunteer C";
        "Volunteer C" -- "Rescue Station";
        "Victim A" -- "Volunteer C";
    }
    """)

    if "mesh_messages" not in st.session_state:
        st.session_state.mesh_messages = []

    st.subheader("Send a simulated SOS")
    with st.form("mesh_form"):
        source = st.selectbox("Sending device", nodes[:3])
        message_type = st.selectbox(
            "Message type",
            ["Trapped", "Medical emergency", "Food / Water", "Evacuation"],
        )
        destination = st.selectbox("Destination", nodes[3:])
        send = st.form_submit_button("Simulate relay")

        if send:
            route_options = {
                "Victim Phone A": [
                    "Victim Phone A",
                    "Volunteer Phone B",
                    "Volunteer Phone C",
                    "Rescue Station",
                ],
                "Volunteer Phone B": [
                    "Volunteer Phone B",
                    "Volunteer Phone C",
                    "Rescue Station",
                ],
                "Volunteer Phone C": [
                    "Volunteer Phone C",
                    "Rescue Station",
                ],
            }

            route = route_options[source]
            st.session_state.mesh_messages.insert(0, {
                "id": str(uuid.uuid4())[:8].upper(),
                "type": message_type,
                "source": source,
                "destination": destination,
                "route": route,
                "hops": len(route) - 1,
                "status": "Simulated delivery",
                "time": datetime.now().strftime("%H:%M:%S"),
            })

    for message in st.session_state.mesh_messages:
        with st.container(border=True):
            st.markdown(
                f"**SOS-{message['id']} · {message['type']}**"
            )
            st.write("Route:", " → ".join(message["route"]))
            st.write("Relay hops:", message["hops"])
            st.write("Status:", message["status"])
            st.caption(
                f"{message['source']} → {message['destination']} "
                f"at {message['time']}"
            )

    if st.button("Clear simulation history"):
        st.session_state.mesh_messages = []
        st.rerun()

st.markdown("---")
st.caption(
    "ResQMesh is a hackathon prototype, not a certified emergency service. "
    "Do not rely on it for real-life rescue."
)

# ---------- REAL OFFLINE SOS INBOX ----------
from streamlit_autorefresh import st_autorefresh
import sqlite3
import pandas as pd
import streamlit as st
st_autorefresh(
    interval=5000,
    limit=None,
    key="resqmesh_sos_refresh"
)

st.header("📡 Incoming Offline SOS Messages")

if st.button("🔄 Refresh SOS Inbox"):
    st.rerun()

try:
    with sqlite3.connect("resqmesh.db") as con:
        messages = pd.read_sql_query(
            """
            SELECT
                created_at AS 'Time (UTC)',
                emergency AS 'Emergency',
                location AS 'Location',
                details AS 'Details',
                status AS 'Status',
                id AS 'Message ID'
            FROM offline_messages
            ORDER BY created_at DESC
            """,
            con
        )

    if messages.empty:
        st.info("No SOS messages received yet.")
    else:
        st.success(f"{len(messages)} SOS message(s) received")
        st.dataframe(messages, use_container_width=True)

except Exception as error:
    st.warning(f"Could not load the SOS inbox: {error}")