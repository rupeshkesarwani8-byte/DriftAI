"""Which routers exist, and which of them need a logged-in user (Build 5c)."""
from fastapi import Depends, FastAPI

from .deps import require_user
from .routers import (
    analyses, analysis_functions, analyze, auth, drift, functions, github, impact, projects, stats,
)

# Every data route is protected. Only /auth/* (login, signup) and /health stay open.
PROTECTED = [
    projects.router, drift.router, impact.router, analyze.router, analyses.router,
    analysis_functions.router, functions.router, github.router, stats.router,
]


def include_all(app: FastAPI) -> None:
    for r in PROTECTED:
        app.include_router(r, dependencies=[Depends(require_user)])
    app.include_router(auth.router)