# File: oauth/spotify.py

import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from pathlib import Path

from config import Config
from utils.json_io import load_json, save_json

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        # Send a simple response page
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h1>Authentication complete.</h1>"
                         b"You may close this window.</body></html>")
        # Store the auth code on the server object
        self.server.auth_code = code

    def log_message(self, format, *args):
        # Suppress HTTP server logs
        return

class SpotifyCollector:
    SCOPE = "user-top-read user-read-private"

    def __init__(self):
        self.sp_oauth = SpotifyOAuth(
            client_id=Config.SPOTIFY_CLIENT_ID,
            client_secret=Config.SPOTIFY_CLIENT_SECRET,
            redirect_uri="http://127.0.0.1:8888/callback",
            scope=self.SCOPE
        )
        self.sp = None

    def authenticate(self):
        """
        Opens the browser for Spotify login, then starts a temporary
        HTTP server on localhost:8888 to catch the redirect and grab the code.
        """
        auth_url = self.sp_oauth.get_authorize_url()
        webbrowser.open(auth_url, new=1)

        server = HTTPServer(("127.0.0.1", 8888), OAuthCallbackHandler)
        # Handle a single request, then shutdown
        server.handle_request()
        code = getattr(server, "auth_code", None)
        if not code:
            raise RuntimeError("Failed to receive auth code from Spotify.")

        token_info = self.sp_oauth.get_access_token(code, as_dict=True)
        self.sp = Spotify(auth=token_info["access_token"])
        print("✅ Spotify authentication successful.")

    def fetch_and_save(self):
        """
        Fetch top tracks and audio features (if permitted), then
        merge into user_profile.json under the 'spotify' key.
        """
        if not self.sp:
            raise RuntimeError("Not authenticated. Call .authenticate() first.")

        profile_path = Path(Config.PROFILE_PATH)
        profile = load_json(profile_path) or {}

        # Top tracks
        items = self.sp.current_user_top_tracks(limit=20, time_range="medium_term")["items"]
        track_ids = [t["id"] for t in items]

        # Try audio features
        audio_features = {}
        try:
            feats = self.sp.audio_features(track_ids)
            audio_features = {f["id"]: f for f in feats if f}
        except Exception:
            pass  # quietly ignore

        spotify_data = {
            "top_tracks": [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "artists": [a["name"] for a in t["artists"]],
                    "uri": t["uri"]
                }
                for t in items
            ],
            "audio_features": audio_features
        }

        profile["spotify"] = spotify_data
        save_json(profile_path, profile)
        print(f"✅ Spotify data saved under '{profile_path}'.")
