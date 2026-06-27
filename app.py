import streamlit as st
import uuid
import json
from datetime import datetime
from streamlit_calendar import calendar

st.set_page_config(page_title="My Calendar", page_icon="📅", layout="wide")

# ====================== Neon Connection ======================
conn = st.connection("neon", type="sql")

def init_db():
    conn.execute("""
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

def load_events():
    df = conn.query("SELECT * FROM events ORDER BY start")
    events = []
    for _, row in df.iterrows():
        event = {
            "id": row["id"],
            "title": row["title"],
            "start": row["start"],
            "color": row["color"],
            "resourceId": row["resourceid"],
        }
        if row["end"]:
            event["end"] = row["end"]
        if row["extended_props"]:
            event.update(json.loads(row["extended_props"]))
        events.append(event)
    return events

def save_event(event: dict):
    extended = {k: v for k, v in event.items() 
                if k not in ['id','title','start','end','color','resourceId']}
    
    conn.execute("""
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

def delete_event(event_id):
    conn.execute("DELETE FROM events WHERE id = %s", (event_id,))

# Initialize
init_db()
if "events" not in st.session_state:
    st.session_state.events = load_events()

# ====================== UI ======================
st.title("📅 My Full Calendar")

mode = st.selectbox("Mode", [
    "daygrid", "timegrid", "timeline", 
    "resource-daygrid", "resource-timegrid", "resource-timeline", 
    "list", "multimonth"
], index=0)

# Add Event (Sidebar)
with st.sidebar:
    st.header("➕ Add Event")
    with st.form("add_event"):
        title = st.text_input("Event Title")
        col1, col2 = st.columns(2)
        with col1:
            sdate = st.date_input("Start Date")
            stime = st.time_input("Start Time", datetime.strptime("09:00", "%H:%M").time())
        with col2:
            edate = st.date_input("End Date", sdate)
            etime = st.time_input("End Time", datetime.strptime("10:00", "%H:%M").time())
        
        color = st.color_picker("Color", "#FF4B4B")
        resourceId = st.selectbox("Room/Resource", ["a","b","c","d","e","f"])
        
        if st.form_submit_button("Save Event"):
            if title:
                new_event = {
                    "title": title,
                    "start": f"{sdate}T{stime}",
                    "end": f"{edate}T{etime}",
                    "color": color,
                    "resourceId": resourceId
                }
                save_event(new_event)
                st.session_state.events = load_events()
                st.success("Event saved!")
                st.rerun()

# Calendar Resources (customize as needed)
calendar_resources = [
    {"id": "a", "building": "Building A", "title": "Room A"},
    {"id": "b", "building": "Building A", "title": "Room B"},
    {"id": "c", "building": "Building B", "title": "Room C"},
    # Add more...
]

calendar_options = {
    "editable": True,
    "selectable": True,
    "navLinks": True,
    "resources": calendar_resources,
    "resourceGroupField": "building",
    # You can expand this with mode-specific options like in your original demo
}

state = calendar(
    events=st.session_state.events,
    options=calendar_options,
    custom_css="""
        .fc-event-past { opacity: 0.8; }
        .fc-event-title { font-weight: 700; }
    """,
    key=mode
)

# Handle clicks
if state.get("eventClick"):
    ev = state["eventClick"]["event"]
    st.info(f"**Clicked:** {ev['title']} ({ev.get('start')})")
    
    if st.button("🗑️ Delete this event", type="primary"):
        delete_event(ev["id"])
        st.session_state.events = load_events()
        st.success("Event deleted")
        st.rerun()

st.caption("✅ Connected to Neon Postgres")
