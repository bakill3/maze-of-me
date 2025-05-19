from __future__ import annotations
import json
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------
#  Path to the single user-profile JSON on disk
# ------------------------------------------------------------------
_FILE = Path(__file__).parent / "user_profile.json"


class UserProfile(dict):
    """
    Very thin wrapper around a dict so we can add convenience helpers.
    """

    # --------------------------------------------------------------
    # basic load / save
    # --------------------------------------------------------------
    @classmethod
    def load(cls) -> "UserProfile":
        try:
            data: dict[str, Any] = json.loads(_FILE.read_text(encoding="utf-8"))
            return cls(data)
        except Exception:
            return cls()

    def save(self) -> None:
        # ALWAYS write as utf-8 so emoji / non-Latin chars survive on Windows
        _FILE.write_text(
            json.dumps(self, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # --------------------------------------------------------------
    # Google helper – pulls name & age straight from OAuth data
    # --------------------------------------------------------------
    def update_from_google(self, google_blob: dict[str, Any]) -> None:
        prof = google_blob.get("profile", {})
        if name := prof.get("name"):
            self["full_name"] = name

        # Derive age from birthday if People API later supplies it
        if (bday := prof.get("birthday")) and len(bday) >= 4:
            try:
                birth_year = int(bday[:4])
                from datetime import date
                self["age"] = date.today().year - birth_year
            except ValueError:
                pass
