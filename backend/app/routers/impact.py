from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ImpactRequest, ImpactResponse
from ..services.drift import detect_drift
from ..services.impact import analyze_impact
from .projects import get_project_or_404

router = APIRouter(prefix="/projects", tags=["impact"])


@router.post("/{project_id}/impact", response_model=ImpactResponse)
def impact(project_id: int, body: ImpactRequest, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    files = [{"path": f.path, "content": f.content} for f in project.files]
    changes = detect_drift(body.old_text, body.new_text)
    results = analyze_impact(files, changes)
    distinct = {f["path"] for r in results for f in r["files"]}
    return ImpactResponse(project_id=project.id, changes=results, total_files=len(distinct))