import sqlite3
from datetime import datetime
import threading
import os

log_lock = threading.Lock()

# Set shared DB file path (relative to project root or use absolute path)
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "chat_logs.db"))

# Establish connection
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,         -- 'client' or 'server'
    source TEXT NOT NULL,       -- e.g., username or SID
    event TEXT NOT NULL,        -- event message
    timestamp TEXT NOT NULL     -- when the event occurred
)
""")
conn.commit()

def log_event(role, source, event):
    """Thread-safe log insertion"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_lock:
        cursor.execute(
            "INSERT INTO logs (role, source, event, timestamp) VALUES (?, ?, ?, ?)",
            (role, source, event, timestamp)
        )
        conn.commit()

def close_logger():
    with log_lock:
        conn.close()
