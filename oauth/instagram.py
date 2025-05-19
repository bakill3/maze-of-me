# File: oauth/instagram.py

import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from requests_oauthlib import OAuth2Session

from config import Config
from utils.json_io import load_json, save_json
from pathlib import Path

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path)
        q = parse_qs(p.query)
        code = q.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Instagram authentication complete.</h1>"
            b"You may close this window.</body></html>"
        )
        self.server.auth_code = code

    def log_message(self, format, *args):
        return

class InstagramCollector:
    AUTH_BASE = "https://api.instagram.com/oauth/authorize"
    TOKEN_URL = "https://api.instagram.com/oauth/access_token"
    SCOPE = ["user_profile", "user_media"]

    def __init__(self):
        self.oauth = OAuth2Session(
            Config.INSTAGRAM_CLIENT_ID,
            redirect_uri=Config.INSTAGRAM_REDIRECT_URI,
            scope=self.SCOPE,
        )

    def authenticate(self):
        auth_url, _ = self.oauth.authorization_url(
            self.AUTH_BASE, response_type="code"
        )
        webbrowser.open(auth_url, new=1)

        server = HTTPServer(("127.0.0.1", 8888), OAuthCallbackHandler)
        server.handle_request()
        code = getattr(server, "auth_code", None)

        self.oauth.fetch_token(
            self.TOKEN_URL,
            client_secret=Config.INSTAGRAM_CLIENT_SECRET,
            code=code,
        )

    def fetch_and_save(self):
        profile_path = Path(Config.PROFILE_PATH)
        data = load_json(profile_path) or {}

        # 1) Basic Instagram profile
        me = self.oauth.get(
            "https://graph.instagram.com/me?fields=id,username"
        ).json()

        # 2) Public media captions
        media = self.oauth.get(
            "https://graph.instagram.com/me/media?fields=id,caption,permalink"
        ).json().get("data", [])

        data["instagram"] = {"profile": me, "media": media}
        save_json(profile_path, data)
