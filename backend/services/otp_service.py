import random

otp_store = {}

def generate_otp(mobile):
    otp = str(random.randint(100000, 999999))
    otp_store[str(mobile)] = otp
    print(f"[OTP DEBUG] Mobile: {mobile} → OTP: {otp}")
    return otp

def verify_otp(mobile, entered_otp):
    stored = otp_store.get(str(mobile))
    if stored and stored == str(entered_otp):
        del otp_store[str(mobile)]
        return True
    return False