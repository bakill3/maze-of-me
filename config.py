# File: config.py

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class Config:
    # OAuth credentials (fill via .env)
    SPOTIFY_CLIENT_ID     = os.getenv('SPOTIFY_CLIENT_ID', '')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', '')

    GOOGLE_CLIENT_ID      = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET  = os.getenv('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI   = os.getenv('GOOGLE_REDIRECT_URI', '')

    #FACEBOOK_APP_ID       = os.getenv('FACEBOOK_APP_ID', '')
    #FACEBOOK_APP_SECRET   = os.getenv('FACEBOOK_APP_SECRET', '')
    #FACEBOOK_REDIRECT_URI = os.getenv('FACEBOOK_REDIRECT_URI', '')

    # File paths
    PROFILE_PATH = Path(__file__).parent / 'user_profile.json'

    # Validation ranges
    MIN_AGE                 = 1
    MAX_AGE                 = 120
    MIN_HEIGHT_CM           = 30
    MAX_HEIGHT_CM           = 300
    MIN_WEIGHT_KG           = 10
    MAX_WEIGHT_KG           = 500
