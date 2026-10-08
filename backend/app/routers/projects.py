from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_user
from ..models import CodeFile, Project
from ..schemas import ProjectCreate, ProjectDetail, ProjectOut, UploadResult

router = APIRouter(prefix="/projects", tags=["projects"])

ALLOWED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".md", ".txt", ".json", ".html", ".css"}
MAX_FILE_BYTES = 1_000_000  # 1 MB


def get_project_or_404(db: Session, project_id: int, user: dict | None = None) -> Project:
    """404 if the project does not exist. If `user` is given, also 404 when it belongs to someone else."""
    project = db.get(Project, project_id)
    if project is None or (user is not None and project.owner_id != user["id"]):
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=ProjectOut)
def create_project(body: ProjectCreate, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    project = Project(name=body.name.strip(), owner_id=user["id"])
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: dict = Depends(require_user)):
    return db.scalars(select(Project).where(Project.owner_id == user["id"]).order_by(Project.id.desc())).all()


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    return get_project_or_404(db, project_id, user)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    db.delete(get_project_or_404(db, project_id, user))
    db.commit()


@router.post("/{project_id}/files", response_model=UploadResult)
async def upload_files(
    project_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(require_user),
):
    project = get_project_or_404(db, project_id, user)
    saved: list[str] = []
    skipped: list[str] = []

    for f in files:
        name = (f.filename or "").replace("\\", "/")
        if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
            skipped.append(name)
            continue
        data = await f.read()
        if len(data) > MAX_FILE_BYTES:
            skipped.append(name)
            continue
        db.add(CodeFile(
            project_id=project.id,
            path=name,
            content=data.decode("utf-8", errors="ignore"),
        ))
        saved.append(name)

    db.commit()
    return UploadResult(saved=saved, skipped=skipped)