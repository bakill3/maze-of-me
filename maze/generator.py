# ────────────────────────────────────────────────────────────────────────────────
# File: maze/generator.py        (2025-05-20  • unique-NPC lines, no repeats)
# ------------------------------------------------------------------------------#
from __future__ import annotations
import random, datetime as _dt, threading
from typing     import Optional, Deque, Set
from pathlib    import Path
from collections import deque

from llm.model_interface import query_npc
from llm.prompt_builder  import build_npc_prompt, validate_npc_line
from utils.json_io       import load_json
from config              import Config

# ── TEMPLATES ───────────────────────────────────────────────────────────────────
ROOMS_FILE = Path(__file__).parent / "rooms.json"
ROOMS = load_json(ROOMS_FILE) if ROOMS_FILE.exists() else {
    "happy": [
        "Sunbeams dance across {wall_color} walls and a {furniture}. "
        "Hope swells as memories of {name} resurface.",
        ["plush sofa", "vintage jukebox", "beanbag"],
        ["honey yellow", "peach", "warm cream"],
    ],
    "sad": [
        "Muted {wall_color} walls press inwards. A lone {furniture} creaks. "
        "Drips echo the countdown to {event}.",
        ["rocking chair", "dusty piano", "torn loveseat"],
        ["washed-out blue", "ashen grey", "cold teal"],
    ],
    "angry": [
        "Ragged shadows slash the {wall_color} walls; a {furniture} rattles. "
        "Your pulse matches the room’s fury.",
        ["metal desk", "barred window", "shattered mirror"],
        ["scarlet", "burnt umber", "dark crimson"],
    ],
    "neutral": [
        "Bare {wall_color} walls and a simple {furniture}. "
        "Silence reigns—only your heartbeat remains.",
        ["wooden stool", "plain cot", "unmarked door"],
        ["bone white", "pale beige", "soft grey"],
    ],
}

EMOTIONS        = list(ROOMS.keys())
ROOM_CACHE_SIZE = 12      # recent room sentences to avoid duplicates
NPC_CACHE_SIZE  = 12      # recent npc lines to avoid duplicates
NPC_RETRIES     = 4       # attempts before we give up and craft a line
LLM_BG_TIMEOUT  = 30      # sec safeguard for background thread

# ───────────────────────────────────────────────────────────────────────────────
class Room:
    def __init__(self, desc: str, theme: str):
        self.description = desc
        self.theme       = theme


class MazeGenerator:
    """Template rooms + unique, personalised NPC lines (async)."""

    def __init__(self, profile_blob: dict):
        self.pro = profile_blob
        # recent caches
        self._recent_rooms: Deque[str] = deque(maxlen=ROOM_CACHE_SIZE)
        self._recent_npcs : Deque[str] = deque(maxlen=NPC_CACHE_SIZE)

        # rotating YouTube hooks
        self._yt = [v["title"] for v in self.pro.get("google", {})
                                          .get("youtube_history", [])]
        random.shuffle(self._yt)

        # calendar hook (today’s first event)
        today = _dt.date.today().isoformat()
        self._today = next((
            ev["summary"] for ev in self.pro.get("google", {})
                                        .get("calendar_events", [])
            if ev["start"][:10] == today
        ), "")

        # double buffer
        self._curr_room: Optional[Room] = None
        self._curr_npc : str           = "…"
        self._next_room, self._next_npc = self._build_pair_blocking()

        self._bg_thread: Optional[threading.Thread] = None

    # ── helpers ──────────────────────────────────────────────────────────
    def _rand(self, seq): return random.choice(seq)

    def _make_room_sentence(self, mood: str) -> str:
        tpl, furn, colors = ROOMS[mood]
        return tpl.format(
            name       = self.pro.get("google", {}).get("profile", {})
                                  .get("given_name", "You"),
            event      = self._today or "—",
            furniture  = self._rand(furn),
            wall_color = self._rand(colors),
        )

    def _unique_room(self) -> Room:
        # 8 attempts to get unseen; else accept repeat
        for _ in range(8):
            mood = random.choice(EMOTIONS)
            sent = self._make_room_sentence(mood)
            if sent not in self._recent_rooms:
                self._recent_rooms.append(sent)
                return Room(sent, mood)
        # fallback
        mood = random.choice(EMOTIONS)
        sent = self._make_room_sentence(mood)
        self._recent_rooms.append(sent)
        return Room(sent, mood)

    # ---- NPC generation ------------------------------------------------
    def _yt_pop(self) -> str:
        if not self._yt: return ""
        t = self._yt.pop(0); self._yt.append(t); return t

    def _hooks(self) -> dict[str, str]:
        return {
            "name": self.pro.get("google", {}).get("profile", {})
                             .get("given_name", ""),
            "event": self._today,
            "youtube": self._yt_pop(),
            "time": _dt.datetime.now().strftime("%H:%M"),
        }

    def _gen_npc(self, room_desc: str) -> str:
        hooks = self._hooks()
        for _ in range(NPC_RETRIES):
            raw  = query_npc(build_npc_prompt(self.pro, room_desc, hooks))
            line = validate_npc_line(raw, hooks)
            if line and line not in self._recent_npcs:
                self._recent_npcs.append(line)
                return line
            # tweak hook to push model in new direction
            hooks["youtube"] = self._yt_pop()
        # final crafted fallback (still varied)
        alt = random.choice([
            "I feel your memories leaking, {name}.",
            "The clock ticks toward {event}, does it scare you?",
            "Even here, {time} haunts you.",
            "Your videos whisper: “{youtube}”…"
        ]).format(**hooks)
        self._recent_npcs.append(alt)
        return alt

    # ---- pair builders -------------------------------------------------
    def _build_pair(self) -> tuple[Room, str]:
        r = self._unique_room()
        n = self._gen_npc(r.description)
        return r, n

    def _build_pair_blocking(self):
        return self._build_pair()

    def _build_pair_bg(self):
        try:
            self._next_room, self._next_npc = self._build_pair()
        except Exception:
            self._next_room = Room("An unremarkable grey cell.", "neutral")
            self._next_npc  = "The figure gives no answer."

    # ── public API ───────────────────────────────────────────────────────
    def move(self, _ch: str) -> Room:
        if self._curr_room is None:
            self._curr_room, self._curr_npc = self._next_room, self._next_npc
            self._bg_thread = threading.Thread(
                target=self._build_pair_bg, daemon=True
            )
            self._bg_thread.start()
            return self._curr_room

        # swap buffers
        self._curr_room, self._curr_npc = self._next_room, self._next_npc

        # tiny join (never block >0.05 s)
        if self._bg_thread and self._bg_thread.is_alive():
            self._bg_thread.join(timeout=0.05)

        # fire new build
        self._bg_thread = threading.Thread(
            target=self._build_pair_bg, daemon=True
        )
        self._bg_thread.start()
        return self._curr_room

    def talk(self) -> str:
        return self._curr_npc or "The figure stares silently…"
