# ────────────────────────────────────────────────────────────────────────────────
# File: maze/generator.py (2025-05-21 • Full interactive NPC, emotion, inspect, memory)
# ------------------------------------------------------------------------------#
from __future__ import annotations
import random, datetime as _dt, threading
from typing     import Optional, Deque, List
from pathlib    import Path
from collections import deque

from llm.model_interface import query_npc
from llm.prompt_builder  import build_npc_prompt, validate_npc_line
from utils.json_io       import load_json
from config              import Config

ROOMS_FILE = Path(__file__).parent / "rooms.json"
ROOMS = load_json(ROOMS_FILE) if ROOMS_FILE.exists() else {
    "happy": [
        [
            "Sunbeams dance across {wall_color} walls and a {furniture}. Hope swells as memories of {hook} resurface.",
            "A faint, upbeat melody echoes from the {furniture}—perhaps you remember {hook}?",
            "The scent of citrus lingers, and somewhere, a calendar reminder for {hook} whispers from the corners.",
        ],
        ["plush sofa", "vintage jukebox", "beanbag"],
        ["honey yellow", "peach", "warm cream"],
    ],
    "sad": [
        [
            "Muted {wall_color} walls press inwards. A lone {furniture} creaks. Drips echo the countdown to {hook}.",
            "Your footsteps echo like memories you'd rather forget—was it {hook}?",
            "Rain taps the {furniture}. The air is thick with something left unsaid: {hook}.",
        ],
        ["rocking chair", "dusty piano", "torn loveseat"],
        ["washed-out blue", "ashen grey", "cold teal"],
    ],
    "angry": [
        [
            "Ragged shadows slash the {wall_color} walls; a {furniture} rattles. Your pulse matches the room’s fury at {hook}.",
            "Something overturned the {furniture}. Was it anger about {hook}?",
            "The air burns, the {furniture} looks battered—did you remember {hook}?",
        ],
        ["metal desk", "barred window", "shattered mirror"],
        ["scarlet", "burnt umber", "dark crimson"],
    ],
    "neutral": [
        [
            "Bare {wall_color} walls and a simple {furniture}. Silence reigns—only {hook} remains.",
            "A corridor of smooth {wall_color} stretches ahead. {hook} lingers in the quiet air.",
            "The {furniture} waits, perfectly centered. The maze itself seems to pause for {hook}.",
        ],
        ["wooden stool", "plain cot", "unmarked door"],
        ["bone white", "pale beige", "soft grey"],
    ],
}

EMOTIONS        = list(ROOMS.keys())
ROOM_CACHE_SIZE = 40
NPC_CACHE_SIZE  = 30
NPC_RETRIES     = 7

class Room:
    def __init__(self, desc: str, theme: str, furniture: str, items=None):
        self.description = desc
        self.theme       = theme
        self.furniture   = furniture
        self.items       = items or []

