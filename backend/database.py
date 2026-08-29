"""
IMPACT-X — Phase 3: Database Design & Loader
Creates the SQLite schema and loads the simulated organization
(from seed_data.py) into it.

Run this file directly to (re)build data/impact_x.db from scratch.
"""

import sqlite3
import os
from seed_data import build_organization

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "impact_x.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_schema(conn):
    cursor = conn.cursor()

    cursor.executescript("""
    DROP TABLE IF EXISTS RELATIONSHIPS;
    DROP TABLE IF EXISTS INCIDENTS;
    DROP TABLE IF EXISTS ASSETS;
    DROP TABLE IF EXISTS BUSINESS_SERVICES;
    DROP TABLE IF EXISTS USERS;

    CREATE TABLE USERS (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        role TEXT NOT NULL,
        privilege_level TEXT NOT NULL CHECK (privilege_level IN ('standard', 'elevated', 'admin'))
    );

    CREATE TABLE BUSINESS_SERVICES (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        criticality TEXT NOT NULL CHECK (criticality IN ('low', 'medium', 'high', 'critical'))
    );

    -- Unified table for applications, databases, servers, apis, cloud_resources
    CREATE TABLE ASSETS (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('application', 'database', 'server', 'api', 'cloud_resource')),
        owner_department TEXT,
        data_sensitivity TEXT CHECK (data_sensitivity IN ('low', 'medium', 'high') OR data_sensitivity IS NULL)
    );

    -- Graph edges: connects any two entities (user/asset/business service) by id
    CREATE TABLE RELATIONSHIPS (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_id TEXT NOT NULL,
        to_id TEXT NOT NULL,
        relationship_type TEXT NOT NULL CHECK (
            relationship_type IN ('HAS_ACCESS', 'CONNECTS_TO', 'DEPENDS_ON', 'HOSTS', 'SUPPORTS', 'OWNS')
        )
    );

    CREATE TABLE INCIDENTS (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id TEXT NOT NULL,
        incident_type TEXT NOT NULL,
        risk_level TEXT NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
        risk_score INTEGER,
        status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'INVESTIGATING', 'RESOLVED')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_relationships_from ON RELATIONSHIPS(from_id);
    CREATE INDEX idx_relationships_to ON RELATIONSHIPS(to_id);
    CREATE INDEX idx_incidents_entity ON INCIDENTS(entity_id);
    """)

    conn.commit()


def load_data(conn, org):
    cursor = conn.cursor()

    # USERS
    cursor.executemany(
        "INSERT INTO USERS (id, name, department, role, privilege_level) VALUES (?, ?, ?, ?, ?)",
        [(u["id"], u["name"], u["department"], u["role"], u["privilege_level"]) for u in org["users"]]
    )

    # BUSINESS_SERVICES
    cursor.executemany(
        "INSERT INTO BUSINESS_SERVICES (id, name, criticality) VALUES (?, ?, ?)",
        [(s["id"], s["name"], s["criticality"]) for s in org["business_services"]]
    )

    # ASSETS — applications
    cursor.executemany(
        "INSERT INTO ASSETS (id, name, type, owner_department, data_sensitivity) VALUES (?, ?, 'application', ?, NULL)",
        [(a["id"], a["name"], a["owner_department"]) for a in org["applications"]]
    )

    # ASSETS — databases
    cursor.executemany(
        "INSERT INTO ASSETS (id, name, type, owner_department, data_sensitivity) VALUES (?, ?, 'database', NULL, ?)",
        [(d["id"], d["name"], d["data_sensitivity"]) for d in org["databases"]]
    )

    # ASSETS — apis
    cursor.executemany(
        "INSERT INTO ASSETS (id, name, type, owner_department, data_sensitivity) VALUES (?, ?, 'api', NULL, NULL)",
        [(a["id"], a["name"]) for a in org["apis"]]
    )

    # ASSETS — servers
    cursor.executemany(
        "INSERT INTO ASSETS (id, name, type, owner_department, data_sensitivity) VALUES (?, ?, 'server', NULL, NULL)",
        [(s["id"], s["name"]) for s in org["servers"]]
    )

    # ASSETS — cloud resources
    cursor.executemany(
        "INSERT INTO ASSETS (id, name, type, owner_department, data_sensitivity) VALUES (?, ?, 'cloud_resource', NULL, NULL)",
        [(c["id"], c["name"]) for c in org["cloud_resources"]]
    )

    # RELATIONSHIPS
    cursor.executemany(
        "INSERT INTO RELATIONSHIPS (from_id, to_id, relationship_type) VALUES (?, ?, ?)",
        [(r["from"], r["to"], r["type"]) for r in org["relationships"]]
    )

    conn.commit()


def build_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    org = build_organization()
    conn = get_connection()
    create_schema(conn)
    load_data(conn, org)

    # Sanity check counts
    cursor = conn.cursor()
    for table in ["USERS", "BUSINESS_SERVICES", "ASSETS", "RELATIONSHIPS", "INCIDENTS"]:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows")

    conn.close()
    print(f"\nDatabase built at: {os.path.abspath(DB_PATH)}")


if __name__ == "__main__":
    build_database()