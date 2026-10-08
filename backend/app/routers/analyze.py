from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_user
from ..models import Analysis
from ..schemas import AnalyzeResponse, ImpactRequest
from ..services.drift import detect_drift
from ..services.impact import analyze_impact
from ..services.plan import build_action_plan
from ..services.risk import compute_risk
from .projects import get_project_or_404

router = APIRouter(prefix="/projects", tags=["analyze"])


@router.post("/{project_id}/analyze", response_model=AnalyzeResponse)
def analyze(
    project_id: int, body: ImpactRequest, db: Session = Depends(get_db), user: dict = Depends(require_user)
):
    project = get_project_or_404(db, project_id, user)
    files = [{"path": f.path, "content": f.content} for f in project.files]

    changes = detect_drift(body.old_text, body.new_text)
    results = analyze_impact(files, changes)
    plan = build_action_plan(results)
    risk = compute_risk(results, plan)
    distinct = {f["path"] for r in results for f in r["files"]}

    analysis = Analysis(
        project_id=project.id,
        old_text=body.old_text,
        new_text=body.new_text,
        result={
            "changes": results,
            "action_plan": plan,
            "risk": risk,
            "total_files": len(distinct),
        },
        change_count=len(changes),
        file_count=len(distinct),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return AnalyzeResponse(
        analysis_id=analysis.id,
        project_id=project.id,
        changes=results,
        action_plan=plan,
        risk=risk,
        total_files=len(distinct),
    )