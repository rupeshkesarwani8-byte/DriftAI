"""Tiny schema upgrade for the existing SQLite file (create_all never adds columns to old tables)."""
from sqlalchemy import inspect, text


def ensure_owner_column(engine) -> bool:
    """Add projects.owner_id if the database was created before Build 5c. Returns True if it changed anything."""
    names = {c["name"] for c in inspect(engine).get_columns("projects")}
    if "owner_id" in names:
        return False
    with engine.begin() as con:
        con.execute(text("ALTER TABLE projects ADD COLUMN owner_id INTEGER"))
        con.execute(text("CREATE INDEX IF NOT EXISTS ix_projects_owner_id ON projects (owner_id)"))
    return True