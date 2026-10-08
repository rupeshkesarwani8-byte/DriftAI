"""POST /import/github  ->  create a project from a public GitHub repository (Build 4)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_user
from app.models import CodeFile, Project
from app.services.github_import import GitHubImportError, fetch_repo_files

router = APIRouter(tags=["github"])


class GithubImportRequest(BaseModel):
    url: str = Field(min_length=3, max_length=300)
    name: str | None = Field(default=None, max_length=120)
    branch: str | None = Field(default=None, max_length=120)
    replace: bool = False               # True = refresh the files of an existing project with the same name


class GithubImportResponse(BaseModel):
    project_id: int
    name: str
    repo: str
    branch: str | None
    files_imported: int
    skipped: dict[str, int]
    notes: list[str]
    replaced: bool = False


def make_code_file(project_id: int, path: str, content: str) -> CodeFile:
    """Build a CodeFile row without assuming exact column names (works with models.py as is)."""
    cols = list(CodeFile.__table__.columns)
    names = {c.name for c in cols}
    path_col = next((n for n in ("path", "filename", "name") if n in names), None)
    content_col = next((n for n in ("content", "text", "source") if n in names), None)
    if path_col is None or content_col is None:
        raise RuntimeError("CodeFile model has no path/content column")
    values = {"project_id": project_id, path_col: path, content_col: content}
    if "name" in names and path_col != "name":
        values["name"] = path.rsplit("/", 1)[-1]
    for c in cols:                     # fill other required columns with harmless values
        if c.name in values or c.primary_key or c.nullable:
            continue
        if c.default is not None or c.server_default is not None:
            continue
        kind = str(c.type).upper()
        if "INT" in kind:
            values[c.name] = len(content.encode("utf-8"))
        elif "DATE" in kind or "TIME" in kind:
            values[c.name] = datetime.now(timezone.utc)
        else:
            values[c.name] = ""
    if "size" in names and "size" not in values:
        values["size"] = len(content.encode("utf-8"))
    return CodeFile(**values)


@router.post("/import/github", response_model=GithubImportResponse)
def import_github(body: GithubImportRequest, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    try:
        ref, files, stats = fetch_repo_files(body.url, body.branch)
    except GitHubImportError as e:
        raise HTTPException(status_code=400, detail=str(e))

    project_name = (body.name or "").strip() or f"{ref.owner}/{ref.repo}"
    existing = (db.query(Project)
                .filter(Project.name == project_name, Project.owner_id == user["id"])
                .first())
    if existing is not None and not body.replace:
        raise HTTPException(
            status_code=409,
            detail=f'A project named "{project_name}" already exists (#{existing.id}). '
                   "Replace its files with the fresh download, or type a different project name.")
    try:
        if existing is not None:
            project = existing
            db.query(CodeFile).filter(CodeFile.project_id == project.id).delete()
        else:
            project = Project(name=project_name, owner_id=user["id"])
            db.add(project)
            db.flush()                  # get project.id
        for path, content in files:
            db.add(make_code_file(project.id, path, content))
        db.commit()
    except Exception as e:              # keep the database clean if anything fails
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Could not save the imported files: {e}")

    return GithubImportResponse(
        project_id=project.id, name=project_name, repo=f"{ref.owner}/{ref.repo}", branch=ref.branch,
        files_imported=stats.imported,
        skipped={"ignored_folders": stats.skipped_dirs, "unsupported_type": stats.skipped_type,
                 "too_big": stats.skipped_big, "binary": stats.skipped_binary,
                 "over_limit": stats.skipped_limit},
        notes=stats.notes, replaced=existing is not None,
    )