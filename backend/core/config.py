import os
from pathlib import Path
from dotenv import load_dotenv

# Project root directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Flask configuration
SECRET_KEY = os.getenv("SECRET_KEY")

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Existing configuration
REVIEW_FILE = "data/reviews.xlsx"
UPLOAD_DIR = os.path.join("static", "uploads")