from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    ROOT              = Path(__file__).parent
    PROFILE_PATH      = ROOT / "user_profile.json"
    MODELS_DIR        = ROOT / "models"

    SPOTIFY_CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")

    GOOGLE_CLIENT_ID      = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET  = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI   = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8888/")
