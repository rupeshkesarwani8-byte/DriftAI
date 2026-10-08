import random

OTP_EXPIRY_SECONDS = 600  # OTP 10 minute me expire hota hai
MAX_LOGIN_ATTEMPTS = 3
MIN_PASSWORD_LENGTH = 8

_otp_store = {}


def send_otp(phone):
    """Generate an OTP and remember when it was created."""
    code = str(random.randint(100000, 999999))
    _otp_store[phone] = (code, 0)
    return code


def verify_otp(phone, code, age_seconds):
    if phone not in _otp_store:
        return False
    saved, _ = _otp_store[phone]
    if age_seconds > OTP_EXPIRY_SECONDS:
        return False
    return saved == code


def login(phone, code, failed_attempts):
    if failed_attempts >= MAX_LOGIN_ATTEMPTS:
        raise PermissionError("Account locked")
    return verify_otp(phone, code, 0)


def validate_password(password):
    """Reject passwords that are too short."""
    return len(password) >= MIN_PASSWORD_LENGTH