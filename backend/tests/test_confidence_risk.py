from app.services.drift import detect_drift
from app.services.impact import analyze_impact
from app.services.plan import build_action_plan
from app.services.risk import compute_risk

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
TEST = {
    "path": "test_auth.py",
    "content": (
        "def test_otp_expired_after_ten_minutes():\n"
        "    assert verify_otp('9', '1', age_seconds=601) is False\n"
    ),
}
DOC = {"path": "README.md", "content": "- OTP expires in 10 minutes after it is sent.\n"}
SHOP = {"path": "shop.py", "content": "def checkout(cart):\n    return sum(cart)\n"}

OTP_CHANGES = detect_drift("OTP expires in 10 minutes.", "OTP expires in 5 minutes.")


def run(files, changes):
    results = analyze_impact(files, changes)
    return results, build_action_plan(results)


def test_literal_match_is_high_confidence():
    _, plan = run([AUTH, TEST, DOC], OTP_CHANGES)
    by_path = {i["path"]: i for i in plan if i["path"]}
    assert by_path["auth.py"]["confidence"] == "high"
    assert by_path["README.md"]["confidence"] == "high"
    assert "600" in by_path["auth.py"]["reason"]


def test_weak_match_is_low_confidence():
    _, plan = run([TEST], OTP_CHANGES)
    assert plan[0]["confidence"] == "low"
    assert "matched keywords" in plan[0]["reason"]


def test_sensitive_change_is_high_risk():
    results, plan = run([AUTH], OTP_CHANGES)
    risk = compute_risk(results, plan)
    assert risk["level"] == "high"
    assert any("sensitive" in reason.lower() for reason in risk["reasons"])


def test_plain_change_is_low_risk():
    changes = detect_drift("Page size is 10 items.", "Page size is 20 items.")
    results, plan = run([SHOP], changes)
    assert compute_risk(results, plan)["level"] == "low"