from auth import send_otp, verify_otp


def test_otp_valid_within_time():
    assert verify_otp("9999999999", "123456", age_seconds=300) is True


def test_otp_expired_after_ten_minutes():
    assert verify_otp("9999999999", "123456", age_seconds=601) is False