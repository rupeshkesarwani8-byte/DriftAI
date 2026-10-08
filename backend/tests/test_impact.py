from app.services.drift import detect_drift
from app.services.impact import analyze_impact, kind_of

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
SHOP = {"path": "shop.py", "content": "def checkout(cart):\n    return sum(cart)\n"}

CHANGES = detect_drift("OTP expires in 10 minutes.", "OTP expires in 5 minutes.")


def test_finds_affected_file_with_converted_value():
    files = analyze_impact([AUTH, SHOP], CHANGES)[0]["files"]
    assert files[0]["path"] == "auth.py"
    assert any(e["literal"] and "600" in e["literal"] for e in files[0]["evidence"])
    assert all(f["path"] != "shop.py" for f in files)


def test_reports_function_name():
    files = analyze_impact([AUTH], CHANGES)[0]["files"]
    assert any(e["function"] == "verify_otp" for e in files[0]["evidence"])


def test_unrelated_project_has_no_impact():
    assert analyze_impact([SHOP], CHANGES)[0]["files"] == []


def test_file_kinds():
    assert kind_of("tests/test_auth.py") == "test"
    assert kind_of("README.md") == "doc"
    assert kind_of("auth.py") == "code"