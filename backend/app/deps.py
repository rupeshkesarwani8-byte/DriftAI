"""Login check shared by every data route (Build 5c).

`require_user` does three things before a route runs:
  1. reads the "Authorization: Bearer <token>" header and finds the user  (401 if missing or invalid)
  2. gives the very first account the projects that were made before accounts existed
  3. if the URL contains a project_id or analysis_id, checks that it belongs to this user
     (404, not 403, so nobody can find out which ids exist)
"""
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .database import get_db
from .models import Analysis, Project
from .services import users
from .services.security import read_token


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def claim_legacy_projects(db: Session, user_id: int) -> None:
    """Projects with no owner (made before login existed) belong to the first account."""
    if user_id != users.first_user_id():
        return
    if db.scalar(select(Project.id).where(Project.owner_id.is_(None)).limit(1)) is None:
        return
    db.execute(update(Project).where(Project.owner_id.is_(None)).values(owner_id=user_id))
    db.commit()


def require_user(
    request: Request,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Please log in.")
    uid = read_token(authorization[7:].strip())
    user = users.get_user(uid) if uid is not None else None
    if not user:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")

    claim_legacy_projects(db, user["id"])

    project_id = _int(request.path_params.get("project_id"))
    if project_id is not None:
        row = db.execute(select(Project.owner_id).where(Project.id == project_id)).first()
        if row is not None and row[0] != user["id"]:
            raise HTTPException(status_code=404, detail="Project not found")

    analysis_id = _int(request.path_params.get("analysis_id"))
    if analysis_id is not None:
        row = db.execute(
            select(Project.owner_id).join(Analysis, Analysis.project_id == Project.id).where(Analysis.id == analysis_id)
        ).first()
        if row is not None and row[0] != user["id"]:
            raise HTTPException(status_code=404, detail="Analysis not found")
    return user