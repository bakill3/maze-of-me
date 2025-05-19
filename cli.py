# File: cli.py
import sys, time, random, threading
from collections import deque
from pathlib import Path
import colorama
from colorama import Fore, Style

from config             import Config
from user_profile       import UserProfile
from utils.platform_time import clear_screen
from utils.json_io      import load_json
from oauth.spotify      import SpotifyCollector
from oauth.google       import GoogleCollector
from audio.player       import AudioPlayer
from maze.generator     import MazeGenerator

colorama.init(autoreset=True)

THEME_ART = {
    "calm":    Fore.BLUE    + "  ~~~ a tranquil chamber ~~\n",
    "tense":   Fore.RED     + "  !!! a crackling corridor !!!\n",
    "vibrant": Fore.MAGENTA + "  *** a pulsing hall ***\n",
    "memory":  Fore.CYAN    + "  ### memory lane ###\n",
    "neutral": "",
}

BANNER = Fore.CYAN + r"""
  __  __             
 |  \/  | __ _  ___  
 | |\/| |/ _` |/ _ \ 
 | |  | | (_| | (_) |
 |_|  |_|\__,_|\___/ 
    Maze of Me
""" + Style.RESET_ALL

MENU = Fore.YELLOW + """
╔════════════════════════════════╗
║        Maze of Me CLI         ║
╠════════════════════════════════╣
║ 1) Go Left        – move left  ║
║ 2) Go Right       – move right ║
║ 3) Go Forward     – move ahead ║
║ 4) Talk to figure – interact   ║
║ h or ?            – help menu  ║
║ 0) Quit           – exit game  ║
╚════════════════════════════════╝
""" + Style.RESET_ALL


def typewriter(text: str, color=Fore.GREEN, delay: float = .01) -> None:
    for ch in text:
        sys.stdout.write(color + ch)
        sys.stdout.flush()
        time.sleep(delay)
    print(Style.RESET_ALL, end="")


def do_oauth(label: str, Collector):
    print(Fore.CYAN + f"🔑 {label} OAuth…" + Style.RESET_ALL)
    coll = Collector()
    coll.authenticate()
    coll.fetch_and_save()
    print(Fore.GREEN + f"✅ {label} data saved.\n" + Style.RESET_ALL)


def _preload(idx: int, tracks, player, buf, queue, done):
    if idx in done or idx in buf:
        return
    tr = tracks[idx]
    try:
        src = player.download_youtube(tr["artists"][0], tr["name"])
        wav = player.convert_to_wav(src)
        buf[idx] = wav
        queue.append(idx)
    except Exception:
        pass


# ────────────────────────────────────────────────────────────────────
def main():
    clear_screen()
    player = AudioPlayer()
    player.play_main_music("main_music", "mp3")

    print(BANNER)
    typewriter("🧠 Logging-in with Google…\n\n", Fore.GREEN)

    profile = UserProfile.load() or UserProfile.collect()
    profile.save()

    cfg = load_json(Config.PROFILE_PATH) or {}
    if not cfg.get("google", {}).get("profile"):
        do_oauth("Google", GoogleCollector)
        cfg = load_json(Config.PROFILE_PATH)

    if not cfg.get("spotify"):
        do_oauth("Spotify", SpotifyCollector)
        cfg = load_json(Config.PROFILE_PATH)

    tracks = cfg["spotify"]["top_tracks"]
    track_n = len(tracks)
    maze    = MazeGenerator(cfg)

    # simple 1-track preload buffer
    q, buf, done = deque(), {}, set()
    if track_n:
        first = random.randrange(track_n)
        threading.Thread(target=_preload,
                         args=(first, tracks, player, buf, q, done),
                         daemon=True).start()

    typewriter("🔍 Entering the Maze…\n\n", Fore.CYAN)

    while True:
        print(MENU)
        ch = input(Fore.CYAN + "➤ " + Style.RESET_ALL).lower().strip()

        if ch in ("h", "?"):
            continue
        if ch == "0":
            print(Fore.GREEN + "👋 Goodbye." + Style.RESET_ALL)
            break

        if ch in ("1", "2", "3"):
            room = maze.move(ch)
            print(THEME_ART.get(room.theme, ""), end="")
            typewriter(room.description + "\n\n", Fore.WHITE)

            # ── music (one-ahead preload) ────────────────────────
            if track_n:
                # take preloaded if we have it, otherwise random fallback
                idx = q.popleft() if q else random.randrange(track_n)
                done.add(idx)
                tr  = tracks[idx]
                wav = buf.pop(idx, None)

                if wav and wav.exists():
                    player.play_file(wav)
                else:
                    player.play_full_from_youtube(tr["artists"][0], tr["name"])

                # schedule exactly ONE track ahead
                avail = [i for i in range(track_n)
                         if i not in done and i not in buf and i not in q]
                if not avail:
                    done.clear()
                    avail = list(range(track_n))
                nxt = random.choice(avail)
                threading.Thread(target=_preload,
                                 args=(nxt, tracks, player, buf, q, done),
                                 daemon=True).start()
            continue

        if ch == "4":
            line = maze.talk()
            typewriter(line + "\n\n", Fore.MAGENTA)
            continue

        print(Fore.RED + "❓ Unknown command." + Style.RESET_ALL)


if __name__ == "__main__":
    main()
