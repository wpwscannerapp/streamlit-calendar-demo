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

def load_resources():
    with get_cursor() as cur:
        cur.execute("SELECT * FROM resources ORDER BY id")
        rows = cur.fetchall()
    if not rows:
        defaults = [("a", "Room A", "Building A", "#FF4B4B"), ("b", "Room B", "Building A", "#3D9DF3"), ("c", "Conference Room", "Building B", "#3DD56D")]
        with get_cursor() as cur:
            for d in defaults:
                cur.execute("INSERT INTO resources VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING", d)
        return load_resources()
    return [{"id": r[0], "title": r[1], "building": r[2], "color": r[3]} for r in rows]

def save_resource(res):
    with get_cursor() as cur:
        cur.execute("INSERT INTO resources (id, title, building, color) VALUES (%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title, building=EXCLUDED.building, color=EXCLUDED.color", 
                   (res["id"], res["title"], res.get("building", "General"), res["color"]))

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

# Recurrence Generator
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
            new_event["id"] = f"{base_event.get('id','')}_{i}"
            new_event["start"] = (start + delta).isoformat()
            new_event["end"] = (start + delta + end_delta).isoformat()
            instances.append(new_event)
    except:
        instances = [base_event]
    return instances

# Init
init_db()
if "resources" not in st.session_state:
    st.session_state.resources = load_resources()
if "events" not in st.session_state:
    st.session_state.events = load_events()

# Sidebar
with st.sidebar:
    st.header("Resources")
    for i, r in enumerate(st.session_state.resources):
        col1, col2 = st.columns([3,1])
        with col1:
            new_title = st.text_input("Name", r["title"], key=f"rt_{i}")
            if new_title != r["title"]:
                r["title"] = new_title
                save_resource(r)
        with col2:
            new_color = st.color_picker("", r["color"], key=f"rc_{i}")
            if new_color != r["color"]:
                r["color"] = new_color
                save_resource(r)
    if st.button("➕ Add Resource"):
        new_id = chr(97 + len(st.session_state.resources))
        new_res = {"id": new_id, "title": f"New Resource", "building": "General", "color": "#999999"}
        st.session_state.resources.append(new_res)
        save_resource(new_res)
        st.rerun()

    st.header("➕ Add Event")
    with st.form("add_event", clear_on_submit=True):
        title = st.text_input("Title *")
        address = st.text_input("Address / Location")
        notes = st.text_area("Notes")
        col1, col2 = st.columns(2)
        with col1:
            sdate = st.date_input("Start Date")
            stime = st.time_input("Start Time", datetime.strptime("09:00", "%H:%M").time())
        with col2:
            edate = st.date_input("End Date", sdate)
            etime = st.time_input("End Time", datetime.strptime("10:00", "%H:%M").time())
        
        resourceId = st.selectbox("Resource", [r["id"] for r in st.session_state.resources],
                                 format_func=lambda x: next((r["title"] for r in st.session_state.resources if r["id"] == x), x))
        recurrence = st.selectbox("Recurrence", ["None", "Daily", "Weekly", "Monthly"])
        
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
                
                if recurrence != "None":
                    instances = generate_recurring(base, recurrence.lower())
                    for inst in instances:
                        save_event(inst)
                else:
                    save_event(base)
                
                st.session_state.events = load_events()
                st.success("✅ Event(s) saved!")
                st.rerun()

# Calendar
calendar_resources = [{"id": r["id"], "title": r["title"], "building": r.get("building", "General")} for r in st.session_state.resources]

state = calendar(
    events=st.session_state.events,
    options={"editable": True, "resources": calendar_resources, "resourceGroupField": "building"},
    custom_css=".fc-event-past { opacity: 0.8; } .fc-event-title { font-weight: 700; }",
    key="multi_calendar"
)

if state.get("eventClick"):
    ev = state["eventClick"]["event"]
    st.subheader(f"✏️ {ev.get('title', 'Event')}")
    st.write(f"**Location:** {ev.get('address', 'Not set')}")
    if ev.get("notes"): st.write(f"**Notes:** {ev['notes']}")
    
    with st.form("edit_event"):
        new_title = st.text_input("Title", ev.get("title", ""))
        new_address = st.text_input("Address", ev.get("address", ""))
        new_notes = st.text_area("Notes", ev.get("notes", ""))
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Save Changes"):
                updated = ev.copy()
                updated["title"] = new_title
                updated["address"] = new_address
                updated["notes"] = new_notes
                save_event(updated)
                st.session_state.events = load_events()
                st.success("Updated!")
                st.rerun()
        with col2:
            if st.form_submit_button("Delete", type="primary"):
                delete_event(ev["id"])
                st.session_state.events = load_events()
                st.success("Deleted!")
                st.rerun()

st.caption("Multi Calendar with Recurring Events • Neon Postgres")
