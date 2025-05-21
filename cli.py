import sys, time, random, threading, itertools
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

def show_spinner(stop_event):
    spinner = itertools.cycle(['|', '/', '-', '\\'])
    while not stop_event.is_set():
        sys.stdout.write(Fore.YELLOW + "\rNPC is thinking... " + next(spinner) + Style.RESET_ALL)
        sys.stdout.flush()
        time.sleep(0.07)
    sys.stdout.write('\r' + ' ' * 30 + '\r')
    sys.stdout.flush()

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

DIALOGUE_OPTIONS = [
    ("a", "Who are you?"),
    ("b", "Explain this room."),
    ("c", "You’re lying."),
    ("d", "Stay silent."),
]
FEEDBACK_OPTIONS = [
    ("1", "😊 Happy"),
    ("2", "😢 Sad"),
    ("3", "😡 Angry"),
    ("4", "😐 Neutral"),
]

MENU = Fore.YELLOW + """
╔═══════════════════════════════════════════════╗
║             Maze of Me CLI                   ║
╠═══════════════════════════════════════════════╣
║ 1) Go Left        – move left                ║
║ 2) Go Right       – move right               ║
║ 3) Go Forward     – move ahead               ║
║ 4) Talk to figure – interact                 ║
║ 5) Inspect room/furniture                    ║
║ 6) View interaction log                      ║
║ 0) Quit           – exit game                ║
║ h or ?            – help menu                ║
╚═══════════════════════════════════════════════╝
""" + Style.RESET_ALL

def typewriter(txt, color=Fore.GREEN, delay=.01):
    for c in txt: sys.stdout.write(color + c); sys.stdout.flush(); time.sleep(delay)
    print(Style.RESET_ALL, end="")

def choose(prompt, options):
    print(prompt)
    for key, text in options:
        print(f"  {key}) {text}")
    valid = {k for k, _ in options}
    while True:
        ch = input(Fore.CYAN+"➤ "+Style.RESET_ALL).strip().lower()
        if ch in valid:
            return ch
        print(Fore.RED+"❓ Invalid option. Please type one of: " + ", ".join(valid) + Style.RESET_ALL)

