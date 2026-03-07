"""SQLite database initialization and connection management."""

import sqlite3
import threading
from pathlib import Path
from typing import Optional

# Module-level database path — defaults to herald.db next to this file
_DB_PATH: str = str(Path(__file__).parent.parent / "herald.db")
_local = threading.local()


def set_db_path(path: str) -> None:
    """Override the database path (useful for testing)."""
    global _DB_PATH
    _DB_PATH = path


def get_db_path() -> str:
    """Return the current database path."""
    return _DB_PATH


def get_connection() -> sqlite3.Connection:
    """Get a thread-local SQLite connection with row factory."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def close_connection() -> None:
    """Close the thread-local connection if it exists."""
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None


def init_db(db_path: Optional[str] = None) -> None:
    """Create all tables if they don't exist."""
    if db_path is not None:
        set_db_path(db_path)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS knowledge_items (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            embedding TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            company TEXT,
            plan TEXT DEFAULT 'free',
            health_score REAL DEFAULT 100.0,
            signup_date TEXT NOT NULL,
            last_active TEXT,
            churn_risk TEXT DEFAULT 'low',
            total_conversations INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL REFERENCES customers(id),
            channel TEXT DEFAULT 'chat',
            status TEXT DEFAULT 'active',
            sentiment_score REAL,
            satisfaction INTEGER,
            assigned_to TEXT,
            subject TEXT,
            resolved_at TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL REFERENCES conversations(id),
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            conversation_id TEXT REFERENCES conversations(id),
            customer_id TEXT NOT NULL REFERENCES customers(id),
            subject TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'open',
            priority TEXT DEFAULT 'medium',
            category TEXT,
            assigned_to TEXT,
            resolution_notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT
        );

        CREATE TABLE IF NOT EXISTS onboarding_flows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            steps_json TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS customer_onboarding (
            id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL REFERENCES customers(id),
            flow_id TEXT NOT NULL REFERENCES onboarding_flows(id),
            current_step INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            started_at TEXT NOT NULL,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS copilot_suggestions (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL REFERENCES conversations(id),
            suggestion TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
    """)

    conn.commit()
