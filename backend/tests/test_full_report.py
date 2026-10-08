from datetime import datetime

from app.services.full_report import build_full_markdown

RESULT = {
    "changes": [{"entity": "OTP", "property": "expires", "old_value": "10 minutes", "new_value": "5 minutes"}],
    "action_plan": [{"text": "Change 10 minutes -> 5 minutes at auth.py:1", "confidence": "high",
                     "reason": "old value found: 600", "evidence": "OTP_EXPIRY_SECONDS = 600"}],
    "risk": {"score": 85, "level": "high", "reasons": ["Touches a sensitive area: login, otp"]},
}
FN = [{"entity": "OTP", "property": "expires", "old_value": "10 minutes", "new_value": "5 minutes",
       "matches": [{"qualname": "OTP_EXPIRY_SECONDS", "kind": "constant", "confidence": "high",
                    "path": "auth.py", "start_line": 1, "end_line": 1, "reasons": ["contains old value: 600"]}],
       "weak_matches": []}]


def test_full_report_has_all_sections():
    md = build_full_markdown(4, "shop_demo", datetime(2026, 10, 6, 8, 11), RESULT, FN)
    assert "# DriftAI report: analysis #4" in md
    assert "**Risk: HIGH (85/100)**" in md
    assert "| OTP | expires | 10 minutes | 5 minutes |" in md
    assert "- [ ] Change 10 minutes -> 5 minutes at auth.py:1 (confidence: high)" in md
    assert "**OTP_EXPIRY_SECONDS** (constant, high) at `auth.py:1-1`" in md


def test_full_report_handles_empty_result():
    md = build_full_markdown(1, "x", None, {}, [])
    assert "No requirement changes were detected." in md
    assert "No function-level data." in md


def test_no_strong_match_message_mentions_hidden_weak():
    fn = [{"entity": "a", "property": "b", "old_value": "1", "new_value": "2",
           "matches": [], "weak_matches": [{"qualname": "x"}]}]
    md = build_full_markdown(1, "x", None, {}, fn)
    assert "No strong match found. (1 weak match(es) were hidden)" in md