class MazeGenerator:
    """Interactive maze/NPC with memory, emotion, context, contacts."""

    def __init__(self, profile_blob: dict):
        self.pro = profile_blob
        self._recent_rooms: Deque[str] = deque(maxlen=ROOM_CACHE_SIZE)
        self._recent_npcs : Deque[str] = deque(maxlen=NPC_CACHE_SIZE)
        self._recent_dialogues: Deque[str] = deque(maxlen=10)
        self._emotion_feedback = deque(maxlen=8)
        self._contacts: List[str] = []
        self._yt_channels = self.pro.get("google", {}).get("youtube_channels", [])
        self._gmail = self.pro.get("google", {}).get("gmail_subjects", [])
        self._tasks = self.pro.get("google", {}).get("tasks", [])
        self._playlists = self.pro.get("spotify", {}).get("playlists", [])
        self._genres = self.pro.get("spotify", {}).get("genres", [])
        self._top_artist = self.pro.get("spotify", {}).get("top_artist", "")
        self._liked_tracks = self.pro.get("spotify", {}).get("liked_tracks", [])

        # Load contacts (names only for hooks)
        try:
            self._contacts = [c.get("name","") for c in self.pro.get("google", {}).get("contacts", []) if c.get("name")]
        except Exception:
            self._contacts = []

        self._yt = [v["title"] for v in self.pro.get("google", {})
                                          .get("youtube_history", [])]
        random.shuffle(self._yt)

        today = _dt.date.today()
        self._calendar_events = [
            {
                "summary": ev.get("summary", ""),
                "start": ev.get("start", "")[:10],  # YYYY-MM-DD
            }
            for ev in self.pro.get("google", {}).get("calendar_events", [])
        ]

        self._today = next((
            ev["summary"] for ev in self._calendar_events
            if ev["start"] == today.isoformat()
        ), "")

        self._upcoming_events = []
        for ev in self._calendar_events:
            try:
                ev_date = _dt.datetime.strptime(ev["start"], "%Y-%m-%d").date()
                delta = (ev_date - today).days
                if 0 < delta <= 14:
                    self._upcoming_events.append(
                        {"summary": ev["summary"], "days": delta, "date": ev_date}
                    )
            except Exception:
                continue

        self._special_events = []
        for ev in self._upcoming_events:
            s = ev["summary"].lower()
            if "interview" in s:
                self._special_events.append(f"Interview: {ev['summary']} in {ev['days']} days")
            if "birthday" in s:
                self._special_events.append(f"Birthday: {ev['summary']} in {ev['days']} days")
            if "meeting" in s:
                self._special_events.append(f"Meeting: {ev['summary']} in {ev['days']} days")
            if "exam" in s:
                self._special_events.append(f"Exam: {ev['summary']} in {ev['days']} days")

        self._birthday_hook = ""
        try:
            dob = self.pro.get("google", {}).get("profile", {}).get("birthdate", "")
            if dob:
                dob_dt = _dt.datetime.strptime(dob, "%Y-%m-%d").date()
                next_birthday = dob_dt.replace(year=today.year)
                if next_birthday < today:
                    next_birthday = next_birthday.replace(year=today.year + 1)
                days_until = (next_birthday - today).days
                if days_until <= 14:
                    self._birthday_hook = f"Your birthday in {days_until} days"
        except Exception:
            pass

        self._room_counter = 0
        self._curr_room: Optional[Room] = None
        self._curr_npc : str           = "…"
        self._last_dialogue: Optional[str] = None
        self._bg_thread: Optional[threading.Thread] = None
        self._next_room, self._next_npc = self._build_pair_blocking()

    def _rand(self, seq): return random.choice(seq)
    
    def set_progress(self, visited, moods):
        self._visited = visited
        self._moods = moods

    def _make_room_sentence(self, mood: str) -> tuple[str, str, list]:
        hooks = [
            self.pro.get("google", {}).get("profile", {}).get("given_name", ""),
            self._today or "",
            self._birthday_hook or "",
            self._yt[0] if self._yt else "",
        ]
        if self._special_events: hooks.append(self._special_events[0])
        if self._upcoming_events: hooks.append(f"{self._upcoming_events[0]['summary']} in {self._upcoming_events[0]['days']} days")
        if self._contacts: hooks.append(self._contacts[0])
        if self._yt_channels: hooks.append(self._yt_channels[0])
        if self._gmail: hooks.append(self._gmail[0])
        if self._tasks: hooks.append(self._tasks[0])
        if self._playlists: hooks.append(self._playlists[0])
        if self._genres: hooks.append(self._genres[0])
        if self._top_artist: hooks.append(self._top_artist)
        if self._liked_tracks: hooks.append(self._liked_tracks[0])
        hooks = [h for h in hooks if h]
        hook = random.choice(hooks) if hooks else "something unsaid"

        tpl_list, furn_list, color_list = ROOMS[mood]
        tpl = random.choice(tpl_list)
        furniture = self._rand(furn_list)
        desc = tpl.format(
            name       = self.pro.get("google", {}).get("profile", {}).get("given_name", "You"),
            hook       = hook,
            event      = self._today or "—",
            contact    = random.choice(self._contacts) if self._contacts else "someone",
            furniture  = furniture,
            wall_color = self._rand(color_list),
        )
        # --- Inventory/Item logic ---
        items = []
        # Add themed items from user data
        if self._playlists: items.append("Spotify headphones")
        if self._gmail: items.append("Email letter")
        if self._tasks: items.append("Google Task note")
        if self._calendar_events: items.append("Google Calendar")
        if self._yt_channels: items.append(f"YouTube: {self._yt_channels[0]}")
        if self._genres: items.append(f"Music genre: {self._genres[0]}")
        return desc, furniture, items

    def get_player_emotion_profile(self):
        """Return a summary of the player's emotional state and influences."""
        from collections import Counter
        mood_hist = list(self._emotion_feedback)
        if not mood_hist:
            return {"current": "neutral", "counts": {}, "time": _dt.datetime.now().hour}
        c = Counter(mood_hist)
        most = c.most_common(1)[0][0]
        hour = _dt.datetime.now().hour
        # Influence: night = more sad/angry, day = more happy/neutral
        if hour < 6 or hour > 22:
            bias = "sad" if c.get("sad",0) > 0 else most
        elif 6 <= hour < 12:
            bias = "happy" if c.get("happy",0) > 0 else most
        else:
            bias = most
        return {"current": bias, "counts": dict(c), "time": hour}

    def _choose_room_mood(self):
        """Choose a room mood based on player emotion profile and time of day."""
        prof = self.get_player_emotion_profile()
        # 60% chance to use player's current mood, else random
        if random.random() < 0.6:
            return prof["current"] if prof["current"] in EMOTIONS else random.choice(EMOTIONS)
        return random.choice(EMOTIONS)

    def _unique_room(self) -> Room:
        # Dream/memory sequence every 6th room
        if hasattr(self, '_room_counter') and self._room_counter and self._room_counter % 6 == 0:
            return self._dream_room()
        for _ in range(12):
            mood = self._choose_room_mood()
            sent, furniture, items = self._make_room_sentence(mood)
            if sent not in self._recent_rooms:
                self._recent_rooms.append(sent)
                return Room(sent, mood, furniture, items)
        mood = self._choose_room_mood()
        sent, furniture, items = self._make_room_sentence(mood)
        self._recent_rooms.append(sent)
        return Room(sent, mood, furniture, items)

    def _dream_room(self) -> Room:
        """Generate a special memory/dream room from user data."""
        # Use a notable event: birthday, concert, big meeting, etc.
        events = [e for e in self._calendar_events if any(k in e["summary"].lower() for k in ["birthday","concert","meeting","party","exam"])]
        if events:
            ev = random.choice(events)
            desc = f"You find yourself reliving: {ev['summary']} ({ev['start']}). The room is warped by memory."
            return Room(desc, "dream", "memory artifact", ["Memory fragment"])
        # Fallback: YouTube or music
        if self._yt:
            yt = random.choice(self._yt)
            desc = f"A dreamlike echo of '{yt}' fills the room. You sense this is a memory."
            return Room(desc, "dream", "echoing object", ["YouTube memory"])
        return Room("A surreal, shifting space. You feel a memory trying to surface.", "dream", "blurred object", ["Unknown memory"])

    def _gen_npc(self, room_desc: str, dialogue_key=None, log=None) -> tuple[str, str]:
        history_snippet = ""
        if log:
            for l in reversed(log):
                if "[Player]" in l and len(history_snippet) < 160:
                    history_snippet = l
                    break
        prompt_extras = {"last_player_input": dialogue_key or ""}
        hooks = self._hooks(prompt_extras)
        # Pass contacts and player_emotions
        player_emotions = list(self._emotion_feedback)
        # --- ENHANCEMENT: Named NPCs from real data ---
        npc_name = None
        if self._contacts:
            npc_name = random.choice(self._contacts)
        elif self._yt_channels:
            npc_name = random.choice(self._yt_channels)
        elif self._gmail:
            npc_name = random.choice(self._gmail)
        elif self._playlists:
            npc_name = random.choice(self._playlists)
        # If we have a name, use it in the NPC intro
        if npc_name:
            intro = f"Your old friend {npc_name} appears here, their presence shaped by your memories."
            history_snippet = intro
        for _ in range(NPC_RETRIES):
            prompt = build_npc_prompt(
                self.pro, room_desc, hooks, str(dialogue_key) if dialogue_key else "", history_snippet,
                player_emotions=player_emotions, contacts=self._contacts
            )
            raw  = query_npc(prompt)
            line = validate_npc_line(raw, hooks, player_emotions=player_emotions, contacts=self._contacts)
            if line and line not in self._recent_npcs:
                self._recent_npcs.append(line)
                return line, history_snippet
            hooks = self._hooks(prompt_extras)
        alt = f"{npc_name if npc_name else (random.choice(self._contacts) if self._contacts else 'A shadow')} lingers here."
        self._recent_npcs.append(alt)
        return alt, history_snippet

    def _build_pair(self) -> tuple[Room, str]:
        r = self._unique_room()
        n, _ = self._gen_npc(r.description)
        return r, n

    def _build_pair_blocking(self):
        return self._build_pair()

    def _build_pair_bg(self):
        try:
            self._next_room, self._next_npc = self._build_pair()
        except Exception:
            self._next_room = Room("An unremarkable grey cell.", "neutral", "bench")
            self._next_npc  = "The figure gives no answer."

    def move(self, _ch: str) -> Room:
        self._room_counter += 1
        if self._curr_room is None:
            self._curr_room, self._curr_npc = self._next_room, self._next_npc
            self._bg_thread = threading.Thread(
                target=self._build_pair_bg, daemon=True
            )
            self._bg_thread.start()
            return self._curr_room

        self._curr_room, self._curr_npc = self._next_room, self._next_npc
        if self._bg_thread and self._bg_thread.is_alive():
            self._bg_thread.join(timeout=0.05)
        self._bg_thread = threading.Thread(
            target=self._build_pair_bg, daemon=True
        )
        self._bg_thread.start()
        return self._curr_room

    def talk_with_context(self, dialogue_key, curr_room, log=None):
        npc_line, npc_mem = self._gen_npc(
            curr_room.description if curr_room else "A blank room.",
            dialogue_key,
            log,
        )
        self._recent_dialogues.append(npc_line)
        self._last_dialogue = npc_line
        return npc_line, npc_mem

    def record_feedback(self, feedback):
        self._emotion_feedback.append(feedback)

    def get_room_furniture(self):
        if self._curr_room: return self._curr_room.furniture
        return "something unremarkable"

    def inspect_furniture(self, furniture):
        prompt_key = f"inspect:{furniture}"
        npc_line, _ = self._gen_npc(
            f"You look closely at the {furniture}.",
            prompt_key,
            list(self._recent_dialogues),
        )
        return npc_line

    def get_room_items(self):
        if self._curr_room: return self._curr_room.items
        return []
    def collect_item(self, item):
        if not hasattr(self, '_inventory'):
            self._inventory = []
        if self._curr_room and item in self._curr_room.items:
            self._inventory.append(item)
            self._curr_room.items.remove(item)
            return True
        return False
    def get_inventory(self):
        return getattr(self, '_inventory', [])

    def get_npc_stats(self):
        """Return stats on NPCs and contact mentions for analytics display."""
        from collections import Counter
        # Count all NPC lines (excluding fallback/empty)
        npc_lines = list(self._recent_npcs)
        total_npcs = len(npc_lines)
        # Most frequent NPC (by name in line, if present)
        name_counts = Counter()
        contact_counts = Counter()
        for line in npc_lines:
            # Try to extract a name/contact from the line
            for contact in self._contacts:
                if contact and contact in line:
                    contact_counts[contact] += 1
                    name_counts[contact] += 1
            for yt in getattr(self, '_yt_channels', []):
                if yt and yt in line:
                    name_counts[yt] += 1
            for playlist in getattr(self, '_playlists', []):
                if playlist and playlist in line:
                    name_counts[playlist] += 1
        most_npc = name_counts.most_common(1)[0][0] if name_counts else None
        most_contact = contact_counts.most_common(1)[0][0] if contact_counts else None
        return {
            'total_npcs': total_npcs,
            'most_npc': most_npc,
            'most_contact': most_contact,
            'contact_mentions': dict(contact_counts)
        }

    def _hooks(self, prompt_extras=None):
        """Return a dictionary of hooks for LLM prompt, using user data and context."""
        hooks = {}
        # Name
        name = self.pro.get("google", {}).get("profile", {}).get("given_name", "")
        if name:
            hooks["name"] = name
        # Special events
        if self._special_events:
            hooks["special"] = self._special_events[0]
        # Birthday
        if self._birthday_hook:
            hooks["birthday"] = self._birthday_hook
        # Today event
        if self._today:
            hooks["event"] = self._today
        # Contact
        if self._contacts:
            hooks["contact"] = self._contacts[0]
        # YouTube
        if self._yt_channels:
            hooks["youtube"] = self._yt_channels[0]
        # Gmail
        if self._gmail:
            hooks["gmail"] = self._gmail[0]
        # Tasks
        if self._tasks:
            hooks["task"] = self._tasks[0]
        # Playlist
        if self._playlists:
            hooks["playlist"] = self._playlists[0]
        # Genre
        if self._genres:
            hooks["genre"] = self._genres[0]
        # Top artist
        if self._top_artist:
            hooks["artist"] = self._top_artist
        # Liked track
        if self._liked_tracks:
            hooks["track"] = self._liked_tracks[0]
        # YouTube video
        if hasattr(self, '_yt') and self._yt:
            hooks["ytvideo"] = self._yt[0]
        # Add any prompt extras
        if prompt_extras:
            hooks.update(prompt_extras)
        return hooks