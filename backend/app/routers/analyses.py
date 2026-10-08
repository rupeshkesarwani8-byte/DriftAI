from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_user
from ..models import Analysis, Feedback, Project
from ..schemas import AnalysisDetail, AnalysisSummary, FeedbackIn
from ..services.report import build_markdown

router = APIRouter(tags=["analyses"])


def get_analysis_or_404(db: Session, analysis_id: int, user: dict | None = None) -> Analysis:
    """404 if missing. If `user` is given, also 404 when the analysis belongs to someone else's project."""
    analysis = db.get(Analysis, analysis_id)
    if analysis is None or (user is not None and analysis.project.owner_id != user["id"]):
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


def _utc(analysis: Analysis):
    created = analysis.created_at
    return created if created.tzinfo else created.replace(tzinfo=timezone.utc)


def summary_of(analysis: Analysis) -> dict:
    return {
        "id": analysis.id,
        "project_id": analysis.project_id,
        "project_name": analysis.project.name,
        "change_count": analysis.change_count,
        "file_count": analysis.file_count,
        "created_at": _utc(analysis),
    }


@router.get("/analyses", response_model=list[AnalysisSummary])
def list_analyses(
    limit: int = Query(20, ge=1, le=100),
    project_id: int | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    query = (
        select(Analysis)
        .join(Project, Analysis.project_id == Project.id)
        .where(Project.owner_id == user["id"])
        .order_by(Analysis.id.desc())
        .limit(limit)
    )
    if project_id is not None:
        query = query.where(Analysis.project_id == project_id)
    return [summary_of(a) for a in db.scalars(query)]


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(analysis_id: int, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    analysis = get_analysis_or_404(db, analysis_id, user)
    return {
        **summary_of(analysis),
        "old_text": analysis.old_text,
        "new_text": analysis.new_text,
        **analysis.result,
        "feedback": {f.item_key: f.verdict for f in analysis.feedback},
    }


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: int, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    db.delete(get_analysis_or_404(db, analysis_id, user))
    db.commit()


@router.put("/analyses/{analysis_id}/feedback", status_code=204)
def set_feedback(
    analysis_id: int, body: FeedbackIn, db: Session = Depends(get_db), user: dict = Depends(require_user)
):
    """Human-in-the-loop: the person says whether a suggestion was relevant."""
    analysis = get_analysis_or_404(db, analysis_id, user)
    existing = db.scalar(
        select(Feedback).where(
            Feedback.analysis_id == analysis.id, Feedback.item_key == body.item_key
        )
    )
    if body.verdict == "none":
        if existing:
            db.delete(existing)
    elif existing:
        existing.verdict = body.verdict
    else:
        db.add(Feedback(analysis_id=analysis.id, item_key=body.item_key, verdict=body.verdict))
    db.commit()


@router.get("/analyses/{analysis_id}/export.md", response_class=PlainTextResponse)
def export_markdown(analysis_id: int, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    analysis = get_analysis_or_404(db, analysis_id, user)
    when = _utc(analysis).strftime("%Y-%m-%d %H:%M UTC")
    text = build_markdown(analysis.project.name, when, analysis.result)
    return PlainTextResponse(
        text,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="driftai-report-{analysis.id}.md"'},
    )