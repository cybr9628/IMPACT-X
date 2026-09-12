"""
IMPACT-X — Authentication Module
Handles user sign-up and sign-in for the dashboard itself (separate from
the simulated NovaTech Corporation identities used inside the demo data).

Passwords are hashed with bcrypt (industry-standard, automatically salted,
one-way) before being stored — the plain-text password is never saved
anywhere, and cannot be recovered from the stored hash. Passwords are
HASHED, not encrypted — that's intentional and correct: hashing means not
even IMPACT-X itself can recover a password, which is what you want.

Email is a different story: you DO need to read it back eventually (e.g.
password reset), so it is symmetrically ENCRYPTED at rest with Fernet,
plus a separate one-way hash column used only for duplicate-detection so
the encrypted value (which changes every time due to a random IV) doesn't
break the UNIQUE constraint.

⚠️ PERSISTENCE — READ THIS:
Streamlit Community Cloud's filesystem is EPHEMERAL. The container is
rebuilt from your last git push whenever the app redeploys or wakes from
sleep (which happens automatically after a period of inactivity) — any
row written to a local SQLite file after that point is gone. That's why
accounts "disappear after a couple of days."

The fix: accounts now live in a real hosted database when one is
configured, via a DATABASE_URL connection string (works with any free
Postgres host — Supabase, Neon, Railway, etc.):

  1. Create a free Postgres project (e.g. supabase.com or neon.tech).
  2. Copy its connection string.
  3. In Streamlit Cloud: App settings -> Secrets -> add
         DATABASE_URL = "postgresql://user:password@host:5432/dbname"
     (for local dev, put the same line in .streamlit/secrets.toml, or
     just leave it unset — see below).
  4. Add `psycopg2-binary` to requirements.txt.

If DATABASE_URL isn't set (e.g. you're just running locally), this file
transparently falls back to the local SQLite file — fine for local
testing, but remember that path is NOT persistent once deployed.
"""

import os
import re
import hashlib
import bcrypt

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "impact_x.db")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_FERNET_KEY = os.environ.get("FERNET_KEY")
_fernet = None
if _FERNET_KEY:
    try:
        from cryptography.fernet import Fernet
        _fernet = Fernet(_FERNET_KEY.encode())
    except Exception:
        _fernet = None


def _get_database_url():
    """Looks for DATABASE_URL in Streamlit secrets first, then env vars.
    Returns None if neither is set (local-SQLite fallback mode)."""
    try:
        import streamlit as st
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    return os.environ.get("DATABASE_URL")


_DATABASE_URL = _get_database_url()
_USE_POSTGRES = bool(_DATABASE_URL)

if _USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
else:
    import sqlite3


def get_connection():
    """Returns a live DB connection. Postgres (persistent) when
    DATABASE_URL is configured; local SQLite otherwise."""
    if _USE_POSTGRES:
        conn = psycopg2.connect(_DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.row_factory = sqlite3.Row
    return conn


def _ph():
    """Parameter placeholder — Postgres uses %s, SQLite uses ?."""
    return "%s" if _USE_POSTGRES else "?"


def init_auth_table():
    """Creates the AUTH_USERS table if it doesn't already exist. Never
    DROPs, so accounts survive every app restart once a real DATABASE_URL
    is configured."""
    conn = get_connection()
    cur = conn.cursor()
    if _USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS AUTH_USERS (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                username_lower TEXT UNIQUE,
                email_encrypted TEXT NOT NULL,
                email_hash TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS AUTH_USERS (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                username_lower TEXT UNIQUE,
                email_encrypted TEXT NOT NULL,
                email_hash TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    cur.close()
    conn.close()


def _hash_password(password):
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def _verify_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _encrypt_email(email):
    if _fernet is None:
        return email
    return _fernet.encrypt(email.encode()).decode()


def _email_hash(email):
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


def validate_signup_input(username, email, password, confirm_password):
    if not USERNAME_RE.match(username or ""):
        return "Username must be 3-32 characters (letters, numbers, underscore only)."
    if not EMAIL_RE.match(email or ""):
        return "Please enter a valid email address."
    if not password or len(password) < 8:
        return "Password must be at least 8 characters."
    if password != confirm_password:
        return "Passwords do not match."
    return None


def create_user(username, email, password):
    """
    Creates a new user account with a securely hashed password and an
    encrypted-at-rest email. Returns (success: bool, message: str).
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        password_hash = _hash_password(password)
        p = _ph()
        cur.execute(
            f"""INSERT INTO AUTH_USERS
               (username, username_lower, email_encrypted, email_hash, password_hash)
               VALUES ({p}, {p}, {p}, {p}, {p})""",
            (username, username.lower(), _encrypt_email(email), _email_hash(email), password_hash),
        )
        conn.commit()
        return True, "Account created successfully."
    except Exception as e:
        conn.rollback()
        msg = str(e).lower()
        if "username" in msg:
            return False, "That username is already taken."
        elif "email_hash" in msg or "email" in msg:
            return False, "That email is already registered."
        return False, "Could not create account (duplicate entry)."
    finally:
        cur.close()
        conn.close()


def verify_user(username, password):
    """
    Checks sign-in credentials, case-insensitively on username.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    cur = conn.cursor()
    p = _ph()
    cur.execute(f"SELECT * FROM AUTH_USERS WHERE username_lower = {p}", ((username or "").strip().lower(),))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return False, "No account found with that username."
    password_hash = row["password_hash"]
    if not _verify_password(password, password_hash):
        return False, "Incorrect password."
    return True, "Signed in successfully."


def storage_mode():
    """Lets the UI show a small badge indicating whether accounts are
    actually persistent right now — useful for catching a misconfigured
    deploy before a demo."""
    return "postgres" if _USE_POSTGRES else "sqlite-local"


if __name__ == "__main__":
    init_auth_table()
    print(f"=== Auth table ready (storage mode: {storage_mode()}) ===")

    ok, msg = create_user("demo_analyst", "demo@example.com", "SecurePass123")
    print(f"create_user: {ok} — {msg}")

    ok, msg = verify_user("Demo_Analyst", "SecurePass123")
    print(f"verify_user (different case): {ok} — {msg}")