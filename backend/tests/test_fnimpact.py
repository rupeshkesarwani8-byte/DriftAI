from types import SimpleNamespace

from app.services.astmatch import build_index
from app.services.fnimpact import functions_for_changes, get_field

SRC = '''
OTP_EXPIRY_SECONDS = 600
def verify_otp(code, age):
    return age <= OTP_EXPIRY_SECONDS
def unrelated_helper():
    return 600
'''


def test_get_field_works_for_dict_and_object():
    assert get_field({"old": "10"}, "old_value", "old") == "10"
    assert get_field(SimpleNamespace(old_value="7"), "old_value", "old") == "7"
    assert get_field({}, "x", default="-") == "-"


def test_strong_and_weak_are_split():
    units = build_index([("auth.py", SRC)])
    changes = [{"entity": "OTP", "property": "expires", "old_value": "10 minutes", "new_value": "5 minutes"}]
    out = functions_for_changes(units, changes)
    assert out[0]["matches"][0]["qualname"] == "OTP_EXPIRY_SECONDS"
    assert all(m["confidence"] != "low" for m in out[0]["matches"])
    weak_names = [m["qualname"] for m in out[0]["weak_matches"]]
    assert "unrelated_helper" in weak_names          # only the number 600 matched


def test_no_match_returns_empty_lists():
    units = build_index([("auth.py", SRC)])
    out = functions_for_changes(units, [SimpleNamespace(entity="delivery fee", property="waived above",
                                                        old_value="999 rupees", new_value="1499 rupees")])
    assert out[0]["matches"] == []