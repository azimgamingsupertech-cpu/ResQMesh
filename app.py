
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
.stApp {
    background: #08111f;
    color: #eaf2ff;
}
[data-testid="stSidebar"] {
    background: #0c192b;
}
[data-testid="stMetric"] {
    background: #11243a;
    border: 1px solid #233d59;
    padding: 16px;
    border-radius: 12px;
}
div[data-testid="stForm"] {
    background: #102036;
    padding: 18px;
    border-radius: 12px;
}
h1, h2, h3 {
    color: #f1f6ff;
}
</style>
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