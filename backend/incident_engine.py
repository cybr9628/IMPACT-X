"""
IMPACT-X — Phase 5: Incident Detection & Simulation
Simulates a security event against a real user/identity in the graph,
then logs it into the INCIDENTS table.

This is the "trigger" — the single alert that Phase 6 (Blast Radius Engine)
and Phase 7 (Risk Scoring) react to.
"""

import sqlite3
import os
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "impact_x.db")

INCIDENT_TYPES = [
    "Suspicious Login",
    "Impossible Travel Login",
    "Unusual Privilege Change",
    "Abnormal API Activity",
    "Unexpected Access Pattern",
]

# Base risk level purely from the TYPE of event (before we know the identity's privilege).
# Phase 7 will combine this with privilege + asset criticality for the final numeric score.
INCIDENT_BASE_RISK = {
    "Suspicious Login": "MEDIUM",
    "Impossible Travel Login": "HIGH",
    "Unusual Privilege Change": "HIGH",
    "Abnormal API Activity": "MEDIUM",
    "Unexpected Access Pattern": "LOW",
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_random_user(conn, privilege_level=None):
    """Fetch a random user. Optionally filter by privilege level
    (useful for demo: force a high-impact 'admin' user)."""
    cursor = conn.cursor()
    if privilege_level:
        rows = cursor.execute(
            "SELECT * FROM USERS WHERE privilege_level = ?", (privilege_level,)
        ).fetchall()
    else:
        rows = cursor.execute("SELECT * FROM USERS").fetchall()
    return dict(random.choice(rows)) if rows else None


def get_user_by_id(conn, user_id):
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM USERS WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def simulate_incident(user_id=None, incident_type=None, privilege_level=None):
    """
    Simulates a security incident and inserts it into INCIDENTS.

    - user_id: force a specific user (e.g., "U014"). If None, picks randomly.
    - incident_type: force a specific event type. If None, picks randomly.
    - privilege_level: only used when user_id is None — filters random pick
      (e.g., "admin" to guarantee a high-impact demo incident).

    Returns the incident dict that was inserted.
    """
    conn = get_connection()

    if user_id:
        user = get_user_by_id(conn, user_id)
        if not user:
            conn.close()
            raise ValueError(f"No user found with id '{user_id}'")
    else:
        user = get_random_user(conn, privilege_level)
        if not user:
            conn.close()
            raise ValueError("No users found in database — did you run database.py?")

    event_type = incident_type or random.choice(INCIDENT_TYPES)
    base_risk = INCIDENT_BASE_RISK.get(event_type, "MEDIUM")

    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO INCIDENTS (entity_id, incident_type, risk_level, risk_score, status)
           VALUES (?, ?, ?, ?, ?)""",
        (user["id"], event_type, base_risk, None, "OPEN"),
    )
    conn.commit()
    incident_id = cursor.lastrowid

    incident = {
        "incident_id": incident_id,
        "entity_id": user["id"],
        "entity_name": user["name"],
        "department": user["department"],
        "role": user["role"],
        "privilege_level": user["privilege_level"],
        "incident_type": event_type,
        "risk_level": base_risk,
        "status": "OPEN",
    }

    conn.close()
    return incident


def get_all_incidents():
    """Returns all incidents currently logged, most recent first."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM INCIDENTS ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_incidents():
    """Wipes all incidents — useful for resetting before a demo run."""
    conn = get_connection()
    conn.execute("DELETE FROM INCIDENTS")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("=== Simulating a random incident ===")
    incident = simulate_incident()
    print(f"INCIDENT #{incident['incident_id']}")
    print(f"Entity: {incident['entity_name']} ({incident['role']}, {incident['department']})")
    print(f"Privilege: {incident['privilege_level']}")
    print(f"Incident: {incident['incident_type']}")
    print(f"Risk (base): {incident['risk_level']}")

    print("\n=== Simulating a HIGH-IMPACT demo incident (forced admin user) ===")
    demo_incident = simulate_incident(privilege_level="admin", incident_type="Impossible Travel Login")
    print(f"INCIDENT #{demo_incident['incident_id']}")
    print(f"Entity: {demo_incident['entity_name']} ({demo_incident['role']}, {demo_incident['department']})")
    print(f"Privilege: {demo_incident['privilege_level']}")
    print(f"Incident: {demo_incident['incident_type']}")
    print(f"Risk (base): {demo_incident['risk_level']}")

    print("\n=== All incidents in DB ===")
    for inc in get_all_incidents():
        print(dict(inc))