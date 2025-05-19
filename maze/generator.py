# File: maze/generator.py
from __future__ import annotations
import random, datetime as _dt
from typing import Optional
from llm.model_interface import query_room, query_npc
from llm.prompt_builder import build_room_prompt, build_npc_prompt

class Room:
    def __init__(self, desc: str, theme: str):
        self.description = desc
        self.theme       = theme

class MazeGenerator:
    """Generates personalised rooms & NPC lines."""
    def __init__(self, profile: dict):
        self.profile = profile
        self.visited: list[str] = []
        # convenience
        self._yt = [v["title"] for v in profile.get("google", {}).get("youtube_history", [])]
        random.shuffle(self._yt)

    # ── helpers ────────────────────────────────────────────────────────────
    def _today_event(self) -> Optional[str]:
        today = _dt.date.today().isoformat()
        for ev in self.profile.get("google", {}).get("calendar_events", []):
            if ev["start"][:10] == today:
                return ev["summary"]
        return None

    def _yt_snippet(self, k: int = 2) -> str:
        if not self._yt: return ""
        picks = [self._yt.pop(0) for _ in range(min(k, len(self._yt)))]
        self._yt.extend(picks)  # cycle
        return " and ".join(f"“{p}”" for p in picks)

    def _mood(self) -> str:
        feats = list(self.profile.get("spotify", {}).get("audio_features", {}).values())
        if not feats: return "neutral"
        avg = sum(f.get("energy", .5) for f in feats) / len(feats)
        if   avg > .7: return "vibrant"
        elif avg < .3: return "calm"
        else:          return "tense"

    # ── public API ─────────────────────────────────────────────────────────
    def move(self, direction_choice: str) -> Room:
        dir_map = {"1": "left", "2": "right", "3": "forward"}
        direction = dir_map.get(direction_choice, "forward")
        prompt = build_room_prompt(
            profile=self.profile | {"current_date": _dt.date.today().isoformat()},
            direction=direction,
            mood=self._mood(),
            youtube_snippet=self._yt_snippet(),
            today_event=self._today_event(),
        )
        desc = query_room(prompt)
        if not desc:  # fallback
            desc = f"You move {direction}. The air feels {self._mood()}."
        self.visited.append(desc)
        theme = self._mood()
        return Room(desc, theme)

    def talk(self) -> str:
        if not self.visited: return "The figure stares silently."
        prompt = build_npc_prompt(self.profile, self.visited[-1])
        line = query_npc(prompt)
        return line or "…"
