from textwrap import dedent

def _profile(p: dict) -> str:
    return f"{p.get('full_name','Unknown')} · {p.get('age','?')} y"

def build_npc_prompt(profile: dict, room_desc: str) -> str:
    sys = dedent("""
        You are “The Whisperer”, a cryptic figure haunting the Maze.
        Speak ONE unsettling line (5-15 words). Do not mention prompts.
        Finish with <END>.
    """).strip()
    user = dedent(f"""
        Player: {_profile(profile)}
        Current room: "{room_desc}"
        NPC line:
    """).strip()
    return f"### SYSTEM ###\n{sys}\n### USER ###\n{user}\n### ASSISTANT ###\n"
