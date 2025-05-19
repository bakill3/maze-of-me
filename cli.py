# File: cli.py
import sys, time, random, threading, datetime as _dt
from collections import deque
from pathlib import Path

import colorama, requests
from colorama import Fore, Style

from config import Config
from user_profile import UserProfile
from utils.platform_time import clear_screen
from utils.json_io import load_json
from oauth.spotify import SpotifyCollector
from oauth.google  import GoogleCollector
from audio.player  import AudioPlayer
from maze.generator import MazeGenerator

colorama.init(autoreset=True)

THEME_ART = {
    "calm":    Fore.BLUE     + "  ~~~ a tranquil chamber ~~\n",
    "tense":   Fore.RED      + "  !!! a crackling corridor !!!\n",
    "vibrant": Fore.MAGENTA  + "  *** a pulsing hall ***\n",
    "memory":  Fore.CYAN     + "  ### memory lane ###\n",
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

# ──────────────────────────────────────────────────────────────────────────────
def typewriter(txt, color=Fore.GREEN, delay=0.01):
    for c in txt:
        sys.stdout.write(color + c); sys.stdout.flush(); time.sleep(delay)
    print(Style.RESET_ALL, end="")

def do_oauth(label, Collector):
    print(Fore.CYAN + f"🔑 {label} OAuth…" + Style.RESET_ALL)
    coll = Collector(); coll.authenticate(); coll.fetch_and_save()
    print(Fore.GREEN + f"✅ {label} data saved.\n" + Style.RESET_ALL)

def preload(idx, tracks, player, buf, q, done):
    if idx in done or idx in buf: return
    t = tracks[idx]
    try:
        src = player.download_youtube(t["artists"][0], t["name"])
        wav = player.convert_to_wav(src)
        buf[idx] = wav; q.append(idx)
    except Exception: pass

# ──────────────────────────────────────────────────────────────────────────────
def main():
    clear_screen()
    player = AudioPlayer(); player.play_main_music("main_music", "mp3")

    print(BANNER); typewriter("🧠 Welcome to the Maze of Me\n\n")

    profile = UserProfile.load() or UserProfile.collect(); profile.save()
    print(Fore.GREEN + "\n✅ Profile saved.\n")

    data = load_json(Path(Config.PROFILE_PATH)) or {}
    if not data.get("spotify"):        do_oauth("Spotify", SpotifyCollector)
    if not data.get("google",{}).get("profile"): do_oauth("Google", GoogleCollector)

    full   = load_json(Path(Config.PROFILE_PATH))
    tracks = full["spotify"]["top_tracks"]; n = len(tracks)
    mg     = MazeGenerator(full)

    q, buf, done = deque(), {}, set()
    for i in random.sample(range(n), k=min(2,n)):
        threading.Thread(target=preload,args=(i,tracks,player,buf,q,done),daemon=True).start()

    typewriter("🔍 Entering the Maze…\n\n", Fore.CYAN)

    while True:
        print(MENU)
        ch = input(Fore.CYAN + "➤ " + Style.RESET_ALL).strip().lower()
        if ch in ("h","?"): continue
        if ch == "0": print(Fore.GREEN+"👋 Goodbye."+Style.RESET_ALL); break

        if ch in ("1","2","3"):
            room = mg.move(ch)
            print(THEME_ART.get(room.theme,""), end="")
            typewriter(f"{room.description}\n\n", Fore.WHITE)

            # mood-aware track pick
            if n:
                pick = q.popleft() if q else random.randrange(n)
                done.add(pick)
                wav = buf.pop(pick, None)
                t   = tracks[pick]
                if wav and wav.exists(): player.play_file(wav)
                else: player.play_full_from_youtube(t["artists"][0], t["name"])
                # queue another
                avail=[i for i in range(n) if i not in done and i not in q and i not in buf]
                if not avail: done.clear(); avail=list(range(n))
                nxt=random.choice(avail)
                threading.Thread(target=preload,args=(nxt,tracks,player,buf,q,done),daemon=True).start()
            continue

        if ch == "4":
            line = mg.talk()
            typewriter(line + "\n\n", Fore.MAGENTA)
            continue

        print(Fore.RED+"❓ Unknown command."+Style.RESET_ALL)

if __name__ == "__main__":
    main()
