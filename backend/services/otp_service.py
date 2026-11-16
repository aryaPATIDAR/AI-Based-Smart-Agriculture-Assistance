import os
import re
import time
import hmac
import random
import hashlib
import smtplib
from email.message import EmailMessage

# .env ko project root tak upar dhoondh ke load karta hai (main.py mein kuch nahi lagana padega)
from pathlib import Path
from dotenv import load_dotenv


def _load_env():
    here = Path(__file__).resolve()
    candidates = [p / ".env" for p in here.parents] + [Path.cwd() / ".env"]
    for c in candidates:
        if c.is_file():
            load_dotenv(c, override=True, encoding="utf-8-sig")
            print(f"[mail] .env mili: {c}")
            return c
    print("[mail] .env kahin nahi mili. In jagahon pe dhoondha:")
    for c in candidates:
        print("   ", c)
    return None


_ENV_PATH = _load_env()

OTP_EXPIRY_SEC = 600          # 10 minute
RESEND_COOLDOWN_SEC = 60      # resend ke beech 60 sec
MAX_ATTEMPTS = 5              # galat OTP ki limit

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# email -> {hash, expiry, sent_at, attempts}
# Note: ye memory mein hai (single server process ke liye theek). Server restart pe OTP chale jate hain.
_otp_store = {}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email):
    return str(email or "").strip().lower()


def is_valid_email(email):
    return bool(EMAIL_RE.match(email))


def _hash(email, otp):
    return hashlib.sha256(f"{email}:{otp}".encode()).hexdigest()


def generate_otp():
    return str(random.SystemRandom().randint(100000, 999999))


def send_otp_email(to_email, otp):
    """Email bhejta hai. Success pe True, fail pe False."""
    mail_user = (os.environ.get("MAIL_USER") or "").strip()
    mail_pass = (os.environ.get("MAIL_APP_PASSWORD") or "").replace(" ", "").strip()

    if not mail_user or not mail_pass:
        print("MAIL_USER / MAIL_APP_PASSWORD set nahi hai. .env path:", _ENV_PATH)
        return False

    msg = EmailMessage()
    msg["Subject"] = "Smart Agriculture Platform - Email Verification"
    msg["From"] = mail_user
    msg["To"] = to_email
    msg.set_content(
        f"Aapka verification OTP hai: {otp}\n\n"
        "Ye OTP 10 minute tak valid hai. Kisi ke saath share na karein."
    )

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(mail_user, mail_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print("Email bhejne mein error:", e)
        return False


def send_otp(email):
    """OTP banata hai, store karta hai, email bhejta hai. (ok, message) return karta hai."""
    email = normalize_email(email)
    now = time.time()

    rec = _otp_store.get(email)
    if rec and now - rec["sent_at"] < RESEND_COOLDOWN_SEC:
        wait = int(RESEND_COOLDOWN_SEC - (now - rec["sent_at"])) + 1
        return False, f"{wait} second baad dobara try karein"

    otp = generate_otp()
    if not send_otp_email(email, otp):
        return False, "Email nahi bhej paye, baad mein try karein"

    _otp_store[email] = {
        "hash": _hash(email, otp),
        "expiry": now + OTP_EXPIRY_SEC,
        "sent_at": now,
        "attempts": 0,
    }
    return True, "OTP email pe bhej diya gaya"


def verify_otp(email, entered):
    """(ok, message) return karta hai."""
    email = normalize_email(email)
    rec = _otp_store.get(email)

    if not rec:
        return False, "Pehle OTP mangwayein"

    if time.time() > rec["expiry"]:
        _otp_store.pop(email, None)
        return False, "OTP expire ho gaya, naya mangwayein"

    if rec["attempts"] >= MAX_ATTEMPTS:
        _otp_store.pop(email, None)
        return False, "Bahut zyada galat try, naya OTP mangwayein"

    rec["attempts"] += 1

    if not hmac.compare_digest(rec["hash"], _hash(email, str(entered).strip())):
        return False, "Galat OTP, dobara try karein"

    _otp_store.pop(email, None)  # ek OTP ek hi baar use ho
    return True, "Email verify ho gaya"