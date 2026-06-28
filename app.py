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

def load_events():
    with get_cursor() as cur:
        cur.execute("SELECT * FROM events ORDER BY start")
        rows = cur.fetchall()
    events = []
    for row in rows:
        event = {"id": row[0], "title": row[1], "start": row[2], "color": row[4], "resourceId": row[5]}
        if row[3]: event["end"] = row[3]
        if row[6]: event.update(json.loads(row[6]))
        events.append(event)
    return events

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
            event["title"], event["start"], event.get("end"),
            event.get("color"), event.get("resourceId"),
            json.dumps(extended) if extended else None
        ))

def delete_event(event_id):
    with get_cursor() as cur:
        cur.execute("DELETE FROM events WHERE id = %s", (event_id,))

# ====================== Resources ======================
if "resources" not in st.session_state:
    st.session_state.resources = [
        {"id": "a", "title": "Room A", "building": "Building A", "color": "#FF4B4B"},
        {"id": "b", "title": "Room B", "building": "Building A", "color": "#3D9DF3"},
        {"id": "c", "title": "Conference Room", "building": "Building B", "color": "#3DD56D"},
    ]

# ====================== Recurring Helper ======================
def generate_recurring(base_event, rec_type, interval=1, count=12):
    instances = []
    try:
        start = datetime.fromisoformat(base_event["start"].replace("Z", "+00:00"))
        end_delta = datetime.fromisoformat(base_event.get("end", base_event["start"]).replace("Z", "+00:00")) - start
        
        for i in range(count):
            if rec_type == "daily":
                delta = timedelta(days=i * interval)
            elif rec_type == "weekly":
                delta = timedelta(weeks=i * interval)
            else:  # monthly
                delta = timedelta(days=i * 30 * interval)
            
            new_event = base_event.copy()
            new_event["id"] = f"{base_event.get('id')}_{i}"
            new_event["start"] = (start + delta).isoformat()
            new_event["end"] = (start + delta + end_delta).isoformat()
            instances.append(new_event)
    except:
        instances = [base_event]
    return instances

# ====================== UI ======================
init_db()
if "events" not in st.session_state:
    st.session_state.events = load_events()

# Sidebar
with st.sidebar:
    st.header("Resources")
    for i, r in enumerate(st.session_state.resources):
        c1, c2 = st.columns([3,1])
        with c1:
            r["title"] = st.text_input("Name", r["title"], key=f"rname_{i}")
            r["color"] = st.color_picker("Color", r["color"], key=f"rcol_{i}")
        if st.button("Delete", key=f"rdel_{i}"):
            st.session_state.resources.pop(i)
            st.rerun()
    
    if st.button("➕ Add Resource"):
        new_id = chr(97 + len(st.session_state.resources))
        st.session_state.resources.append({"id": new_id, "title": f"New Resource {new_id.upper()}", "building": "General", "color": "#999999"})
        st.rerun()

    st.header("➕ Add Event")
    with st.form("add_event"):
        title = st.text_input("Title *")
        col1, col2 = st.columns(2)
        with col1:
            sdate = st.date_input("Start")
            stime = st.time_input("Start Time", datetime.strptime("09:00", "%H:%M").time())
        with col2:
            edate = st.date_input("End", sdate)
            etime = st.time_input("End Time", datetime.strptime("10:00", "%H:%M").time())
        
        resourceId = st.selectbox("Resource", [r["id"] for r in st.session_state.resources],
                                 format_func=lambda x: next(r["title"] for r in st.session_state.resources if r["id"] == x))
        recurrence = st.selectbox("Recurrence", ["None", "Daily", "Weekly", "Monthly"])
        
        if st.form_submit_button("Save"):
            if title:
                base = {
                    "title": title,
                    "start": f"{sdate}T{stime}",
                    "end": f"{edate}T{etime}",
                    "resourceId": resourceId,
                    "color": next(r["color"] for r in st.session_state.resources if r["id"] == resourceId)
                }
                if recurrence != "None":
                    base["recurrence"] = {"type": recurrence.lower()}
                    instances = generate_recurring(base, recurrence.lower())
                    for inst in instances:
                        save_event(inst)
                else:
                    save_event(base)
                st.session_state.events = load_events()
                st.success("Saved!")
                st.rerun()

# Calendar
calendar_resources = [{"id": r["id"], "title": r["title"], "building": r.get("building", "General")} for r in st.session_state.resources]

state = calendar(
    events=st.session_state.events,
    options={"editable": True, "resources": calendar_resources, "resourceGroupField": "building", "selectable": True},
    key="multi_cal"
)

if state.get("eventClick"):
    ev = state["eventClick"]["event"]
    st.subheader(f"Edit: {ev['title']}")
    # Simple edit form
    with st.form("edit"):
        new_title = st.text_input("Title", ev["title"])
        if st.form_submit_button("Update"):
            updated = ev.copy()
            updated["title"] = new_title
            save_event(updated)
            st.session_state.events = load_events()
            st.rerun()
        if st.form_submit_button("Delete", type="primary"):
            delete_event(ev["id"])
            st.session_state.events = load_events()
            st.rerun()

st.caption("Multi Calendar with Recurring Events • Neon Postgres")
