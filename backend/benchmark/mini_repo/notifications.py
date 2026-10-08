MAX_RETRIES = 5


def send_sms(phone, text):
    print("SMS", phone, text)
    return True


def send_email_receipt(email, order):
    print("EMAIL", email, order)
    return True


def send_with_retry(send_fn, *args):
    """Try sending a notification again when it fails."""
    for _ in range(MAX_RETRIES):
        if send_fn(*args):
            return True
    return False