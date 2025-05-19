# File: oauth/google.py

import json
import threading
import webbrowser
from http.server           import HTTPServer, BaseHTTPRequestHandler
from urllib.parse          import urlparse, parse_qs
from pathlib               import Path
from datetime              import datetime, timedelta

from google.oauth2.credentials    import Credentials
from google_auth_oauthlib.flow    import Flow
from googleapiclient.discovery    import build
from googleapiclient.errors       import HttpError

from config                import Config
from utils.json_io         import load_json, save_json

# The port on which the local server will listen
REDIRECT_HOST = "127.0.0.1"
REDIRECT_PORT = 8888

class _GoogleCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler to receive the OAuth2 redirect with the code."""
    auth_code = None

    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        if "code" in qs:
            _GoogleCallbackHandler.auth_code = qs["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            # Simple page to tell user they're done
            self.wfile.write(
                "<h1>✅ Google authentication complete. You can close this window.</h1>"
                .encode("utf-8")
            )
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args):
        # Silence default logging
        pass

class GoogleCollector:
    """Collects Google profile, calendar events, and YouTube history."""

    # Scopes for profile, calendar read-only, YouTube history
    SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]

    # Location of your client secret JSON downloaded from Google Cloud
    CLIENT_SECRETS_FILE = Path(__file__).parent.parent / "google_client_secret.json"

    def __init__(self):
        self.creds: Credentials | None = None

    def authenticate(self):
        # Start the OAuth2 flow
        flow = Flow.from_client_secrets_file(
            str(self.CLIENT_SECRETS_FILE),
            scopes=self.SCOPES,
            redirect_uri=f"http://{REDIRECT_HOST}:{REDIRECT_PORT}/"
        )

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent"
        )

        # Launch local HTTP server to catch the redirect
        server = HTTPServer((REDIRECT_HOST, REDIRECT_PORT), _GoogleCallbackHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        print("\n🔑 Google OAuth… opening browser for login…")
        webbrowser.open(auth_url, new=1)

        # Wait for the handler to get the code
        while not _GoogleCallbackHandler.auth_code:
            pass
        server.shutdown()
        code = _GoogleCallbackHandler.auth_code

        # Exchange code for tokens
        flow.fetch_token(code=code)
        self.creds = flow.credentials

        print("✅ Google authentication successful.\n")

    def fetch_and_save(self):
        """Fetch profile, calendar events, and YouTube history and save them."""
        if not self.creds:
            raise RuntimeError("Google credentials not found. Call authenticate() first.")

        data = load_json(Path(Config.PROFILE_PATH)) or {}

        # 1) Basic profile
        try:
            oauth2 = build("oauth2", "v2", credentials=self.creds, cache_discovery=False)
            profile = oauth2.userinfo().get().execute()
        except HttpError as e:
            print(f"⚠️ Google profile fetch error: {e}")
            profile = {}

        # 2) Calendar events (next 10 upcoming)
        try:
            cal = build("calendar", "v3", credentials=self.creds, cache_discovery=False)
            now = datetime.utcnow().isoformat() + "Z"
            events_result = (
                cal.events()
                   .list(
                       calendarId="primary",
                       timeMin=now,
                       maxResults=10,
                       singleEvents=True,
                       orderBy="startTime"
                   )
                   .execute()
            )
            events = events_result.get("items", [])
        except HttpError as e:
            print(f"⚠️ Google calendar fetch error: {e}")
            events = []

                # 3) YouTube watch history (last 10 via Activities API)
        try:
            yt = build("youtube", "v3", credentials=self.creds, cache_discovery=False)
            acts = (
                yt.activities()
                  .list(
                      part="snippet,contentDetails",
                      mine=True,
                      maxResults=10
                  )
                  .execute()
            )
            items = acts.get("items", [])
            yt_history = []
            for it in items:
                snip = it.get("snippet", {})
                cd   = it.get("contentDetails", {})
                title = snip.get("title", "Untitled")
                # Attempt to pull a videoId from any contentDetails subfield
                video_id = (
                    cd.get("upload", {}).get("videoId")
                    or cd.get("watchHistory", {}).get("resourceId", {}).get("videoId")
                    or cd.get("like", {}).get("resourceId", {}).get("videoId")
                )
                url = f"https://youtu.be/{video_id}" if video_id else ""
                yt_history.append({"title": title, "url": url})
        except HttpError as e:
            print(f"⚠️ YouTube history fetch error: {e}")
            yt_history = []


        # Merge and save
        data["google"] = {
            "profile": profile,
            "calendar_events": [
                {
                    "summary": ev.get("summary", ""),
                    "start": ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date", "")),
                    "end":   ev.get("end",   {}).get("dateTime", ev.get("end",   {}).get("date", "")),
                }
                for ev in events
            ],
            "youtube_history": yt_history
        }

        save_json(Path(Config.PROFILE_PATH), data)
        print("✅ Google data saved.\n")
