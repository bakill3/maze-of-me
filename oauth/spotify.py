"""
Very small Spotify collector:

• authenticate()            – OAuth code flow in a browser
• fetch_and_save()          – store top-tracks (+ audio-features) in user_profile.json
"""

from __future__ import annotations
import json, os, time, webbrowser, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Final, Optional

import requests
from requests_oauthlib import OAuth2Session

from config        import Config
from utils.json_io import load_json, save_json


_REDIRECT_URI: Final[str] = "http://127.0.0.1:8888/spotify_callback"
_SCOPES:        Final[list[str]] = ["user-top-read"]
_AUTH:          Final[str] = "https://accounts.spotify.com/authorize"
_TOKEN:         Final[str] = "https://accounts.spotify.com/api/token"

_CALLBACK_CODE: Optional[str] = None   # set by mini HTTP server


# ──────────────────────────────────────────────────────────────────────────
# Tiny one-shot HTTP server to catch the redirect
# ──────────────────────────────────────────────────────────────────────────
class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        global _CALLBACK_CODE
        if "code=" in self.path:
            _CALLBACK_CODE = self.path.split("code=")[-1].split("&")[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h3>Spotify authentication complete, you can close this tab.</h3>")
        else:
            self.send_response(400); self.end_headers()

    def log_message(self, *_):  # silence console spam
        return


def _start_callback_server() -> HTTPServer:
    server = HTTPServer(("127.0.0.1", 8888), _CallbackHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ──────────────────────────────────────────────────────────────────────────
# Collector
# ──────────────────────────────────────────────────────────────────────────
class SpotifyCollector:
    def __init__(self) -> None:
        self.session: Optional[OAuth2Session] = None
        self.token:   Optional[dict[str, Any]] = None

    # ..........................................................
    def authenticate(self) -> None:
        """
        Opens the browser.  If the redirect isn’t captured within 60 s,
        falls back to asking the user to paste the URL.
        """
        oauth = OAuth2Session(
            client_id=Config.SPOTIFY_CLIENT_ID,
            redirect_uri=_REDIRECT_URI,
            scope=_SCOPES,
        )
        auth_url, _ = oauth.authorization_url(_AUTH)

        # 1) start local callback server
        srv = _start_callback_server()

        # 2) open browser
        print("🔑 Spotify OAuth… opening browser for login…")
        webbrowser.open(auth_url, new=2, autoraise=True)

        # 3) wait up to 60 s for redirect
        timeout = time.time() + 60
        while _CALLBACK_CODE is None and time.time() < timeout:
            time.sleep(0.3)

        srv.shutdown()

        code = _CALLBACK_CODE
        if code is None:
            # manual fallback
            print("⚠️  Couldn’t capture the redirect automatically.")
            url = input("Paste the FULL redirect URL you were sent to: ").strip()
            if "code=" in url:
                code = url.split("code=")[-1].split("&")[0]

        if not code:
            raise RuntimeError("Failed to receive auth code from Spotify.")

        # 4) exchange for token
        self.session = OAuth2Session(Config.SPOTIFY_CLIENT_ID, redirect_uri=_REDIRECT_URI)
        self.token   = self.session.fetch_token(
            _TOKEN,
            client_secret=Config.SPOTIFY_CLIENT_SECRET,
            code=code,
        )

    # ..........................................................
    def _api_get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        if not self.session or not self.token:
            raise RuntimeError("authenticate() first.")
        url = f"https://api.spotify.com/v1/{endpoint.lstrip('/')}"
        resp = self.session.get(url, params=params or {})
        resp.raise_for_status()
        return resp.json()

    # ..........................................................
    def fetch_and_save(self) -> None:
        if not self.session:
            raise RuntimeError("authenticate() first.")

        top = self._api_get("me/top/tracks", {"limit": 20})["items"]
        tracks = [
            {
                "id": t["id"],
                "name": t["name"],
                "artists": [a["name"] for a in t["artists"]],
                "uri": t["uri"],
            }
            for t in top
        ]

        # optional audio-features (ignore 403 if quota exhausted)
        feats: dict[str, Any] = {}
        try:
            ids = ",".join(t["id"] for t in tracks)
            feats_raw = self._api_get("audio-features", {"ids": ids})["audio_features"]
            feats = {f["id"]: f for f in feats_raw if f}
        except requests.HTTPError:
            pass

        # merge into profile JSON
        prof = load_json(Path(Config.PROFILE_PATH))
        prof["spotify"] = {"top_tracks": tracks, "audio_features": feats}
        save_json(Path(Config.PROFILE_PATH), prof)
