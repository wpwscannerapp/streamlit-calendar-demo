import streamlit as st
import psycopg2
import uuid
import json
from datetime import datetime, timedelta
from streamlit_calendar import calendar

st.set_page_config(page_title="Multi Calendar", page_icon="📅", layout="wide")

# ====================== Robust Neon Connection ======================
@st.cache_resource(show_spinner="Connecting to Neon...")
def get_db_connection():
    try:
        conn = psycopg2.connect(
            "postgresql://neondb_owner:npg_Zf2b3FjPdnvh@ep-frosty-fog-at6gioza-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require",
            connect_timeout=10
        )
        conn.set_session(autocommit=True)  # Important for Streamlit
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        st.stop()

def get_cursor():
    """Get a fresh cursor"""
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
        st.error(f"Init DB error: {e}")

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
    extended = {k: v for k, v in event.items() 
                if k not in ['id','title','start','end','color','resourceId']}
    
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
        st.error(f"Save error: {e}")

def delete_event(event_id: str):
    try:
        with get_cursor() as cur:
            cur.execute("DELETE FROM events WHERE id = %s", (event_id,))
    except Exception as e:
        st.error(f"Delete error: {e}")

# ====================== Initialize ======================
init_db()

if "events" not in st.session_state:
    st.session_state.events = load_events()

# ====================== Sidebar & Calendar (same as before) ======================
# ... [Keep the rest of your UI code from the previous full version]

st.caption("✅ Neon Connected • Robust Mode")
