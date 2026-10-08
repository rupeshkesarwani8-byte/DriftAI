from app.services.drift import detect_drift


def test_number_change():
    changes = detect_drift("OTP expires in 10 minutes.", "OTP expires in 5 minutes.")
    assert len(changes) == 1
    c = changes[0]
    assert c["type"] == "value_change"
    assert c["entity"] == "OTP"
    assert c["property"] == "expires"
    assert c["old_value"] == "10 minutes"
    assert c["new_value"] == "5 minutes"


def test_unit_change():
    changes = detect_drift("OTP expires in 10 minutes.", "OTP expires in 2 hours.")
    assert len(changes) == 1
    assert changes[0]["old_value"] == "10 minutes"
    assert changes[0]["new_value"] == "2 hours"


def test_unchanged_returns_nothing():
    text = "OTP expires in 10 minutes."
    assert detect_drift(text, text) == []


def test_added_requirement():
    changes = detect_drift(
        "OTP expires in 10 minutes.",
        "OTP expires in 10 minutes.\nUsers get 3 login attempts.",
    )
    assert len(changes) == 1
    assert changes[0]["type"] == "added"


def test_removed_requirement():
    changes = detect_drift(
        "OTP expires in 10 minutes.\nUsers get 3 login attempts.",
        "OTP expires in 10 minutes.",
    )
    assert len(changes) == 1
    assert changes[0]["type"] == "removed"


def test_bullets_only_changed_line_reported():
    old = "- Password must be at least 8 characters\n- Session lasts 30 minutes"
    new = "- Password must be at least 12 characters\n- Session lasts 30 minutes"
    changes = detect_drift(old, new)
    assert len(changes) == 1
    assert changes[0]["entity"] == "Password"
    assert changes[0]["old_value"] == "8 characters"
    assert changes[0]["new_value"] == "12 characters"