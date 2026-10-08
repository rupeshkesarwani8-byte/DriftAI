"""Login lockout (Build 6): too many wrong passwords for one email -> wait a while.

Kept in memory on purpose: simple, no extra table. It resets when the server restarts.
"""
import threading
import time

MAX_FAILURES = 5          # wrong passwords allowed ...
WINDOW_SECONDS = 15 * 60  # ... inside this window
LOCK_SECONDS = 15 * 60    # then locked for this long

_lock = threading.Lock()
_failures: dict[str, list[float]] = {}
_locked_until: dict[str, float] = {}


def _now() -> float:
    return time.time()


def seconds_locked(key: str) -> int:
    """0 if the key may try to log in, otherwise how many seconds remain."""
    with _lock:
        until = _locked_until.get(key, 0.0)
        left = until - _now()
        if left <= 0:
            _locked_until.pop(key, None)
            return 0
        return int(left) + 1


def record_failure(key: str) -> None:
    with _lock:
        now = _now()
        recent = [t for t in _failures.get(key, []) if now - t < WINDOW_SECONDS]
        recent.append(now)
        _failures[key] = recent
        if len(recent) >= MAX_FAILURES:
            _locked_until[key] = now + LOCK_SECONDS
            _failures.pop(key, None)


def record_success(key: str) -> None:
    with _lock:
        _failures.pop(key, None)
        _locked_until.pop(key, None)


def reset_all() -> None:
    """Used by tests."""
    with _lock:
        _failures.clear()
        _locked_until.clear()