from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.services import ratelimit, users
from app.services.security import hash_password, make_token, read_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(max_length=200)
    password: str = Field(min_length=8, max_length=200)


class LoginIn(BaseModel):
    email: str
    password: str


class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)


def public(user: dict) -> dict:
    return {"id": user["id"], "name": user["name"], "email": user["email"]}


def current_user(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Please log in.")
    uid = read_token(authorization[7:].strip())
    user = users.get_user(uid) if uid is not None else None
    if not user:
        raise HTTPException(401, "Session expired. Please log in again.")
    return user


@router.post("/signup")
def signup(body: SignupIn):
    if not users.EMAIL_RE.match(body.email.strip()):
        raise HTTPException(422, "Please enter a valid email address.")
    user = users.create_user(body.email, body.name, hash_password(body.password))
    if user is None:
        raise HTTPException(409, "An account with this email already exists.")
    return {"token": make_token(user["id"]), "user": public(user)}


@router.post("/login")
def login(body: LoginIn):
    key = users.normalize_email(body.email)
    wait = ratelimit.seconds_locked(key)
    if wait:
        raise HTTPException(
            429,
            f"Too many failed attempts. Try again in {max(1, wait // 60)} minute(s).",
            headers={"Retry-After": str(wait)},
        )
    user = users.get_user_by_email(body.email)
    # Same message for unknown email and wrong password, so emails cannot be probed.
    if not user or not verify_password(body.password, user["password_hash"]):
        ratelimit.record_failure(key)
        raise HTTPException(401, "Incorrect email or password.")
    ratelimit.record_success(key)
    return {"token": make_token(user["id"]), "user": public(user)}


@router.get("/me")
def me(authorization: str | None = Header(default=None)):
    return {"user": public(current_user(authorization))}


@router.post("/password")
def change_password(body: PasswordIn, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(400, "Current password is incorrect.")
    if body.new_password == body.current_password:
        raise HTTPException(400, "New password must be different from the current one.")
    users.update_password(user["id"], hash_password(body.new_password))
    return {"ok": True}