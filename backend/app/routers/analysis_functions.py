"""Function-level data and the full Markdown report for a SAVED analysis (Build 4.5)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.fn_schemas import FunctionChange, FunctionResponse
from app.models import Analysis, Project
from app.services.astmatch import build_index
from app.services.fnimpact import file_pairs, functions_for_changes
from app.services.full_report import build_full_markdown

router = APIRouter(tags=["analyses"])


def _load(db: Session, analysis_id: int, top_k: int):
    a = db.get(Analysis, analysis_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    result = a.result or {}
    units = build_index(file_pairs(db, a.project_id))
    items = functions_for_changes(units, result.get("changes", []), top_k)
    return a, result, units, items


@router.get("/analyses/{analysis_id}/functions", response_model=FunctionResponse)
def analysis_functions(analysis_id: int, top_k: int = Query(5, ge=1, le=10), db: Session = Depends(get_db)):
    a, _, units, items = _load(db, analysis_id, top_k)
    return FunctionResponse(project_id=a.project_id, units_indexed=len(units),
                            changes=[FunctionChange(**i) for i in items])


@router.get("/analyses/{analysis_id}/full-report.md")
def full_report(analysis_id: int, db: Session = Depends(get_db)):
    a, result, _, items = _load(db, analysis_id, 5)
    project = db.get(Project, a.project_id) if a.project_id is not None else None
    name = getattr(project, "name", None) or "Untitled project"
    text = build_full_markdown(a.id, name, a.created_at, result, items)
    return Response(content=text, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="driftai-analysis-{a.id}-full.md"'})