from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    ROOT              = Path(__file__).parent
    PROFILE_PATH      = ROOT / "user_profile.json"
    MODELS_DIR        = ROOT / "models"

    # Validation ranges for user data
    MIN_HEIGHT_CM     = 30
    MAX_HEIGHT_CM     = 300
    MIN_WEIGHT_KG     = 30
    MAX_WEIGHT_KG     = 300

    # Performance tuning for llama.cpp
    GPU_LAYERS        = int(os.getenv("LLAMA_GPU_LAYERS", "32"))
    N_THREADS         = int(os.getenv("LLAMA_THREADS", str(os.cpu_count() or 4)))
    CTX_SIZE          = int(os.getenv("LLAMA_CTX", "2048"))

    SPOTIFY_CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")

    GOOGLE_CLIENT_ID      = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET  = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI   = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8888/")
