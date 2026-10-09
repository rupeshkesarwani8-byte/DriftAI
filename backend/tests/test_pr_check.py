"""Build 12: the pull-request check (pr_check.py)."""
import shutil
import subprocess

import pytest

import pr_check
from app.services.astmatch import build_index

CODE = '''
TOKEN_TTL_SECONDS = 7 * 24 * 3600  # 7 days

def make_token(user_id):
    """Create a login token that is valid for 7 days."""
    return user_id

def unrelated_helper(x):
    return x
'''

CHANGE = {"entity": "login token", "property": "validity", "old_value": "7 days", "new_value": "1 day",
          "old_sentence": "A login token is valid for 7 days.", "new_sentence": "A login token is valid for 1 day."}


def test_analyse_finds_the_token_code(monkeypatch):
    monkeypatch.setattr(pr_check, "detect_drift", lambda old, new: [CHANGE])
    units = build_index([("auth.py", CODE)])
    res = pr_check.analyse("old", "new", units)
    names = [m.unit.qualname for m in res[0]["matches"]]
    assert "TOKEN_TTL_SECONDS" in names or "make_token" in names
    assert "unrelated_helper" not in names


def test_render_has_marker_and_location(monkeypatch):
    monkeypatch.setattr(pr_check, "detect_drift", lambda old, new: [CHANGE])
    units = build_index([("auth.py", CODE)])
    md = pr_check.render({"REQUIREMENTS.md": pr_check.analyse("o", "n", units)}, [])
    assert md.startswith(pr_check.MARKER)
    assert "`auth.py`" in md and "7 days" in md and "1 day" in md


def test_render_without_changed_files():
    assert "nothing to check" in pr_check.render({}, [])


def test_no_match_says_check_by_hand(monkeypatch):
    monkeypatch.setattr(pr_check, "detect_drift", lambda old, new: [CHANGE])
    units = build_index([("other.py", "def paint(x):\n    return x\n")])
    md = pr_check.render({"R.md": pr_check.analyse("o", "n", units)}, [])
    assert "check the code by hand" in md


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_end_to_end_on_a_real_git_repo(tmp_path, monkeypatch):
    def g(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    g("init", "-q", "-b", "main")
    g("config", "user.email", "t@t.t")
    g("config", "user.name", "t")
    (tmp_path / "auth.py").write_text(CODE, encoding="utf-8")
    (tmp_path / "REQUIREMENTS.md").write_text("A login token is valid for 7 days.\n", encoding="utf-8")
    g("add", "-A")
    g("commit", "-qm", "base")
    g("checkout", "-qb", "change")
    (tmp_path / "REQUIREMENTS.md").write_text("A login token is valid for 1 day.\n", encoding="utf-8")
    g("commit", "-qam", "change")
    monkeypatch.setattr(pr_check, "detect_drift", lambda old, new: [CHANGE] if old != new else [])
    out = tmp_path / "comment.md"
    assert pr_check.main(["--base", "main", "--head", "change", "--repo", str(tmp_path), "--out", str(out)]) == 0
    md = out.read_text(encoding="utf-8")
    assert "REQUIREMENTS.md" in md and "auth.py" in md 