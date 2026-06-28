import streamlit as st
import psycopg2
import uuid
import json
from datetime import datetime, timedelta
from streamlit_calendar import calendar

st.set_page_config(page_title="Multi Calendar", page_icon="📅", layout="wide")
st.title("📅 Multi Calendar")

# ====================== Database ======================
def get_db_connection():
    if 'db_conn' not in st.session_state:
        conn = psycopg2.connect(
            "postgresql://neondb_owner:npg_Zf2b3FjPdnvh@ep-frosty-fog-at6gioza-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require",
            connect_timeout=15
        )
        conn.set_session(autocommit=True)
        st.session_state.db_conn = conn
    return st.session_state.db_conn

def get_cursor():
    return get_db_connection().cursor()

def init_db():
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                start TEXT NOT NULL,
                "end" TEXT,
                color TEXT,
                resourceId TEXT,
                extended_props TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                building TEXT,
                color TEXT
            )
        """)

# ... (load_resources, save_resource, load_events, save_event, delete_event same as before)

def save_event(event: dict):
    extended = {k: v for k, v in event.items() if k not in ['id','title','start','end','color','resourceId']}
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO events (id, title, start, "end", color, resourceId, extended_props)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title=EXCLUDED.title, start=EXCLUDED.start, "end"=EXCLUDED."end",
                color=EXCLUDED.color, resourceId=EXCLUDED.resourceId, extended_props=EXCLUDED.extended_props
        """, (
            event.get("id", str(uuid.uuid4())),
            event["title"],
            event["start"],
            event.get("end"),
            event.get("color"),
            event.get("resourceId"),
            json.dumps(extended) if extended else None
        ))

# Init
init_db()
if "resources" not in st.session_state:
    st.session_state.resources = load_resources()
if "events" not in st.session_state:
    st.session_state.events = load_events()

# Sidebar Add Event (same)
with st.sidebar:
    # ... resources management
    st.header("➕ Add Event")
    with st.form("add_event", clear_on_submit=True):
        title = st.text_input("Title *")
        address = st.text_input("Address / Location")
        notes = st.text_area("Notes")
        # date, time, resource, recurrence
        if st.form_submit_button("Save Event"):
            if title:
                base = {
                    "title": title,
                    "start": f"{sdate}T{stime}",
                    "end": f"{edate}T{etime}",
                    "resourceId": resourceId,
                    "color": next((r["color"] for r in st.session_state.resources if r["id"] == resourceId), "#3788d8")
                }
                if address: base["address"] = address
                if notes: base["notes"] = notes
                save_event(base)
                st.session_state.events = load_events()
                st.success("Saved!")
                st.rerun()

# Calendar (same)
state = calendar( ... )

# FIXED DISPLAY
if state.get("eventClick"):
    ev = state["eventClick"]["event"]
    st.subheader(f"✏️ {ev.get('title', 'Event')}")
    
    st.write(f"**Start:** {ev.get('start')}")
    st.write(f"**End:** {ev.get('end')}")
    st.write(f"**Location:** {ev.get('address', 'Not set')}")
    if ev.get("notes"):
        st.write(f"**Notes:** {ev['notes']}")
    
    # Debug (remove later)
    st.expander("Debug - Raw Event Data").json(ev)
    
    with st.form("edit_event"):
        new_title = st.text_input("Title", ev.get("title", ""))
        new_address = st.text_input("Address", ev.get("address", ""))
        new_notes = st.text_area("Notes", ev.get("notes", ""))
        if st.form_submit_button("Save Changes"):
            updated = ev.copy()
            updated["title"] = new_title
            updated["address"] = new_address
            updated["notes"] = new_notes
            save_event(updated)
            st.session_state.events = load_events()
            st.success("Updated!")
            st.rerun()
        if st.form_submit_button("Delete", type="primary"):
            delete_event(ev["id"])
            st.session_state.events = load_events()
            st.success("Deleted!")
            st.rerun()
