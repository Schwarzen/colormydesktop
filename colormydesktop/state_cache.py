import os
import sqlite3
from typing import Dict, Optional

# Automatically resolve the correct system location (Works for native & Flatpak)
XDG_CONFIG = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
DB_DIR = os.path.join(XDG_CONFIG, "colormydesktop")
DB_PATH = os.path.join(DB_DIR, "state_cache.db")


def _get_connection() -> sqlite3.Connection:
    """Creates directory path and returns a thread-safe connection instance."""
    os.makedirs(DB_DIR, exist_ok=True)
    # Enable WAL mode (Write-Ahead Logging) for safe concurrent reads/writes
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_cache() -> None:
    """Initializes the database schema if it does not already exist."""
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feature_switches (
                css_id TEXT PRIMARY KEY,
                is_active INTEGER NOT NULL
            )
            """
        )
        conn.commit()


def save_switch_state(css_id: str, is_active: bool) -> None:
    """Saves or updates a single switch state atomically using UPSERT syntax."""
    # Convert Python boolean to SQLite integer (1 or 0)
    value = 1 if is_active else 0

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO feature_switches (css_id, is_active)
            VALUES (?, ?)
            ON CONFLICT(css_id) 
            DO UPDATE SET is_active = excluded.is_active
            """,
            (css_id, value),
        )
        conn.commit()


def load_all_switch_states() -> Dict[str, bool]:
    """Retrieves all persisted switch toggles as a native Python dictionary."""
    states = {}
    if not os.path.exists(DB_PATH):
        return states

    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT css_id, is_active FROM feature_switches")
        for css_id, is_active in cursor.fetchall():
            states[css_id] = bool(is_active)

    return states
