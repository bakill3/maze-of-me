# File: cli.py
import sys, time, random, threading
from collections import deque
import colorama
from colorama import Fore, Style

from config           import Config
from utils.platform_time import clear_screen
from utils.json_io    import load_json
from oauth.google     import GoogleCollector
from oauth.spotify    import SpotifyCollector
from audio.player     import AudioPlayer
from maze.generator   import MazeGenerator

colorama.init(autoreset=True)

# ───── static art ────────────────────────────────────────────────
THEME_ART = {
    "happy":   Fore.YELLOW  + "  ☀️  a radiant chamber ☀️\n",
    "sad":     Fore.BLUE    + "  ☔  a weeping hall ☔\n",
    "angry":   Fore.RED     + "  🔥  a seething vault 🔥\n",
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

def typewriter(txt, color=Fore.GREEN, delay=.01):
    for c in txt: sys.stdout.write(color + c); sys.stdout.flush(); time.sleep(delay)
    print(Style.RESET_ALL, end="")

# ───── music preload helper ──────────────────────────────────────
def _preload(idx, tracks, player, buf, queue, done):
    if idx in done or idx in buf: return
    t = tracks[idx]
    try:
        src = player.download_youtube(t["artists"][0], t["name"])
        wav = player.convert_to_wav(src)
        buf[idx] = wav; queue.append(idx)
    except: pass

# ───── main ──────────────────────────────────────────────────────
def main():
    clear_screen()
    player = AudioPlayer(); player.play_main_music("main_music", "mp3")
    print(BANNER); typewriter("🔑 Logging-in with Google…\n\n")

    # ── Google first (mandatory) ────────────────────────────────
    if not (prof := load_json(Config.PROFILE_PATH)) or not prof.get("google"):
        g = GoogleCollector()           # one instance
        g.authenticate()                # opens browser once
        g.fetch_and_save()              # re-uses stored tokens
        prof = load_json(Config.PROFILE_PATH)

    # ── Spotify (mandatory) ───────────────────────────────
    if not (prof or {}).get("spotify"):
        s = SpotifyCollector()          # keep ONE instance
        s.authenticate()                # user approves once
        s.fetch_and_save()              # uses cached tokens
        prof = load_json(Config.PROFILE_PATH)


    # ── build objects ──────────────────────────────────────────
    tracks = prof["spotify"]["top_tracks"] if prof.get("spotify") else []
    track_n = len(tracks)
    maze    = MazeGenerator(prof)

    q, buf, done = deque(), {}, set()
    if track_n:
        first = random.randrange(track_n)
        threading.Thread(target=_preload,
                         args=(first,tracks,player,buf,q,done),
                         daemon=True).start()

    typewriter("🔍 Entering the Maze…\n\n", Fore.CYAN)

    while True:
        print(MENU)
        ch = input(Fore.CYAN+"➤ "+Style.RESET_ALL).strip().lower()
        if ch in ("h","?"): continue
        if ch == "0": print(Fore.GREEN+"👋 Goodbye."+Style.RESET_ALL); break

        if ch in ("1","2","3"):
            room = maze.move(ch)
            print(THEME_ART.get(room.theme,""), end="")
            typewriter(room.description+"\n\n", Fore.WHITE)

            # play music   (single-ahead buffer)
            if track_n:
                # take pre-loaded if we have it, otherwise random fallback
                idx = q.popleft() if q else random.randrange(track_n)
                done.add(idx)
                tr  = tracks[idx]
                wav = buf.pop(idx, None)

                if wav and wav.exists():
                    # <-- FIX: pass exactly one arg
                    player.play_file(wav)
                else:
                    player.play_full_from_youtube(tr["artists"][0], tr["name"])

                # schedule ONE ahead
                avail = [i for i in range(track_n) if i not in done and i not in buf and i not in q]
                if not avail: done.clear(); avail=list(range(track_n))
                nxt = random.choice(avail)
                threading.Thread(target=_preload,
                                 args=(nxt,tracks,player,buf,q,done),daemon=True).start()
            continue

        if ch == "4":
            typewriter(maze.talk()+"\n\n", Fore.MAGENTA); continue

        print(Fore.RED+"❓ Unknown command."+Style.RESET_ALL)

if __name__ == "__main__":
    main()
