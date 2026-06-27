import streamlit as st
import sqlite3
import json
from datetime import datetime
from streamlit_calendar import calendar

st.set_page_config(page_title="Full Calendar App", page_icon="📅", layout="wide")

# ====================== DATABASE SETUP ======================
def init_db():
    conn = sqlite3.connect('calendar.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT,
            start TEXT,
            end TEXT,
            color TEXT,
            resourceId TEXT,
            extendedProps TEXT
        )
    ''')
    conn.commit()
    conn.close()

def load_events():
    conn = sqlite3.connect('calendar.db')
    c = conn.cursor()
    c.execute("SELECT * FROM events")
    rows = c.fetchall()
    conn.close()
    
    events = []
    for row in rows:
        event = {
            "id": row[0],
            "title": row[1],
            "start": row[2],
            "end": row[3],
            "color": row[4],
            "resourceId": row[5],
        }
        if row[6]:
            event.update(json.loads(row[6]))
        events.append(event)
    return events

def save_event(event):
    conn = sqlite3.connect('calendar.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO events (id, title, start, end, color, resourceId, extendedProps)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        event.get('id', datetime.now().isoformat()),
        event['title'],
        event['start'],
        event.get('end'),
        event.get('color', '#3788d8'),
        event.get('resourceId'),
        json.dumps({k: v for k, v in event.items() if k not in ['id','title','start','end','color','resourceId']})
    ))
    conn.commit()
    conn.close()

def delete_event(event_id):
    conn = sqlite3.connect('calendar.db')
    c = conn.cursor()
    c.execute("DELETE FROM events WHERE id=?", (event_id,))
    conn.commit()
    conn.close()

# Initialize DB and load events
init_db()
if 'events' not in st.session_state:
    st.session_state.events = load_events()

# ====================== SIDEBAR ======================
st.sidebar.header("📅 Full Calendar App")

mode = st.sidebar.selectbox(
    "View Mode",
    ["daygrid", "timegrid", "timeline", "resource-daygrid", "resource-timegrid", "resource-timeline", "list", "multimonth"],
    index=0
)

# Add new event form
st.sidebar.subheader("➕ Add New Event")
with st.sidebar.form("new_event"):
    title = st.text_input("Event Title")
    start_date = st.date_input("Start Date")
    start_time = st.time_input("Start Time", value=datetime.strptime("09:00", "%H:%M").time())
    end_date = st.date_input("End Date", value=start_date)
    end_time = st.time_input("End Time", value=datetime.strptime("10:00", "%H:%M").time())
    
    color = st.color_picker("Color", "#3788d8")
    resource = st.selectbox("Resource", [r["title"] for r in calendar_resources]) if 'calendar_resources' in globals() else None
    
    submitted = st.form_submit_button("Add Event")
    if submitted and title:
        start = f"{start_date}T{start_time}"
        end = f"{end_date}T{end_time}"
        new_event = {
            "title": title,
            "start": start,
            "end": end,
            "color": color,
            "resourceId": resource
        }
        save_event(new_event)
        st.session_state.events = load_events()
        st.success("Event added!")
        st.rerun()

if st.sidebar.button("🔄 Refresh Events"):
    st.session_state.events = load_events()
    st.rerun()

# ====================== CALENDAR OPTIONS ======================
calendar_resources = [
    {"id": "a", "building": "Building A", "title": "Room A"},
    {"id": "b", "building": "Building A", "title": "Room B"},
    # ... add more
]

calendar_options = {
    "editable": True,
    "navLinks": True,
    "selectable": True,
    "resources": calendar_resources,
    "resourceGroupField": "building",
}

# Dynamic options based on mode (same logic as your demo, expanded)
if "resource" in mode:
    # ... (copy and adapt from your original demo)
    pass
else:
    # ... adapt other modes

# ====================== RENDER CALENDAR ======================
state = calendar(
    events=st.session_state.events,
    options=calendar_options,
    custom_css="""
    .fc-event-past { opacity: 0.8; }
    .fc-event-time { font-style: italic; }
    .fc-event-title { font-weight: 700; }
    """,
    key=mode + "_full",
)

# ====================== HANDLE CALLBACKS ======================
if state.get("eventClick"):
    event = state["eventClick"]["event"]
    st.info(f"Clicked: {event['title']}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Delete Event"):
            delete_event(event['id'])
            st.session_state.events = load_events()
            st.success("Event deleted")
            st.rerun()
    with col2:
        # Edit form would go here
        pass

if state.get("select"):
    st.success(f"Selected range: {state['select']['start']} to {state['select']['end']}")
    # Pre-fill add form or auto-create

if state.get("eventsSet"):
    # Optional: sync back if drag/drop
    pass

st.write("### Raw State (for debugging)")
st.json(state)
