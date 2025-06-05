from __future__ import annotations
from textwrap import dedent
import re, random
from typing import Dict, List, Optional

def _profile_blurb(profile: dict) -> str:
    gp = profile.get("google", {}).get("profile", {})
    name  = gp.get("name", "Unknown")
    email = gp.get("email", "—")
    return f"{name} · {email}"

_HOOK_TOKEN_RE = re.compile(r"<<(\w+)>>")

def _fallback_with_hook(hooks: Dict[str, str], player_emotions: Optional[List[str]]=None, contacts: Optional[List[str]]=None) -> str:
    player_emotions = player_emotions or []
    contacts = contacts or []
    # Add more interesting "fallbacks" using hooks, emotions, and contacts.
    if not hooks: return "The figure studies you in silence…"
    key, value = random.choice(list(hooks.items()))
    responses = []
    if key == "contact" and contacts:
        responses.append(f"Maybe you should talk to {value} again?")
        responses.append(f"Your mind wanders to {value}. Miss them?")
    if player_emotions:
        mood = player_emotions[-1]
        responses.append(f"I sense you're feeling {mood.lower()}. Why do you think that is?")
    responses += [
        f"{value}, the maze still echoes your name.",
        f"Counting down: {hooks.get('upcoming', '')}.",
        f"It is {hooks.get('time', '')}. Shadows stretch and wait.",
        f"Still humming “{hooks.get('youtube', '')}”, aren’t you?",
        f"Are you prepared for {hooks.get('event', '')}?",
        f"{hooks.get('special', '')}... will you be ready?",
        f"{hooks.get('birthday', '')}... Time doesn't stop, does it?",
    ]
    return random.choice([resp for resp in responses if resp.strip()]) or "You feel a presence, but it says nothing."

def build_npc_prompt(
    profile: dict,
    last_room_desc: str,
    hooks: Dict[str, str],
    dialogue_key: Optional[str] = None,
    player_history: Optional[str] = "",
    player_emotions: Optional[List[str]] = None,
    contacts: Optional[List[str]] = None,
    room_emotion: Optional[str] = None,
) -> str:
    """
    Prompt for **The Whisperer** (NPC) -- with memory, emotion, and contact intent.
    """
    # Aggressively truncate for speed
    if isinstance(player_history, list):
        player_history = player_history[-2:]
        player_history = " | ".join(player_history)
    if isinstance(player_emotions, list):
        player_emotions = player_emotions[-2:]
    if isinstance(contacts, list):
        contacts = contacts[-2:]
    recent_emotions = ", ".join(player_emotions or []) or "none"
    contacts_line = ", ".join(contacts or [])
    rm_emotion = room_emotion or "neutral"
    sys_msg = dedent(f"""
        You are **The Whisperer**, a cryptic—but subtly human—figure in a psychological maze.
        Respond with exactly ONE mysterious, unsettling, or caring line (6-26 words).
        Use *exactly ONE* hook token from the list (e.g. <<contact>>, <<special>>, <<birthday>>, <<name>>), inserting its value verbatim.
        The player just spoke to you with intent: '{dialogue_key or ""}'.
        List of player contacts: {contacts_line}
        Recent player emotions: {recent_emotions}
        Current room emotion: {rm_emotion}
        Never break character. Never repeat the room description. End with <END>.
    """).strip()
    hook_block = "\n".join(f"<<{k}>> = {v}" for k, v in hooks.items()) if hooks else "(no hooks today)"
    user_msg = dedent(f"""
        Player profile: {_profile_blurb(profile)}
        Personal hooks you may reference (choose one, insert verbatim!):
        {hook_block}
        Current room description:
        "{last_room_desc}"
        Room mood: {rm_emotion}
        Player last dialogue/action: "{dialogue_key or 'none'}"
        Previous interaction: "{player_history or 'none'}"
        Your single mysterious sentence:
    """).strip()
    return (
        "### SYSTEM ###\n"   + sys_msg   + "\n"
        "### USER ###\n"    + user_msg  + "\n"
        "### ASSISTANT ###\n"
    )

def validate_npc_line(text: str, hooks: Dict[str, str], player_emotions: Optional[List[str]]=None, contacts: Optional[List[str]]=None) -> str:
    player_emotions = player_emotions or []
    contacts = contacts or []
    raw = (text or "").strip()
    if not raw:
        return _fallback_with_hook(hooks, player_emotions, contacts)
    m = _HOOK_TOKEN_RE.search(raw)
    if not m:
        return _fallback_with_hook(hooks, player_emotions, contacts)
    key = m.group(1)
    value = hooks.get(key, "")
    if not value:
        return _fallback_with_hook(hooks, player_emotions, contacts)
    line = _HOOK_TOKEN_RE.sub(value, raw, count=1)
    line = line.replace("<END>", "").strip()
    return line or _fallback_with_hook(hooks, player_emotions, contacts)
