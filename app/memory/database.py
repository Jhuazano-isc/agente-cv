import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent.parent / "storage" / "memory.db"

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversation_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            response_id TEXT NOT NULL,
            previous_response_id TEXT,
            user_message TEXT NOT NULL,
            agent_reply TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def log_turn(response_id: str, previous_response_id: str | None, user_message: str, agent_reply: str):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO conversation_turns (timestamp, response_id, previous_response_id, user_message, agent_reply)
        VALUES (?, ?, ?, ?, ?)
        """,
        (datetime.now(timezone.utc).isoformat(), response_id, previous_response_id, user_message, agent_reply),
    )
    conn.commit()
    conn.close()


