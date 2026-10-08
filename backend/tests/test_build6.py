"""Build 6: login lockout, change password, /stats."""
import pytest

pytest.importorskip("httpx")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import Analysis, Feedback, Project
from app.services import ratelimit
from app.wiring import include_all


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIFTAI_USERS_DB", str(tmp_path / "users.db"))
    monkeypatch.setenv("DRIFTAI_SECRET", "test-secret")
    ratelimit.reset_all()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    include_all(app)
    app.dependency_overrides[get_db] = override
    return TestClient(app), Session


def signup(c, email, name="U"):
    r = c.post("/auth/signup", json={"name": name, "email": email, "password": "longenough1"})
    return r.json()["token"], r.json()["user"]["id"]


def auth(t):
    return {"Authorization": f"Bearer {t}"}


def test_lockout_after_five_wrong_passwords(env):
    c, _ = env
    signup(c, "a@x.io")
    for _ in range(5):
        assert c.post("/auth/login", json={"email": "a@x.io", "password": "wrong-pass"}).status_code == 401
    r = c.post("/auth/login", json={"email": "a@x.io", "password": "longenough1"})
    assert r.status_code == 429 and "Retry-After" in r.headers          # even the right password waits


def test_success_clears_failure_count(env):
    c, _ = env
    signup(c, "a@x.io")
    for _ in range(4):
        c.post("/auth/login", json={"email": "a@x.io", "password": "bad-password"})
    assert c.post("/auth/login", json={"email": "a@x.io", "password": "longenough1"}).status_code == 200
    for _ in range(4):
        assert c.post("/auth/login", json={"email": "a@x.io", "password": "bad-password"}).status_code == 401


def test_change_password(env):
    c, _ = env
    t, _ = signup(c, "a@x.io")
    body = {"current_password": "nope-nope", "new_password": "brandnew123"}
    assert c.post("/auth/password", json=body, headers=auth(t)).status_code == 400
    body["current_password"] = "longenough1"
    assert c.post("/auth/password", json=body, headers=auth(t)).status_code == 200
    assert c.post("/auth/login", json={"email": "a@x.io", "password": "longenough1"}).status_code == 401
    assert c.post("/auth/login", json={"email": "a@x.io", "password": "brandnew123"}).status_code == 200
    assert c.post("/auth/password", json=body).status_code == 401


def test_stats_counts_only_own_data(env):
    c, Session = env
    t1, u1 = signup(c, "a@x.io")
    t2, u2 = signup(c, "b@x.io")
    db = Session()
    p1 = Project(name="Mine", owner_id=u1)
    p2 = Project(name="Theirs", owner_id=u2)
    db.add_all([p1, p2]); db.flush()
    res = lambda lvl: {"changes": [], "action_plan": [], "risk": {"score": 1, "level": lvl, "reasons": []}}
    a1 = Analysis(project_id=p1.id, old_text="o", new_text="n", result=res("high"), change_count=3, file_count=2)
    a2 = Analysis(project_id=p1.id, old_text="o", new_text="n", result=res("low"), change_count=1, file_count=2)
    a3 = Analysis(project_id=p2.id, old_text="o", new_text="n", result=res("medium"), change_count=9, file_count=1)
    db.add_all([a1, a2, a3]); db.flush()
    db.add_all([Feedback(analysis_id=a1.id, item_key="k", verdict="relevant"),
                Feedback(analysis_id=a3.id, item_key="k", verdict="not_relevant")])
    db.commit(); db.close()

    s = c.get("/stats", headers=auth(t1)).json()
    assert s["projects"] == 1 and s["analyses"] == 2 and s["changes_found"] == 4
    assert s["risk_levels"] == {"low": 1, "medium": 0, "high": 1}
    assert s["feedback"] == {"relevant": 1, "not_relevant": 0}
    assert s["top_projects"][0]["name"] == "Mine" and len(s["recent"]) == 2
    assert c.get("/stats").status_code == 401


def test_stats_for_new_user_is_empty(env):
    c, _ = env
    t, _ = signup(c, "a@x.io")
    s = c.get("/stats", headers=auth(t)).json()
    assert s["projects"] == 0 and s["analyses"] == 0 and s["recent"] == []