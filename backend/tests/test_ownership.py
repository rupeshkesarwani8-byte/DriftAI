"""Build 5c: every user sees only their own projects and analyses."""
import pytest

pytest.importorskip("httpx")   # needed by FastAPI TestClient: pip install httpx

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.migrate import ensure_owner_column
from app.models import Analysis, Project
from app.wiring import include_all

RESULT = {"changes": [], "action_plan": [], "risk": {"score": 0, "level": "low", "reasons": []}, "total_files": 0}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIFTAI_USERS_DB", str(tmp_path / "users.db"))
    monkeypatch.setenv("DRIFTAI_SECRET", "test-secret")
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


def signup(client, email):
    r = client.post("/auth/signup", json={"name": email.split("@")[0], "email": email, "password": "longenough1"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def make_project(client, headers, name="demo"):
    r = client.post("/projects", json={"name": name}, headers=headers)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    up = client.post(f"/projects/{pid}/files", headers=headers,
                     files=[("files", ("auth.py", b"OTP_EXPIRY_SECONDS = 600\n", "text/plain"))])
    assert up.status_code == 200, up.text
    return pid


def add_analysis(Session, project_id):
    with Session() as db:
        a = Analysis(project_id=project_id, old_text="old", new_text="new", result=RESULT, change_count=0, file_count=0)
        db.add(a)
        db.commit()
        return a.id


def test_login_is_required(env):
    client, _ = env
    assert client.get("/projects").status_code == 401
    assert client.get("/analyses").status_code == 401
    assert client.post("/projects", json={"name": "x"}).status_code == 401
    assert client.get("/projects", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    assert client.get("/auth/me").status_code == 401          # auth routes themselves stay reachable


def test_projects_are_private(env):
    client, _ = env
    a, b = signup(client, "a@x.io"), signup(client, "b@x.io")
    pid = make_project(client, a)
    assert [p["id"] for p in client.get("/projects", headers=a).json()] == [pid]
    assert client.get("/projects", headers=b).json() == []
    assert client.get(f"/projects/{pid}", headers=a).status_code == 200
    assert client.get(f"/projects/{pid}", headers=b).status_code == 404
    assert client.delete(f"/projects/{pid}", headers=b).status_code == 404
    other = client.post(f"/projects/{pid}/files", headers=b, files=[("files", ("x.py", b"X=1", "text/plain"))])
    assert other.status_code == 404
    assert client.get("/projects/9999", headers=a).status_code == 404       # missing is still a plain 404
    assert client.delete(f"/projects/{pid}", headers=a).status_code == 204


def test_analyses_are_private(env):
    client, Session = env
    a, b = signup(client, "a@x.io"), signup(client, "b@x.io")
    pid = make_project(client, a)
    aid = add_analysis(Session, pid)

    assert [x["id"] for x in client.get("/analyses", headers=a).json()] == [aid]
    assert client.get("/analyses", headers=b).json() == []
    assert client.get(f"/analyses/{aid}", headers=a).status_code == 200
    assert client.get(f"/analyses/{aid}/functions", headers=a).status_code == 200

    for method, url, kw in [
        ("get", f"/analyses/{aid}", {}),
        ("get", f"/analyses/{aid}/functions", {}),
        ("get", f"/analyses/{aid}/full-report.md", {}),
        ("get", f"/analyses/{aid}/export.md", {}),
        ("put", f"/analyses/{aid}/feedback", {"json": {"item_key": "k", "verdict": "relevant"}}),
        ("delete", f"/analyses/{aid}", {}),
        ("post", f"/projects/{pid}/analyze", {"json": {"old_text": "a 1", "new_text": "a 2"}}),
        ("post", f"/projects/{pid}/functions", {"json": {"old_text": "a 1", "new_text": "a 2"}}),
        ("post", f"/projects/{pid}/impact", {"json": {"old_text": "a 1", "new_text": "a 2"}}),
    ]:
        r = getattr(client, method)(url, headers=b, **kw)
        assert r.status_code == 404, (method, url, r.status_code)


def test_owner_can_analyze_and_list(env):
    client, _ = env
    a = signup(client, "a@x.io")
    pid = make_project(client, a)
    r = client.post(f"/projects/{pid}/analyze", headers=a,
                    json={"old_text": "The session timeout is 30 minutes.", "new_text": "The session timeout is 45 minutes."})
    assert r.status_code == 200, r.text
    assert r.json()["analysis_id"] in [x["id"] for x in client.get("/analyses", headers=a).json()]


def test_old_projects_go_to_the_first_account_only(env):
    client, Session = env
    with Session() as db:                       # a project made before accounts existed
        db.add(Project(name="legacy"))
        db.commit()
    first = signup(client, "first@x.io")
    second = signup(client, "second@x.io")
    assert client.get("/projects", headers=second).json() == []
    assert [p["name"] for p in client.get("/projects", headers=first).json()] == ["legacy"]
    assert client.get("/projects", headers=second).json() == []              # still not shared later


def test_owner_id_column_is_added_to_an_old_database():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    with engine.begin() as con:
        con.execute(text("CREATE TABLE projects (id INTEGER PRIMARY KEY, name VARCHAR(120), created_at DATETIME)"))
        con.execute(text("INSERT INTO projects (name) VALUES ('old one')"))
    assert ensure_owner_column(engine) is True
    assert "owner_id" in {c["name"] for c in inspect(engine).get_columns("projects")}
    assert ensure_owner_column(engine) is False                             # second run changes nothing
    with engine.connect() as con:
        assert con.execute(text("SELECT name, owner_id FROM projects")).fetchall() == [("old one", None)]