import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (tables register karne ke liye)
from .database import Base, engine
from .migrate import ensure_owner_column
from .wiring import include_all

Base.metadata.create_all(bind=engine)
ensure_owner_column(engine)  # old driftai.db files get the new owner_id column

app = FastAPI(title="DriftAI API", version="0.5.0")

# Frontend origins that may call this API (comma separated)
origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],  # lets the browser read the download file name
)

include_all(app)


@app.get("/health")
def health():
    return {"status": "ok", "app": "DriftAI"}