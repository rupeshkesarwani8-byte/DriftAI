"""GET /stats - numbers for the logged-in user's dashboard (Build 6)."""
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_user
from app.models import Analysis, Feedback, Project

router = APIRouter(tags=["stats"])


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: dict = Depends(require_user)):
    uid = user["id"]
    projects = db.execute(select(Project.id, Project.name).where(Project.owner_id == uid)).all()
    names = {pid: name for pid, name in projects}

    analyses = db.execute(
        select(Analysis.id, Analysis.project_id, Analysis.change_count, Analysis.file_count,
               Analysis.result, Analysis.created_at)
        .where(Analysis.project_id.in_(names.keys()) if names else Analysis.id < 0)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
    ).all()

    levels: Counter = Counter()
    per_project: Counter = Counter()
    for a in analyses:
        risk = (a.result or {}).get("risk") or {}
        levels[risk.get("level", "low")] += 1
        per_project[a.project_id] += 1

    ids = [a.id for a in analyses]
    verdicts: Counter = Counter()
    if ids:
        for verdict, n in db.execute(
            select(Feedback.verdict, func.count()).where(Feedback.analysis_id.in_(ids)).group_by(Feedback.verdict)
        ):
            verdicts[verdict] = n

    return {
        "projects": len(names),
        "analyses": len(analyses),
        "changes_found": sum(a.change_count or 0 for a in analyses),
        "risk_levels": {k: levels.get(k, 0) for k in ("low", "medium", "high")},
        "feedback": {"relevant": verdicts.get("relevant", 0), "not_relevant": verdicts.get("not_relevant", 0)},
        "top_projects": [
            {"id": pid, "name": names[pid], "analyses": n} for pid, n in per_project.most_common(5)
        ],
        "recent": [
            {
                "id": a.id,
                "project": names.get(a.project_id, "?"),
                "changes": a.change_count or 0,
                "risk": ((a.result or {}).get("risk") or {}).get("level", "low"),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in analyses[:5]
        ],
    }