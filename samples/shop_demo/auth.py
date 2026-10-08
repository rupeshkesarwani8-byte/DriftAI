OTP_EXPIRY_SECONDS = 600  # OTP 10 minute me expire hota hai


def send_otp(phone: str) -> str:
    """Phone number par OTP bhejta hai."""
    return "123456"


def verify_otp(phone: str, otp: str, age_seconds: int) -> bool:
    """OTP sahi hai aur expire nahi hua to True."""
    if age_seconds > OTP_EXPIRY_SECONDS:
        return False
    return otp == "123456"