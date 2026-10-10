import sqlite3
from datetime import datetime

import streamlit as st

DB_NAME = "resqmesh.db"


def initialize_database():
    with sqlite3.connect(DB_NAME) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT,
                emergency TEXT NOT NULL,
                location TEXT NOT NULL,
                details TEXT
            )
        """)


initialize_database()

st.set_page_config(
    page_title="ResQMesh",
    page_icon="🆘",
    layout="wide"
)

st.title("🆘 ResQMesh")
st.subheader("Offline Disaster Rescue Network")
st.info(
    "Prototype stage: this version saves reports on this "
    "computer. It does not yet transmit SOS messages between phones."
)

tab_sos, tab_rescue = st.tabs(
    ["Send SOS", "Rescue Dashboard"]
)

with tab_sos:
    st.header("Emergency Request")

    with st.form("sos_form"):
        name = st.text_input("Your name (optional)")

        emergency = st.selectbox(
            "What help do you need?",
            [
                "Trapped",
                "Medical emergency",
                "Food / Water",
                "Evacuation",
                "Other",
                "Safe"
            ]
        )

        location = st.text_input(
            "Location or GPS coordinates",
            placeholder="Example: Village name or latitude, longitude"
        )

        details = st.text_area(
            "Additional details",
            placeholder="Number of people, injuries, nearby landmarks..."
        )

        submitted = st.form_submit_button(
            "🆘 Submit Emergency Report",
            type="primary",
            use_container_width=True
        )

        if submitted:
            if not location.strip():
                st.error("Please enter a location.")
            else:
                with sqlite3.connect(DB_NAME) as connection:
                    connection.execute(
                        """
                        INSERT INTO alerts
                        (created_at, name, emergency, location, details)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            datetime.now().isoformat(timespec="seconds"),
                            name.strip(),
                            emergency,
                            location.strip(),
                            details.strip()
                        )
                    )

                st.success(
                    "Report saved on this computer. "
                    "It has NOT been sent to rescue services."
                )

with tab_rescue:
    st.header("Rescue Team Dashboard")

    with sqlite3.connect(DB_NAME) as connection:
        connection.row_factory = sqlite3.Row
        reports = connection.execute(
            "SELECT * FROM alerts ORDER BY id DESC"
        ).fetchall()

    if not reports:
        st.info("No emergency reports yet. Submit a test SOS first.")
    else:
        st.metric("Total reports", len(reports))

        for report in reports:
            with st.container(border=True):
                st.markdown(
                    f"*#{report['id']} — {report['emergency']}*"
                )
                st.write("Time:", report["created_at"])
                st.write("Name:", report["name"] or "Not provided")
                st.write("Location:", report["location"])
                st.write("Details:", report["details"] or "None")
