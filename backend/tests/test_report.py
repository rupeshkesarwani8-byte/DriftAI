from app.services.drift import detect_drift
from app.services.impact import analyze_impact
from app.services.plan import build_action_plan
from app.services.report import build_markdown

AUTH = {
    "path": "auth.py",
    "content": (
        "OTP_EXPIRY_SECONDS = 600  # OTP 10 minute me expire hota hai\n"
        "\n"
        "\n"
        "def verify_otp(phone, otp, age_seconds):\n"
        "    if age_seconds > OTP_EXPIRY_SECONDS:\n"
        "        return False\n"
        "    return True\n"
    ),
}


def make_result():
    changes = detect_drift("OTP expires in 10 minutes.", "OTP expires in 5 minutes.")
    results = analyze_impact([AUTH], changes)
    return {"changes": results, "action_plan": build_action_plan(results), "total_files": 1}


def test_report_has_all_sections():
    md = build_markdown("shop", "2026-10-06 00:00 UTC", make_result())
    assert md.startswith("# DriftAI report: shop")
    assert "## Requirement changes" in md
    assert "| value_change | OTP | expires | 10 minutes | 5 minutes |" in md
    assert "- [ ] Change 10 minutes → 5 minutes at auth.py:1" in md
    assert "## Affected files" in md


def test_report_without_changes():
    md = build_markdown("shop", "now", {"changes": [], "action_plan": [], "total_files": 0})
    assert "No requirement changes found." in md
    assert "No actions needed." in md
    assert "No matching files found." in md