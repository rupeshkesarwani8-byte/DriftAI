from fastapi import APIRouter

from ..schemas import DriftRequest, DriftResponse
from ..services.drift import detect_drift

router = APIRouter(prefix="/drift", tags=["drift"])


@router.post("/detect", response_model=DriftResponse)
def detect(body: DriftRequest):
    changes = detect_drift(body.old_text, body.new_text)
    return DriftResponse(changes=changes, count=len(changes))