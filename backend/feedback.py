"""
IMPACT-X — Feedback Module
Collects structured feedback from people using the dashboard (ratings +
free-text comments per category) and compiles it into a summary report
so Madhav can see, at a glance, what's working and what to fix next.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "impact_x.db")

CATEGORIES = [
    "Overall Experience",
    "Speed / Performance",
    "Mobile Experience",
    "AI Incident Summaries",
    "Visual Design",
    "Ease of Use",
]


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.row_factory = sqlite3.Row
    return conn


def init_feedback_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS FEEDBACK (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            category TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            comments TEXT,
            improvement_suggestion TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def submit_feedback(username, category, rating, comments, improvement_suggestion=""):
    conn = get_connection()
    conn.execute(
        """INSERT INTO FEEDBACK (username, category, rating, comments, improvement_suggestion)
           VALUES (?, ?, ?, ?, ?)""",
        (username, category, rating, comments, improvement_suggestion),
    )
    conn.commit()
    conn.close()


def get_all_feedback():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM FEEDBACK ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_feedback_summary():
    """Returns a compiled report: overall + per-category averages, and the
    most recent written comments/suggestions."""
    rows = get_all_feedback()
    if not rows:
        return {"count": 0, "avg_rating": 0, "by_category": {}, "recent": []}

    avg_rating = sum(r["rating"] for r in rows) / len(rows)

    by_category = {}
    for r in rows:
        by_category.setdefault(r["category"], []).append(r["rating"])
    by_category_avg = {cat: round(sum(v) / len(v), 2) for cat, v in by_category.items()}

    recent = [r for r in rows if (r.get("comments") or r.get("improvement_suggestion"))][:15]

    return {
        "count": len(rows),
        "avg_rating": round(avg_rating, 2),
        "by_category": by_category_avg,
        "recent": recent,
    }