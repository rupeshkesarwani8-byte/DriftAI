"""Tiny user store on its own SQLite file (users.db) so the existing database is untouched."""
import os
import re
import sqlite3
from datetime import datetime, timezone

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def db_path() -> str:
    return os.environ.get("DRIFTAI_USERS_DB", "users.db")


def _conn(path: str | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(path or db_path())
    con.row_factory = sqlite3.Row
    con.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "email TEXT NOT NULL UNIQUE, "
        "name TEXT NOT NULL, "
        "password_hash TEXT NOT NULL, "
        "created_at TEXT NOT NULL)"
    )
    return con


def normalize_email(email: str) -> str:
    return email.strip().lower()


def create_user(email: str, name: str, password_hash: str, path: str | None = None) -> dict | None:
    """Return the new user, or None if the email is already registered."""
    email = normalize_email(email)
    con = _conn(path)
    try:
        cur = con.execute(
            "INSERT INTO users (email, name, password_hash, created_at) VALUES (?,?,?,?)",
            (email, name.strip(), password_hash, datetime.now(timezone.utc).isoformat()),
        )
        con.commit()
        return get_user(cur.lastrowid, path)
    except sqlite3.IntegrityError:
        return None
    finally:
        con.close()


def _row(row) -> dict | None:
    return dict(row) if row else None


def get_user(user_id: int, path: str | None = None) -> dict | None:
    con = _conn(path)
    try:
        return _row(con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
    finally:
        con.close()


def get_user_by_email(email: str, path: str | None = None) -> dict | None:
    con = _conn(path)
    try:
        return _row(con.execute("SELECT * FROM users WHERE email=?", (normalize_email(email),)).fetchone())
    finally:
        con.close()


def first_user_id(path: str | None = None) -> int | None:
    """Id of the earliest account. Projects made before accounts existed go to this user."""
    con = _conn(path)
    try:
        row = con.execute("SELECT MIN(id) FROM users").fetchone()
        return row[0] if row and row[0] is not None else None
    finally:
        con.close()



def update_password(user_id: int, password_hash: str, path: str | None = None) -> None:
    con = _conn(path)
    try:
        con.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, user_id))
        con.commit()
    finally:
        con.close()