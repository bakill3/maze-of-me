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
            self.wfile.write(
                "<h1>✅ Google authentication complete. You can close this window.</h1>"
                .encode("utf-8")
            )
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args):
        pass

class GoogleCollector:
    """Collects Google profile, calendar events, YouTube history, and contacts."""

    SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/gmail.readonly",     
        "https://www.googleapis.com/auth/tasks.readonly",      
    ]

    CLIENT_SECRETS_FILE = Path(__file__).parent.parent / "google_client_secret.json"

    def __init__(self):
        self.creds: Credentials | None = None

    def authenticate(self):
        flow = Flow.from_client_secrets_file(
            str(self.CLIENT_SECRETS_FILE),
            scopes=self.SCOPES,
            redirect_uri=f"http://{REDIRECT_HOST}:{REDIRECT_PORT}/"
        )

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent"
        )

        server = HTTPServer((REDIRECT_HOST, REDIRECT_PORT), _GoogleCallbackHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        print("\n🔑 Google OAuth… opening browser for login…")
        webbrowser.open(auth_url, new=1)

        while not _GoogleCallbackHandler.auth_code:
            pass
        server.shutdown()
        code = _GoogleCallbackHandler.auth_code

        flow.fetch_token(code=code)
        self.creds = flow.credentials

        print("✅ Google authentication successful.\n")

    def fetch_and_save(self):
        """Fetch profile, calendar events, YouTube history, and contacts. Save all."""
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

        # 2) Calendar events (next 20 upcoming)
        try:
            cal = build("calendar", "v3", credentials=self.creds, cache_discovery=False)
            now = datetime.utcnow().isoformat() + "Z"
            events_result = (
                cal.events()
                   .list(
                       calendarId="primary",
                       timeMin=now,
                       maxResults=20,
                       singleEvents=True,
                       orderBy="startTime"
                   )
                   .execute()
            )
            events = events_result.get("items", [])
        except HttpError as e:
            print(f"⚠️ Google calendar fetch error: {e}")
            events = []

        # 3) YouTube watch history (last 10 via Activities API, including channelTitle)
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
                channel_title = snip.get("channelTitle", "")
                # Try to pull a videoId from any contentDetails subfield
                video_id = (
                    cd.get("upload", {}).get("videoId")
                    or cd.get("watchHistory", {}).get("resourceId", {}).get("videoId")
                    or cd.get("like", {}).get("resourceId", {}).get("videoId")
                )
                url = f"https://youtu.be/{video_id}" if video_id else ""
                yt_history.append({
                    "title": title,
                    "url": url,
                    "channelTitle": channel_title
                })
        except HttpError as e:
            print(f"⚠️ YouTube history fetch error: {e}")
            yt_history = []


        # 4) Google contacts (top 10, name/email/birthday)
        try:
            people = build("people", "v1", credentials=self.creds, cache_discovery=False)
            results = people.people().connections().list(
                resourceName="people/me",
                pageSize=10,
                personFields="names,emailAddresses,birthdays"
            ).execute()
            contacts = results.get("connections", [])
            contact_data = [
                {
                    "name": c.get("names", [{}])[0].get("displayName", ""),
                    "email": c.get("emailAddresses", [{}])[0].get("value", ""),
                    "birthday": (
                        c.get("birthdays", [{}])[0].get("date", {}) 
                        if c.get("birthdays") else ""
                    )
                }
                for c in contacts
            ]
        except Exception as e:
            print(f"⚠️ Google contacts fetch error: {e}")
            contact_data = []
        
        # 5) Gmail (last 5 subjects)
        try:
            gmail = build('gmail', 'v1', credentials=self.creds, cache_discovery=False)
            msgs = gmail.users().messages().list(userId='me', maxResults=5, labelIds=['INBOX']).execute()
            subjects = []
            for msg in msgs.get('messages', []):
                msgdata = gmail.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject']).execute()
                for header in msgdata.get('payload', {}).get('headers', []):
                    if header['name'] == 'Subject':
                        subjects.append(header['value'])
                        break
        except Exception as e:
            print(f"⚠️ Gmail fetch error: {e}")
            subjects = []

        # 6) Google Tasks (first list, top 10)
        try:
            tasks_service = build('tasks', 'v1', credentials=self.creds, cache_discovery=False)
            lists = tasks_service.tasklists().list(maxResults=1).execute()
            all_tasks = []
            for tl in lists.get('items', []):
                tasks = tasks_service.tasks().list(tasklist=tl['id'], maxResults=10).execute()
                for t in tasks.get('items', []):
                    all_tasks.append(t.get('title', ''))
        except Exception as e:
            print(f"⚠️ Google Tasks fetch error: {e}")
            all_tasks = []

        # 7) YouTube Channels (from history)
        yt_channels = []
        try:
            for it in yt_history:
                # Try to parse "channelTitle" if you add this above
                if 'channelTitle' in it:
                    yt_channels.append(it['channelTitle'])
        except Exception:
            pass
        yt_channels = list(dict.fromkeys(yt_channels))[:5]

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
            "youtube_history": yt_history,
            "contacts": contact_data,
            "gmail_subjects": subjects,
            "tasks": all_tasks,
            "youtube_channels": yt_channels,
        }

        save_json(Path(Config.PROFILE_PATH), data)
        print("✅ Google data saved.\n")
