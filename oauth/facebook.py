# File: oauth/facebook.py

import threading
import webbrowser
from http.server      import HTTPServer, BaseHTTPRequestHandler
from urllib.parse     import urlparse, parse_qs
from requests_oauthlib import OAuth2Session
from config           import Config
from utils.json_io    import load_json, save_json
from pathlib          import Path

CALLBACK_HOST = "127.0.0.1"
CALLBACK_PORT = 8888

class _FacebookCallbackHandler(BaseHTTPRequestHandler):
    """Captures Facebook’s OAuth redirect code."""
    auth_code = None

    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        if "code" in qs:
            _FacebookCallbackHandler.auth_code = qs["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("✅ Authentication complete. You can close this window.".encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args):
        pass

class FacebookCollector:
    AUTH_URL  = "https://www.facebook.com/v16.0/dialog/oauth"
    TOKEN_URL = "https://graph.facebook.com/v16.0/oauth/access_token"
    SCOPE     = ["public_profile", "email"]

    def authenticate(self):
        fb = OAuth2Session(
            Config.FACEBOOK_APP_ID,
            scope=self.SCOPE,
            redirect_uri=Config.FACEBOOK_REDIRECT_URI
        )
        auth_url, _ = fb.authorization_url(self.AUTH_URL)

        server = HTTPServer((CALLBACK_HOST, CALLBACK_PORT), _FacebookCallbackHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        print("\n🔑 Facebook OAuth… opening browser for login…")
        webbrowser.open(auth_url, new=1)

        while _FacebookCallbackHandler.auth_code is None:
            pass
        server.shutdown()
        code = _FacebookCallbackHandler.auth_code

        fb.fetch_token(
            self.TOKEN_URL,
            client_secret=Config.FACEBOOK_CLIENT_SECRET,
            code=code
        )
        self.session = fb
        print("✅ Facebook authentication successful.\n")

    def fetch_and_save(self):
        path = Path(Config.PROFILE_PATH)
        data = load_json(path) or {}

        profile = self.session.get("https://graph.facebook.com/me?fields=id,name,email").json()
        events  = self.session.get("https://graph.facebook.com/me/events").json().get("data", [])
        comments = []
        posts   = self.session.get("https://graph.facebook.com/me/posts").json().get("data", [])
        for p in posts:
            for c in self.session.get(f"https://graph.facebook.com/{p['id']}/comments").json().get("data", []):
                comments.append({
                    "post_id":   p["id"],
                    "commenter": c.get("from", {}).get("name"),
                    "message":   c.get("message"),
                })

        data["facebook"] = {
            "profile":  profile,
            "events":   events,
            "comments": comments,
        }
        save_json(path, data)
        print("✅ Facebook data saved.\n")
