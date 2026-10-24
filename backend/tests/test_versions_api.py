
"""Requirement versions: v1 has no analysis, v2 is compared with v1, v3 with v2."""
import pytest
 
pytest.importorskip("httpx")
pytest.importorskip("multipart")
 
try:
    from tests.test_ownership import env, make_project, signup  # noqa: F401
except ImportError:
    from test_ownership import env, make_project, signup  # noqa: F401
 
V1 = "OTP must expire in 10 minutes.\nUsers can reset the password by email.\n"
V2 = "OTP must expire in 5 minutes.\nUsers can reset the password by email.\n"
V3 = "OTP must expire in 3 minutes.\nUsers can reset the password by email.\n"
 
 
def up(client, headers, pid, name, text):
    return client.post(
        f"/projects/{pid}/versions",
        files={"file": (name, text.encode(), "text/plain")},
        headers=headers,
    )
 
 
def auth(headers):
    return headers
 
 
def test_first_version_has_no_analysis(env):
    c, _ = env
    t = signup(c, "a@x.io")
    pid = make_project(c, t)
    r = up(c, t, pid, "req_v1.txt", V1)
    assert r.status_code == 200
    body = r.json()
    assert body["number"] == 1 and body["analysis_id"] is None and body["change_count"] == 0
 
 
def test_second_version_is_compared_with_first(env):
    c, _ = env
    t = signup(c, "a@x.io")
    pid = make_project(c, t)
    up(c, t, pid, "req_v1.txt", V1)
    r = up(c, t, pid, "req_v2.txt", V2).json()
    assert r["number"] == 2
    assert r["change_count"] == 1
    assert r["analysis_id"] is not None
    assert r["risk_level"] in ("low", "medium", "high")
    # the saved analysis opens on the normal analysis page API
    a = c.get(f"/analyses/{r['analysis_id']}", headers=auth(t))
    assert a.status_code == 200 and a.json()["change_count"] == 1
 
 
def test_third_version_compares_with_second_not_first(env):
    c, _ = env
    t = signup(c, "a@x.io")
    pid = make_project(c, t)
    up(c, t, pid, "v1.txt", V1)
    up(c, t, pid, "v2.txt", V2)
    r3 = up(c, t, pid, "v3.txt", V3).json()
    a = c.get(f"/analyses/{r3['analysis_id']}", headers=auth(t)).json()
    assert "5 minutes" in a["old_text"] and "3 minutes" in a["new_text"]
 
 
def test_list_is_in_order(env):
    c, _ = env
    t = signup(c, "a@x.io")
    pid = make_project(c, t)
    for i, txt in enumerate((V1, V2, V3), 1):
        up(c, t, pid, f"v{i}.txt", txt)
    rows = c.get(f"/projects/{pid}/versions", headers=auth(t)).json()
    assert [r["number"] for r in rows] == [1, 2, 3]
 
 
def test_bad_file_type_is_rejected(env):
    c, _ = env
    t = signup(c, "a@x.io")
    pid = make_project(c, t)
    r = up(c, t, pid, "notes.pdf", "x")
    assert r.status_code == 422
 
 
def test_versions_are_private(env):
    c, _ = env
    t1 = signup(c, "a@x.io")
    t2 = signup(c, "b@x.io")
    pid = make_project(c, t1)
    up(c, t1, pid, "v1.txt", V1)
    assert c.get(f"/projects/{pid}/versions", headers=auth(t2)).status_code == 404
    assert up(c, t2, pid, "v2.txt", V2).status_code == 404
 
 
def test_login_required(env):
    assert env[0].get("/projects/1/versions").status_code == 401
 

