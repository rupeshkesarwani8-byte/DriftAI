"""POST /projects/{project_id}/functions  ->  function-level impact for pasted text."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.fn_schemas import FunctionChange, FunctionResponse
from app.models import Project
from app.services.astmatch import build_index
from app.services.drift import detect_drift
from app.services.fnimpact import file_pairs, functions_for_changes

router = APIRouter(tags=["functions"])


class FunctionRequest(BaseModel):
    old_text: str = Field(min_length=1)
    new_text: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)


@router.post("/projects/{project_id}/functions", response_model=FunctionResponse)
def function_impact(project_id: int, body: FunctionRequest, db: Session = Depends(get_db)):
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    units = build_index(file_pairs(db, project_id))
    changes = detect_drift(body.old_text, body.new_text)
    items = functions_for_changes(units, changes, body.top_k)
    return FunctionResponse(project_id=project_id, units_indexed=len(units),
                            changes=[FunctionChange(**i) for i in items])