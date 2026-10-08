import time

SESSION_TIMEOUT_MINUTES = 30


def create_session(user_id):
    return {"user": user_id, "started": time.time()}


def is_session_expired(session):
    """A session expires after a period of inactivity."""
    idle = (time.time() - session["started"]) / 60
    return idle > SESSION_TIMEOUT_MINUTES


def refresh_session(session):
    session["started"] = time.time()
    return session