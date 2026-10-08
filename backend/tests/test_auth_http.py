"""Real HTTP-level checks of the auth router (status codes, token flow, CORS preflight)."""
import pytest

pytest.importorskip("httpx")   # needed by FastAPI TestClient: pip install httpx

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.routers import auth


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIFTAI_USERS_DB", str(tmp_path / "users.db"))
    monkeypatch.setenv("DRIFTAI_SECRET", "test-secret")
    app = FastAPI()
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(auth.router)
    return TestClient(app)


def test_http_signup_login_me(client):
    r = client.post("/auth/signup", json={"name": "Rupesh", "email": "r@x.io", "password": "longenough1"})
    assert r.status_code == 200
    token = r.json()["token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["user"]["email"] == "r@x.io"
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    assert client.post("/auth/signup", json={"name": "R", "email": "r@x.io", "password": "longenough1"}).status_code == 409
    assert client.post("/auth/login", json={"email": "r@x.io", "password": "wrongwrong"}).status_code == 401
    assert client.post("/auth/signup", json={"name": "R", "email": "a@b.co", "password": "short"}).status_code == 422


def test_http_cors_preflight_allows_authorization_header(client):
    r = client.options("/auth/me", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert r.status_code == 200
    assert "authorization" in r.headers["access-control-allow-headers"].lower()