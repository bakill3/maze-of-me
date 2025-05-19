from __future__ import annotations
import random, datetime as _dt
from .room import Room
from llm.model_interface import query_npc
from llm.prompt_builder  import build_npc_prompt

EMOTIONS   = ["happy","sad","angry","calm","tense","vibrant","neutral"]
WALLS      = ["pastel blue","ashen grey","crimson","moss green","bone white"]
FLOORS     = ["marble tiles","creaking wood","cold concrete","velvet carpet"]
FURNITURE  = ["rocking chair","grand piano","rusty cot","mirror","broken clock"]

class MazeGenerator:
    def __init__(self, profile: dict):
        self.p = profile
        self.vis: list[str] = []
        self._yt = [v["title"] for v in profile.get("google", {}).get("youtube_history", [])]
        random.shuffle(self._yt)

    # helpers ----------------------------------------------------------
    def _yt_echo(self) -> str:
        if not self._yt: return ""
        title = self._yt.pop(0); self._yt.append(title)
        return f'Echoes of “{title}” drift here.'

    def _event_today(self) -> str|None:
        today = _dt.date.today().isoformat()
        for ev in self.p.get("google", {}).get("calendar_events", []):
            if ev["start"][:10] == today:
                return f'A rusted plaque reads “{ev["summary"]}”.'
        return None

    def _mood(self) -> str:
        feats = list(self.p.get("spotify", {}).get("audio_features", {}).values())
        if not feats: return "neutral"
        e = sum(f.get("energy", .5) for f in feats) / len(feats)
        return "vibrant" if e>.75 else "happy" if e>.55 else "calm" if e<.25 else "sad" if e<.4 else "tense"

    # public -----------------------------------------------------------
    def move(self, ch: str) -> Room:
        direction = {"1":"left","2":"right","3":"forward"}.get(ch,"forward")
        mood = self._mood()
        parts = [
            f"You step {direction} into a {mood} chamber.",
            f"The {random.choice(WALLS)} walls shimmer.",
            f"A solitary {random.choice(FURNITURE)} rests on {random.choice(FLOORS)}."
        ]
        if (ev := self._event_today()): parts.append(ev)
        if (yt := self._yt_echo()):     parts.append(yt)
        desc = " ".join(parts)
        self.vis.append(desc)
        return Room(desc, mood)

    def talk(self) -> str:
        if not self.vis: return "The figure remains silent."
        prompt = build_npc_prompt(self.p, self.vis[-1])
        return query_npc(prompt) or "…"
