import streamlit as st
import psycopg2
import uuid
import json
from datetime import datetime, timedelta
from streamlit_calendar import calendar

st.set_page_config(page_title="Multi Calendar", page_icon="📅", layout="wide")

# ====================== Database Connection ======================
def get_db_connection():
    if 'db_conn' not in st.session_state:
        try:
            conn = psycopg2.connect(
                "postgresql://neondb_owner:npg_Zf2b3FjPdnvh@ep-frosty-fog-at6gioza-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require",
                connect_timeout=15
            )
            conn.set_session(autocommit=True)
            st.session_state.db_conn = conn
        except Exception as e:
            st.error(f"Failed to connect to Neon: {e}")
            st.stop()
    return st.session_state.db_conn

def get_cursor():
    return get_db_connection().cursor()

def init_db():
    try:
        with get_cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    start TEXT NOT NULL,
                    "end" TEXT,
                    color TEXT DEFAULT '#3788d8',
                    resourceId TEXT,
                    extended_props TEXT
                )
            """)
    except Exception as e:
        st.warning(f"Init warning: {e}")

def load_events():
    try:
        with get_cursor() as cur:
            cur.execute("SELECT * FROM events ORDER BY start")
            rows = cur.fetchall()
        events = []
        for row in rows:
            event = {
                "id": row[0],
                "title": row[1],
                "start": row[2],
                "color": row[4],
                "resourceId": row[5],
            }
            if row[3]: event["end"] = row[3]
            if row[6]: event.update(json.loads(row[6]))
            events.append(event)
        return events
    except:
        return []

def save_event(event: dict):
    extended = {k: v for k, v in event.items() if k not in ['id','title','start','end','color','resourceId']}
    try:
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO events (id, title, start, "end", color, resourceId, extended_props)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    start = EXCLUDED.start,
                    "end" = EXCLUDED."end",
                    color = EXCLUDED.color,
                    resourceId = EXCLUDED.resourceId,
                    extended_props = EXCLUDED.extended_props
            """, (
                event.get("id", str(uuid.uuid4())),
                event["title"],
                event["start"],
                event.get("end"),
                event.get("color", "#3788d8"),
                event.get("resourceId"),
                json.dumps(extended) if extended else None
            ))
    except Exception as e:
        st.error(f"Save failed: {e}")

def delete_event(event_id: str):
    try:
        with get_cursor() as cur:
            cur.execute("DELETE FROM events WHERE id = %s", (event_id,))
    except Exception as e:
        st.error(f"Delete failed: {e}")

# ====================== Init ======================
init_db()

if "events" not in st.session_state:
    st.session_state.events = load_events()

# ====================== Sidebar Add Event ======================
with st.sidebar:
    st.header("📅 My Calendar")
    st.subheader("➕ Add Event")
    with st.form("add_event", clear_on_submit=True):
        title = st.text_input("Title *")
        col1, col2 = st.columns(2)
        with col1:
            sdate = st.date_input("Start Date")
            stime = st.time_input("Start Time", datetime.strptime("09:00", "%H:%M").time())
        with col2:
            edate = st.date_input("End Date", sdate)
            etime = st.time_input("End Time", datetime.strptime("10:00", "%H:%M").time())
        
        color = st.color_picker("Color", "#FF4B4B")
        resourceId = st.selectbox("Resource", ["a","b","c","d","e","f"])
        recurrence = st.selectbox("Recurrence", ["None", "Daily", "Weekly", "Monthly"])
        
        if st.form_submit_button("Save Event"):
            if title:
                base = {
                    "title": title,
                    "start": f"{sdate}T{stime}",
                    "end": f"{edate}T{etime}",
                    "color": color,
                    "resourceId": resourceId
                }
                if recurrence != "None":
                    base["recurrence"] = {"type": recurrence.lower()}
                save_event(base)
                st.session_state.events = load_events()
                st.success("✅ Saved!")
                st.rerun()

# ====================== Calendar ======================
calendar_resources = [ {"id": "a", "building": "Building A", "title": "Room A"}, {"id": "b", "building": "Building A", "title": "Room B"}, {"id": "c", "building": "Building B", "title": "Room C"} ]

calendar_options = {
    "editable": True,
    "selectable": True,
    "navLinks": True,
    "resources": calendar_resources,
    "resourceGroupField": "building",
}

state = calendar(
    events=st.session_state.events,
    options=calendar_options,
    custom_css=".fc-event-past { opacity: 0.8; } .fc-event-title { font-weight: 700; }",
    key="calendar"
)

# Event Interaction
if state.get("eventClick"):
    ev = state["eventClick"]["event"]
    st.subheader(f"Edit: {ev['title']}")
    with st.form("edit_form"):
        new_title = st.text_input("Title", ev["title"])
        new_color = st.color_picker("Color", ev.get("color", "#FF4B4B"))
        if st.form_submit_button("Save Changes"):
            updated = ev.copy()
            updated["title"] = new_title
            updated["color"] = new_color
            save_event(updated)
            st.session_state.events = load_events()
            st.success("Updated!")
            st.rerun()
        if st.form_submit_button("Delete", type="primary"):
            delete_event(ev["id"])
            st.session_state.events = load_events()
            st.success("Deleted!")
            st.rerun()

st.caption("✅ Neon Postgres Calendar App")
