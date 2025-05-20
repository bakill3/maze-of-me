# ──────────────────────────────────────────────────────────────────────────────
# File: llm/prompt_builder.py          (2025-05-20  • stronger NPC prompting)
# ──────────────────────────────────────────────────────────────────────────────
"""
Prompt helpers for Maze-of-Me.

• Rooms use fixed JSON templates (see maze/rooms.json).
• NPC lines come from the local LLM ─ but *must* inject exactly ONE
  personal hook token such as  <<name>>  or  <<youtube>>.
"""

from __future__ import annotations
from textwrap import dedent
import re, random
from typing import Dict

# ╭──────────────────────── profile blurb ───────────────────────╮
def _profile_blurb(profile: dict) -> str:
    gp = profile.get("google", {}).get("profile", {})
    name  = gp.get("name", "Unknown")
    email = gp.get("email", "—")
    return f"{name} · {email}"

# ╭──────────────────────── fall-back helpers ───────────────────╮
_HOOK_TOKEN_RE = re.compile(r"<<(\w+)>>")

def _fallback_with_hook(hooks: Dict[str, str]) -> str:
    """Deterministic, but rotates through hooks for variety."""
    if not hooks:
        return "The figure studies you in silence…"

    key, value = random.choice(list(hooks.items()))
    options = {
        "name":      f"{value}, the maze still echoes your name.",
        "event":     f"Tick-tock…  {value} draws ever nearer.",
        "youtube":   f"Still humming “{value}”, aren’t you?",
        "time":      f"It is {value}.  Shadows stretch and wait.",
    }
    return options.get(key, f"The maze whispers of {value}.")

# ╭───────────────────────── prompt builders ────────────────────╮
def build_npc_prompt(
    profile: dict,
    last_room_desc: str,
    hooks: Dict[str, str],
) -> str:
    """
    Prompt for **The Whisperer** (NPC).

    Requirements given to the model:
      • Output ONE cryptic sentence, 6-15 words, second-person OR first-person.
      • MUST include *exactly ONE* token that appears in the hooks list,
        copying it verbatim, e.g.  <<name>>
      • No extra meta-text, no code-block, no apologies.
      • End with <END>  (so the caller can use it as a stop token).
    """
    sys_msg = dedent("""
        You are **The Whisperer**, a disembodied voice inside a psychological maze.
        Respond with exactly ONE short, unsettling line (6-15 words).
        Copy *one* of the USER hook tokens (e.g. <<name>>) **unchanged**.
        No introductions, no “Sure”, no meta commentary. End with <END>.
    """).strip()

    hook_block = "\n".join(f"<<{k}>> = {v}" for k, v in hooks.items()) \
                 if hooks else "(no hooks today)"

    user_msg = dedent(f"""
        Player profile: {_profile_blurb(profile)}

        Personal hooks you may reference:
        {hook_block}

        Current room description (for atmosphere, not to be repeated verbatim):
        "{last_room_desc}"

        Your single mysterious sentence:
    """).strip()

    return (
        "### SYSTEM ###\n"   + sys_msg   + "\n"
        "### USER ###\n"    + user_msg  + "\n"
        "### ASSISTANT ###\n"
    )

# ╭──────────────────────── validator ───────────────────────────╮
def validate_npc_line(text: str, hooks: Dict[str, str]) -> str:
    """
    • Replace the first <<token>> with its real value.
    • If the model ignored hooks or produced garbage, fall back.
    • Always return a trimmed plain string (no <END>).
    """
    raw = (text or "").strip()
    if not raw:
        return _fallback_with_hook(hooks)

    m = _HOOK_TOKEN_RE.search(raw)
    if not m:
        return _fallback_with_hook(hooks)

    key = m.group(1)
    value = hooks.get(key, "")
    if not value:
        return _fallback_with_hook(hooks)

    line = _HOOK_TOKEN_RE.sub(value, raw, count=1)
    line = line.replace("<END>", "").strip()
    return line or _fallback_with_hook(hooks)
