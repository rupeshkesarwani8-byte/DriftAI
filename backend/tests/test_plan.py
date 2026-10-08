from app.services.drift import detect_drift
from app.services.impact import analyze_impact
from app.services.plan import build_action_plan

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

CHANGES = detect_drift("OTP expires in 10 minutes.", "OTP expires in 5 minutes.")


def make_plan(files):
    return build_action_plan(analyze_impact(files, CHANGES))


def test_plan_order_is_code_test_doc_then_run():
    plan = make_plan([DOC, TEST, AUTH])
    assert [i["kind"] for i in plan] == ["code", "test", "doc", "run"]


def test_code_item_has_exact_location_and_values():
    first = make_plan([DOC, TEST, AUTH])[0]
    assert first["path"] == "auth.py"
    assert first["line"] == 1
    assert "10 minutes" in first["text"] and "5 minutes" in first["text"]
    assert "600" in first["evidence"]


def test_items_are_numbered():
    plan = make_plan([DOC, TEST, AUTH])
    assert [i["order"] for i in plan] == list(range(1, len(plan) + 1))


def test_no_match_gives_manual_item_not_a_guess():
    plan = make_plan([SHOP])
    assert len(plan) == 1
    assert plan[0]["kind"] == "manual"
    assert "insufficient evidence" in plan[0]["text"]