def main():
    clear_screen()
    player = AudioPlayer(); player.play_main_music("main_music", "mp3")
    print(BANNER); typewriter("🔑 Logging-in with Google…\n\n")

    # ── Google first (mandatory) ────────────────────────────────
    prof = load_json(Config.PROFILE_PATH)
    if not (prof and prof.get("google")):
        g = GoogleCollector()
        g.authenticate()
        g.fetch_and_save()
        prof = load_json(Config.PROFILE_PATH)

    # ── Spotify (mandatory) ───────────────────────────────
    if not prof.get("spotify"):
        s = SpotifyCollector()
        s.authenticate()
        s.fetch_and_save()
        prof = load_json(Config.PROFILE_PATH)

    tracks = prof["spotify"]["top_tracks"] if prof.get("spotify") else []
    feats = prof["spotify"].get("audio_features", {}) if prof.get("spotify") else {}
    maze    = MazeGenerator(prof)
    log     = []
    room_count = 0
    last_feedback = None

    q, buf, done = deque(), {}, set()
    track_n = len(tracks)
    room_idx = 0  # Start at 0, will increment to 1 on first move

    if track_n:
        first = random.randrange(track_n)
        threading.Thread(target=player.preload_track,
                         args=(first,tracks,buf,q,done,feats),daemon=True).start()

    typewriter("🔍 Entering the Maze…\n\n", Fore.CYAN)
    curr_room = None
    npc_greeted = False

    while True:
        print(MENU)
        ch = input(Fore.CYAN+"➤ "+Style.RESET_ALL).strip().lower()
        if ch in ("h","?"):
            print(MENU)
            continue
        if ch == "0":
            print(Fore.GREEN+"👋 Goodbye."+Style.RESET_ALL)
            break

        if ch in ("1","2","3"):
            # Room transition: increment, play music, cleanup
            room_count += 1
            room_idx += 1
            curr_room = maze.move(ch)
            npc_greeted = False  # NPC should greet first time you enter
            log.append(f"Room #{room_idx}: {curr_room.theme} – {curr_room.description}")

            print(Fore.CYAN + f"\nRoom #{room_idx}\n" + Style.BRIGHT, end="")
            print(THEME_ART.get(curr_room.theme,""), end="")
            typewriter(curr_room.description+"\n\n", Fore.WHITE)

            # Emotion-matched music
            if track_n:
                emotion = curr_room.theme
                idx = player.pick_track_by_emotion(emotion, tracks, feats)
                player.delete_last_cache()  # Delete previous music files
                done.add(idx)
                tr  = tracks[idx]
                wav = buf.pop(idx, None)
                if wav and wav.exists():
                    player.play_file(wav)
                else:
                    player.play_full_from_youtube(tr["artists"][0], tr["name"])
                # Preload next
                avail = [i for i in range(track_n) if i not in done and i not in buf and i not in q]
                if not avail: done.clear(); avail=list(range(track_n))
                nxt = random.choice(avail)
                threading.Thread(target=player.preload_track,
                                 args=(nxt,tracks,buf,q,done,feats),daemon=True).start()
            continue

        if ch == "4":
            if not curr_room:
                print(Fore.RED + "You haven't entered a room yet." + Style.RESET_ALL)
                continue
            if not npc_greeted:
                stop_event = threading.Event()
                spinner_thread = threading.Thread(target=show_spinner, args=(stop_event,))
                spinner_thread.start()
                npc_reply, npc_mem = maze.talk_with_context("greeting", curr_room, log)
                stop_event.set()
                spinner_thread.join()
                print(Fore.MAGENTA + "NPC: " + Style.BRIGHT + npc_reply + Style.RESET_ALL)
                log.append(f"[NPC] (greeting): {npc_reply}")
                npc_greeted = True
                print(Fore.YELLOW + "\nHow will you address the figure?\n" + Style.RESET_ALL)
                d_opt = choose("Choose:", DIALOGUE_OPTIONS)
            else:
                print(Fore.YELLOW + "\nHow will you address the figure?\n" + Style.RESET_ALL)
                d_opt = choose("Choose:", DIALOGUE_OPTIONS)
                stop_event = threading.Event()
                spinner_thread = threading.Thread(target=show_spinner, args=(stop_event,))
                spinner_thread.start()
                npc_reply, npc_mem = maze.talk_with_context(d_opt, curr_room, log)
                stop_event.set()
                spinner_thread.join()
                print(Fore.MAGENTA + "NPC: " + Style.BRIGHT + npc_reply + Style.RESET_ALL)
                log.append(f"[Player] asked: '{dict(DIALOGUE_OPTIONS)[d_opt]}' – [NPC] replied: {npc_reply}")
                if npc_mem:
                    log.append(f"  (NPC remembered: {npc_mem})")
                print(Fore.YELLOW + "\nHow do you feel about this exchange?\n" + Style.RESET_ALL)
                fb = choose("React:", FEEDBACK_OPTIONS)
                last_feedback = dict(FEEDBACK_OPTIONS)[fb]
                log.append(f"Player emotional feedback: {last_feedback}")
                maze.record_feedback(last_feedback)
                continue
            
            dialogue_label = dict(DIALOGUE_OPTIONS)[d_opt]
            npc_reply, npc_mem = maze.talk_with_context(d_opt, curr_room, log)
            print(Fore.MAGENTA + "NPC: " + Style.BRIGHT + npc_reply + Style.RESET_ALL)
            log.append(f"[Player] asked: '{dialogue_label}' – [NPC] replied: {npc_reply}")
            if npc_mem:
                log.append(f"  (NPC remembered: {npc_mem})")
            # --- Feedback ---
            print(Fore.YELLOW + "\nHow do you feel about this exchange?\n" + Style.RESET_ALL)
            fb = choose("React:", FEEDBACK_OPTIONS)
            last_feedback = dict(FEEDBACK_OPTIONS)[fb]
            log.append(f"Player emotional feedback: {last_feedback}")
            maze.record_feedback(last_feedback)
            continue

        if ch == "5":
            if curr_room is None:
                print(Fore.RED + "You haven't entered a room yet." + Style.RESET_ALL)
                continue
            furniture = maze.get_room_furniture()
            print(Fore.YELLOW + f"\nInspecting: {furniture}\n" + Style.RESET_ALL)
            npc_comment = maze.inspect_furniture(furniture)
            print(Fore.MAGENTA + "NPC: " + Style.BRIGHT + npc_comment + Style.RESET_ALL)
            log.append(f"Inspected furniture: {furniture} – [NPC] commented: {npc_comment}")
            continue

        if ch == "6":
            print(Fore.GREEN + "\n=== Interaction Log ===" + Style.RESET_ALL)
            for entry in log[-30:]:
                print(" - " + entry)
            print(Fore.GREEN + "=======================\n" + Style.RESET_ALL)
            continue

        print(Fore.RED+"❓ Unknown command."+Style.RESET_ALL)

if __name__ == "__main__":
    main()
