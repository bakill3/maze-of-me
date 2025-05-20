# user_profile.py
"""
Minimal wrapper: profile is now **Google-only**.
Fields kept:
    • full_name   (string)
    • age         (int)
All other game data (spotify, calendar, etc.) lives alongside in user_profile.json.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Final

_FILE: Final[Path] = Path(__file__).parent / "user_profile.json"

class UserProfile(dict):
    # ------------------------------------------------------------------  helpers
    @classmethod
    def load(cls) -> "UserProfile | None":
        if _FILE.exists():
            return cls(json.loads(_FILE.read_text(encoding="utf-8")))
        return None

    # called by oauth/google after authentication
    def update_from_google(self, google_blob: dict) -> None:
        prof = google_blob.get("profile", {})
        if n := prof.get("name"):
            self["full_name"] = n
        if age := google_blob.get("derived_age"):
            self["age"] = age

    def save(self) -> None:
        _FILE.write_text(json.dumps(self, indent=2, ensure_ascii=False), encoding="utf-8")
