import pytest
from fastapi import HTTPException

from app.routers import auth
from app.services import users
from app.services.security import hash_password, make_token, read_token, verify_password


@pytest.fixture(autouse=True)
def tmp_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIFTAI_USERS_DB", str(tmp_path / "users.db"))
    monkeypatch.setenv("DRIFTAI_SECRET", "test-secret")


def test_password_hash_and_verify():
    h = hash_password("correct horse")
    assert h != "correct horse" and h.startswith("scrypt$")
    assert verify_password("correct horse", h)
    assert not verify_password("wrong", h)
    assert hash_password("correct horse") != h  # random salt


def test_token_roundtrip_expiry_and_tamper():
    t = make_token(7, ttl=100, now=1000)
    assert read_token(t, now=1050) == 7
    assert read_token(t, now=1200) is None
    body, sig = t.split(".")
    assert read_token(body + "." + sig[:-2] + "xx", now=1050) is None
    assert read_token("garbage", now=1050) is None


def test_signup_login_me_flow():
    out = auth.signup(auth.SignupIn(name="Rupesh", email="Rupesh@Example.com", password="longenough1"))
    assert out["user"]["email"] == "rupesh@example.com"
    login = auth.login(auth.LoginIn(email="RUPESH@example.com", password="longenough1"))
    me = auth.me(authorization="Bearer " + login["token"])
    assert me["user"]["name"] == "Rupesh"
    assert "password" not in str(me)


def test_duplicate_wrong_password_bad_email_and_missing_token():
    auth.signup(auth.SignupIn(name="A", email="a@b.co", password="longenough1"))
    with pytest.raises(HTTPException) as e:
        auth.signup(auth.SignupIn(name="A", email="a@b.co", password="longenough1"))
    assert e.value.status_code == 409
    with pytest.raises(HTTPException) as e:
        auth.login(auth.LoginIn(email="a@b.co", password="nope-nope"))
    assert e.value.status_code == 401
    with pytest.raises(HTTPException) as e:
        auth.login(auth.LoginIn(email="nobody@b.co", password="nope-nope"))
    assert e.value.status_code == 401
    with pytest.raises(HTTPException) as e:
        auth.signup(auth.SignupIn(name="A", email="not-an-email", password="longenough1"))
    assert e.value.status_code == 422
    with pytest.raises(HTTPException) as e:
        auth.me(authorization=None)
    assert e.value.status_code == 401