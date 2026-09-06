"""
IMPACT-X — Authentication Module
Handles user sign-up and sign-in for the dashboard itself (separate from
the simulated NovaTech Corporation identities used inside the demo data).

Passwords are hashed with bcrypt (industry-standard, automatically salted,
one-way) before being stored — the plain-text password is never saved
anywhere, and cannot be recovered from the stored hash.

This table lives independently from impact_x.db's simulated org data, and
is NEVER dropped/rebuilt by database.build_database() — so user accounts
persist across every demo data reset.
"""

import sqlite3
import os
import re
import bcrypt

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "impact_x.db")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_table():
    """Creates the AUTH_USERS table if it doesn't already exist.
    Uses CREATE TABLE IF NOT EXISTS (never DROP) so accounts are never
    wiped by resetting the simulated organization data."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS AUTH_USERS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def _hash_password(password):
    """Hashes a password with bcrypt (includes an automatic random salt).
    Returns the hash as a string, safe to store in the database."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def _verify_password(password, password_hash):
    """Checks a plain-text password attempt against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def validate_signup_input(username, email, password, confirm_password):
    """Returns an error message string, or None if everything is valid."""
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
    Creates a new user account with a securely hashed password.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    try:
        password_hash = _hash_password(password)
        conn.execute(
            "INSERT INTO AUTH_USERS (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash),
        )
        conn.commit()
        return True, "Account created successfully."
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, "That username is already taken."
        elif "email" in str(e):
            return False, "That email is already registered."
        return False, "Could not create account (duplicate entry)."
    finally:
        conn.close()


def verify_user(username, password):
    """
    Checks sign-in credentials.
    Returns (success: bool, message: str).
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM AUTH_USERS WHERE username = ?", (username,)
    ).fetchone()
    conn.close()

    if not row:
        return False, "No account found with that username."
    if not _verify_password(password, row["password_hash"]):
        return False, "Incorrect password."
    return True, "Signed in successfully."


if __name__ == "__main__":
    init_auth_table()
    print("=== Auth table ready ===")

    print("\n=== Creating a sample account ===")
    ok, msg = create_user("demo_analyst", "demo@example.com", "SecurePass123")
    print(f"create_user: {ok} — {msg}")

    print("\n=== Verifying correct password ===")
    ok, msg = verify_user("demo_analyst", "SecurePass123")
    print(f"verify_user (correct): {ok} — {msg}")

    print("\n=== Verifying wrong password ===")
    ok, msg = verify_user("demo_analyst", "WrongPassword")
    print(f"verify_user (wrong): {ok} — {msg}")

    print("\n=== Attempting duplicate signup ===")
    ok, msg = create_user("demo_analyst", "demo@example.com", "AnotherPass123")
    print(f"create_user (duplicate): {ok} — {msg}")