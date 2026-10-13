"""Tests to run (Build 14).

For every requirement change, list the tests that probably need a look:
  - tests that match the requirement directly (their own name or docstring talks about it), and
  - tests that call or mention one of the strongly matched functions or constants.
It only reads code. It never runs anything.
"""
from __future__ import annotations

import re

from app.services.impact import kind_of

MAX_TESTS = 8
MIN_NAME_LEN = 4


def _is_test_path(path: str) -> bool:
    return kind_of(path) == "test"


def _pytest_id(path: str, qualname: str) -> str | None:
    if not path.endswith(".py"):
        return None
    return f"{path}::{qualname.replace('.', '::')}"


def suggest_tests(units, fn_items: list[dict]) -> list[dict]:
    """fn_items = the output of functions_for_changes(). Returns one entry per change."""
    test_units = [u for u in units if _is_test_path(u.path) and u.kind != "constant"]
    out: list[dict] = []
    for item in fn_items:
        direct = [m for m in item["matches"] if _is_test_path(m["path"])]
        code = [m for m in item["matches"] if not _is_test_path(m["path"])]
        seen = {(m["path"], m["qualname"]) for m in direct}
        found: list[dict] = [{
            "path": m["path"], "qualname": m["qualname"],
            "start_line": m["start_line"], "end_line": m["end_line"],
            "reason": "matches the requirement directly",
            "pytest": _pytest_id(m["path"], m["qualname"]),
        } for m in direct]

        names = {m["qualname"].split(".")[-1] for m in code}
        for name in sorted(n for n in names if len(n) >= MIN_NAME_LEN):
            pattern = re.compile(rf"\b{re.escape(name)}\b")
            for u in test_units:
                key = (u.path, u.qualname)
                if key in seen or not pattern.search(u.source):
                    continue
                seen.add(key)
                found.append({
                    "path": u.path, "qualname": u.qualname,
                    "start_line": u.start, "end_line": u.end,
                    "reason": f"uses {name}",
                    "pytest": _pytest_id(u.path, u.qualname),
                })

        extra = max(0, len(found) - MAX_TESTS)
        tests = found[:MAX_TESTS]
        if tests:
            note = f"{extra} more test(s) not shown." if extra else ""
        elif code or direct:
            note = "No test was found for this change. Consider adding one."
        else:
            note = "No strong match was found, so no tests are suggested."
        out.append({"entity": item["entity"], "property": item["property"],
                    "old_value": item["old_value"], "new_value": item["new_value"],
                    "tests": tests, "note": note})
    return out