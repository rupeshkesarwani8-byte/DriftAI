
"""Requirement versions: upload v1, v2, v3 ... and see what drifted between them."""
from datetime import timezone
 
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
 
from ..database import get_db
from ..deps import require_user
from ..models import Analysis, RequirementVersion
from ..schemas import VersionOut
from ..services.docparse import DocumentError, read_document
from ..services.drift import detect_drift
from ..services.impact import analyze_impact
from ..services.plan import build_action_plan
from ..services.risk import compute_risk
from .projects import get_project_or_404
 
router = APIRouter(prefix="/projects", tags=["versions"])
 
 
def _out(db: Session, v: RequirementVersion) -> VersionOut:
    created = v.created_at if v.created_at.tzinfo else v.created_at.replace(tzinfo=timezone.utc)
    out = VersionOut(id=v.id, number=v.number, filename=v.filename, created_at=created)
    analysis = db.get(Analysis, v.analysis_id) if v.analysis_id else None
    if analysis is not None:
        risk = (analysis.result or {}).get("risk") or {}
        out.analysis_id = analysis.id
        out.change_count = analysis.change_count
        out.file_count = analysis.file_count
        out.risk_score = risk.get("score")
        out.risk_level = risk.get("level")
    return out
 
 
@router.get("/{project_id}/versions", response_model=list[VersionOut])
def list_versions(project_id: int, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    project = get_project_or_404(db, project_id, user)
    return [_out(db, v) for v in project.versions]
 
 
@router.post("/{project_id}/versions", response_model=VersionOut)
async def upload_version(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    project = get_project_or_404(db, project_id, user)
    name = (file.filename or "requirements.txt").replace("\\", "/").split("/")[-1]
    try:
        text = read_document(name, await file.read())
    except DocumentError as e:
        raise HTTPException(status_code=422, detail=str(e))
 
    previous = project.versions[-1] if project.versions else None
    version = RequirementVersion(
        project_id=project.id,
        number=(previous.number + 1) if previous else 1,
        filename=name,
        text=text,
    )
 
    if previous is not None:
        files = [{"path": f.path, "content": f.content} for f in project.files]
        changes = detect_drift(previous.text, text)
        results = analyze_impact(files, changes)
        plan = build_action_plan(results)
        risk = compute_risk(results, plan)
        distinct = {f["path"] for r in results for f in r["files"]}
        analysis = Analysis(
            project_id=project.id,
            old_text=previous.text,
            new_text=text,
            result={"changes": results, "action_plan": plan, "risk": risk, "total_files": len(distinct)},
            change_count=len(changes),
            file_count=len(distinct),
        )
        db.add(analysis)
        db.flush()
        version.analysis_id = analysis.id
 
    db.add(version)
    db.commit()
    db.refresh(version)
    return _out(db, version)
 

