#cli.py
import sys, time, random, threading, os, json
from collections import deque, Counter
import colorama
from colorama import Fore, Style

from config           import Config
from utils.platform_time import clear_screen
from utils.json_io    import load_json, save_json
from oauth.google     import GoogleCollector
from oauth.spotify    import SpotifyCollector
from audio.player     import AudioPlayer
from maze.generator   import MazeGenerator
import itertools
from llm.model_interface import streaming_query_npc

colorama.init(autoreset=True)

SESSION_SAVE_FILE = "mazeme_save.json"

def show_spinner(stop_event):
    spinner = itertools.cycle(['|', '/', '-', '\\'])
    while not stop_event.is_set():
        sys.stdout.write(Fore.YELLOW + "\rNPC is thinking... " + next(spinner) + Style.RESET_ALL)
        sys.stdout.flush()
        time.sleep(0.07)
    sys.stdout.write('\r' + ' ' * 30 + '\r')
    sys.stdout.flush()

def animated_intro():
    art = [
        r"    __  __                  ____        __           ",
        r"   |  \/  | __ _  ___ ___  |  _ \  ___ / _| ___ _ __ ",
        r"   | |\/| |/ _` |/ __/ _ \ | | | |/ _ \ |_ / _ \ '__|",
        r"   | |  | | (_| | (_|  __/ | |_| |  __/  _|  __/ |   ",
        r"   |_|  |_|\__,_|\___\___| |____/ \___|_|  \___|_|   ",
        r"              M A Z E   O F   M E                    ",
    ]
    for line in art:
        print(Fore.CYAN + line + Style.RESET_ALL)
        time.sleep(0.06)
    print()
    # Easter egg message
    if random.randint(1, 20) == 10:
        print(Fore.MAGENTA + "Easter Egg: The Maze remembers everything... or does it?" + Style.RESET_ALL)
        print()

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

def save_session(state):
    with open(SESSION_SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)

def load_session():
    if not os.path.exists(SESSION_SAVE_FILE):
        return None
    with open(SESSION_SAVE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def delete_session():
    if os.path.exists(SESSION_SAVE_FILE):
        os.remove(SESSION_SAVE_FILE)

def get_npc_response_bg(maze, dialogue_key, curr_room, log, result_holder, stop_event):
    try:
        npc_reply, npc_mem = maze.talk_with_context(dialogue_key, curr_room, log)
        if not npc_reply:
            npc_reply = "The figure seems lost in thought and does not respond right now."
        result_holder['npc_reply'] = npc_reply
        result_holder['npc_mem'] = npc_mem
    except Exception as e:
        print(f"[ERROR] NPC background thread failed: {e}")
        result_holder['npc_reply'] = "The figure seems lost in thought and does not respond right now."
        result_holder['npc_mem'] = ""
    finally:
        stop_event.set()

def main():
    clear_screen()
    animated_intro()

    # Model file check (robust error)
    model_path = os.path.join("models", "Phi-3-mini-4k-instruct-q4.gguf")
    if not os.path.exists(model_path):
        print(Fore.RED + "\n❌ Model file not found: models/Phi-3-mini-4k-instruct-q4.gguf" + Style.RESET_ALL)
        print(Fore.YELLOW + "Please run 'download_model.bat' in the 'models' folder before starting the game.\n" + Style.RESET_ALL)
        input("Press Enter to exit...")
        sys.exit(1)

    player = AudioPlayer(); player.play_main_music("main_music", "mp3")

    # Session: ask to load/continue game
    save_data = load_session()
    if save_data:
        print(Fore.YELLOW + "Previous session found. Would you like to continue? (y/n)" + Style.RESET_ALL)
        if input(Fore.CYAN+"➤ "+Style.RESET_ALL).strip().lower().startswith("y"):
            prof      = save_data["prof"]
            room_idx  = save_data["room_idx"]
            log       = save_data["log"]
            visited   = save_data["visited"]
            moods     = save_data["moods"]
            npc_greeted = save_data["npc_greeted"]
        else:
            delete_session()
            prof = load_json(Config.PROFILE_PATH)
            room_idx, log, visited, moods, npc_greeted = 0, [], [], [], False
    else:
        prof = load_json(Config.PROFILE_PATH)
        room_idx, log, visited, moods, npc_greeted = 0, [], [], [], False

    typewriter("🔑 Logging-in with Google…\n\n")
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
    q, buf, done = deque(), {}, set()
    track_n = len(tracks)

    # Start
    if track_n:
        first = random.randrange(track_n)
        threading.Thread(target=player.preload_track,
                         args=(first,tracks,buf,q,done,feats),daemon=True).start()

    typewriter("🔍 Entering the Maze…\n\n", Fore.CYAN)
    curr_room = None

    # Restore session vars if continuing
    if save_data:
        maze.set_progress(visited, moods)
        npc_greeted = npc_greeted
    else:
        npc_greeted = False

    # Main loop vars
    last_feedback = None
    room_count = len(visited)
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
║ 7) Save & exit                               ║
║ 8) Stats/progress                            ║
║ i) Inventory        – view items             ║
║ 0) Quit           – exit game                ║
║ h or ?            – help menu                ║
╚═══════════════════════════════════════════════╝
""" + Style.RESET_ALL

    # In-game mini-game trigger
    MINI_GAME_ROOMS = {"special", "exam", "puzzle"}

    def show_loading_spinner(msg="Loading..."):
        stop_event = threading.Event()
        def spinner():
            sp = itertools.cycle(['|', '/', '-', '\\'])
            while not stop_event.is_set():
                sys.stdout.write(Fore.YELLOW + f"\r{msg} " + next(sp) + Style.RESET_ALL)
                sys.stdout.flush()
                time.sleep(0.07)
            sys.stdout.write('\r' + ' ' * 40 + '\r')
            sys.stdout.flush()
            print()
        t = threading.Thread(target=spinner)
        t.start()
        return stop_event

    while True:
        print(MENU)
        ch = input(Fore.CYAN+"➤ "+Style.RESET_ALL).strip().lower()
        if ch in ("h","?"):
            print(MENU)
            continue
        if ch == "0":
            print(Fore.GREEN+"👋 Goodbye."+Style.RESET_ALL)
            print(Fore.YELLOW + "Want to send feedback or feature requests? Open an issue at https://github.com/bakill3/maze-of-me/issues" + Style.RESET_ALL)
            delete_session()
            break

        if ch == "7":  # Save & exit
            state = {
                "prof": prof,
                "room_idx": room_idx,
                "log": log,
                "visited": visited,
                "moods": moods,
                "npc_greeted": npc_greeted
            }
            save_session(state)
            print(Fore.YELLOW + "Session saved. See you next time!" + Style.RESET_ALL)
            break

        if ch == "8":
            # Show stats/progress
            total = len(visited)
            if total:
                c = Counter(moods)
                most = c.most_common(1)[0][0]
                print(Fore.CYAN + f"\nYou visited {total} rooms. Most common mood: {most}" + Style.RESET_ALL)
                print(Fore.YELLOW + "Mood breakdown: " + ", ".join(f"{m}:{n}" for m, n in c.items()) + Style.RESET_ALL)
                if 'sad' in c and c['sad'] > total // 2:
                    print(Fore.RED + "Warning: A shadow of sadness follows you. Maybe try some happy music?" + Style.RESET_ALL)
                elif 'happy' in c and c['happy'] > total // 2:
                    print(Fore.GREEN + "Your journey is bright and optimistic!" + Style.RESET_ALL)
                # --- Enhanced analytics: NPCs and contacts ---
                npc_stats = maze.get_npc_stats()
                print(Fore.MAGENTA + f"\nNPCs encountered: {npc_stats['total_npcs']}" + Style.RESET_ALL)
                if npc_stats['most_npc']:
                    print(Fore.MAGENTA + f"Most frequent NPC: {npc_stats['most_npc']}" + Style.RESET_ALL)
                if npc_stats['most_contact']:
                    print(Fore.MAGENTA + f"Most referenced contact: {npc_stats['most_contact']}" + Style.RESET_ALL)
                if npc_stats['contact_mentions']:
                    print(Fore.YELLOW + "Contact mentions: " + ", ".join(f"{k}:{v}" for k,v in npc_stats['contact_mentions'].items()) + Style.RESET_ALL)
            else:
                print(Fore.CYAN + "No progress yet! Enter a room to begin." + Style.RESET_ALL)
            continue

        if ch in ("1","2","3"):
            stop_event = show_loading_spinner("Moving to next room...")
            room_idx += 1
            curr_room = maze.move(ch)
            stop_event.set()
            npc_greeted = False
            visited.append(curr_room.description)
            moods.append(curr_room.theme)
            log.append(f"Room #{room_idx}: {curr_room.theme} – {curr_room.description}")
            print(Fore.CYAN + f"\nRoom #{room_idx} {curr_room.theme}" + Style.BRIGHT)
            typewriter(curr_room.description+"\n\n", Fore.WHITE)

            # Mini-game in "special" rooms (randomly, or by keyword)
            if any(key in curr_room.theme.lower() or key in curr_room.description.lower() for key in MINI_GAME_ROOMS):
                print(Fore.GREEN + "\nMini-game: Solve this riddle or type 'skip' to continue." + Style.RESET_ALL)
                print("What walks on four legs in the morning, two legs at noon, and three legs in the evening?")
                stop_event = show_loading_spinner("Waiting for your answer...")
                ans = input(Fore.CYAN+"➤ "+Style.RESET_ALL).strip().lower()
                stop_event.set()
                if "man" in ans or "human" in ans:
                    print(Fore.GREEN + "Correct! The Sphinx would be proud." + Style.RESET_ALL)
                    log.append("Mini-game: solved Sphinx riddle")
                elif ans == "skip":
                    print(Fore.YELLOW + "Skipped the riddle. The maze grows more mysterious..." + Style.RESET_ALL)
                    log.append("Mini-game: skipped Sphinx riddle")
                else:
                    print(Fore.RED + "Not quite right, but the maze lets you pass..." + Style.RESET_ALL)
                    log.append(f"Mini-game: incorrect answer '{ans}'")

            # --- Improved music loading ---
            if track_n:
                emotion = curr_room.theme
                stop_event = show_loading_spinner("Loading music...")
                idx = player.pick_track_by_emotion(emotion, tracks, feats)
                player.delete_last_cache()
                done.add(idx)
                tr  = tracks[idx]
                wav = buf.pop(idx, None)
                if wav and wav.exists():
                    player.play_file(wav)
                else:
                    # Start download in background, play a fallback if needed
                    bg_event = threading.Event()
                    def bg_download():
                        player.play_full_from_youtube(tr["artists"][0], tr["name"])
                        bg_event.set()
                    t = threading.Thread(target=bg_download)
                    t.start()
                    # Optionally play a short sound or message while waiting
                    t.join(timeout=2.5)  # Wait up to 2.5s, then continue
                stop_event.set()
                # Preload next track in background for next room
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
                # --- Streaming output with debug and timeout ---
                prompt = maze._gen_npc(curr_room.description, "greeting", log)[0]
                stop_event = threading.Event()
                first_token = [False]
                token_received = [False]
                def spinner():
                    sp = itertools.cycle(['|', '/', '-', '\\'])
                    start_time = time.time()
                    while not stop_event.is_set() and not first_token[0]:
                        sys.stdout.write(Fore.YELLOW + "\rNPC is thinking... " + next(sp) + Style.RESET_ALL)
                        sys.stdout.flush()
                        time.sleep(0.07)
                        # Timeout after 10s if no token
                        if time.time() - start_time > 10:
                            stop_event.set()
                    sys.stdout.write('\r' + ' ' * 40 + '\r')
                    sys.stdout.flush()
                    print()
                    print()
                t = threading.Thread(target=spinner)
                t.start()
                reply_buf = []
                try:
                    # Debug: entering streaming_query_npc
                    # print("[DEBUG] Entering streaming_query_npc...")
                    for token in streaming_query_npc(prompt):
                        token_received[0] = True
                        if not first_token[0]:
                            first_token[0] = True
                            stop_event.set()
                            t.join()
                            print(Fore.MAGENTA + "NPC: " + Style.BRIGHT, end="")
                            sys.stdout.flush()
                        sys.stdout.write(token)
                        sys.stdout.flush()
                        reply_buf.append(token)
                        time.sleep(0.025)
                except Exception as e:
                    stop_event.set()
                    t.join()
                    print(Fore.RED + f"\n[ERROR] Streaming failed: {e}" + Style.RESET_ALL)
                if not token_received[0]:
                    stop_event.set()
                    t.join()
                    print(Fore.RED + "\n[ERROR] No AI output received. (Is the model running? Is streaming_query_npc working?)" + Style.RESET_ALL)
                    print(Fore.YELLOW + "Falling back to slow/blocking mode..." + Style.RESET_ALL)
                    # Fallback to blocking
                    stop_event = show_loading_spinner("NPC is thinking...")
                    result_holder = {}
                    bg_event = threading.Event()
                    t2 = threading.Thread(target=get_npc_response_bg, args=(maze, "greeting", curr_room, log, result_holder, bg_event))
                    t2.start()
                    t2.join(timeout=8)
                    stop_event.set()
                    npc_reply = result_holder.get('npc_reply', '')
                    print(Fore.MAGENTA + "NPC: " + Style.BRIGHT + npc_reply + Style.RESET_ALL)
                    log.append(f"[NPC] (greeting): {npc_reply}")
                else:
                    print(Style.RESET_ALL)
                    npc_reply = ''.join(reply_buf)
                    log.append(f"[NPC] (greeting): {npc_reply}")
                npc_greeted = True
                print(Fore.YELLOW + "\nHow will you address the figure?\n" + Style.RESET_ALL)
                d_opt = choose("Choose:", DIALOGUE_OPTIONS)
            else:
                print(Fore.YELLOW + "\nHow will you address the figure?\n" + Style.RESET_ALL)
                d_opt = choose("Choose:", DIALOGUE_OPTIONS)
                # --- Streaming output for follow-up dialogue with debug and timeout ---
                prompt = maze._gen_npc(curr_room.description, d_opt, log)[0]
                stop_event = threading.Event()
                first_token = [False]
                token_received = [False]
                def spinner():
                    sp = itertools.cycle(['|', '/', '-', '\\'])
                    start_time = time.time()
                    while not stop_event.is_set() and not first_token[0]:
                        sys.stdout.write(Fore.YELLOW + "\rNPC is thinking... " + next(sp) + Style.RESET_ALL)
                        sys.stdout.flush()
                        time.sleep(0.07)
                        if time.time() - start_time > 10:
                            stop_event.set()
                    sys.stdout.write('\r' + ' ' * 40 + '\r')
                    sys.stdout.flush()
                t = threading.Thread(target=spinner)
                t.start()
                reply_buf = []
                try:
                    for token in streaming_query_npc(prompt):
                        token_received[0] = True
                        if not first_token[0]:
                            first_token[0] = True
                            stop_event.set()
                            t.join()
                            print(Fore.MAGENTA + "NPC: " + Style.BRIGHT, end="")
                            sys.stdout.flush()
                        sys.stdout.write(token)
                        sys.stdout.flush()
                        reply_buf.append(token)
                        time.sleep(0.025)
                except Exception as e:
                    stop_event.set()
                    t.join()
                    print(Fore.RED + f"\n[ERROR] Streaming failed: {e}" + Style.RESET_ALL)
                if not token_received[0]:
                    stop_event.set()
                    t.join()
                    print(Fore.RED + "\n[ERROR] No AI output received. (Is the model running? Is streaming_query_npc working?)" + Style.RESET_ALL)
                    print(Fore.YELLOW + "Falling back to slow/blocking mode..." + Style.RESET_ALL)
                    stop_event = show_loading_spinner("NPC is thinking...")
                    result_holder = {}
                    bg_event = threading.Event()
                    t2 = threading.Thread(target=get_npc_response_bg, args=(maze, d_opt, curr_room, log, result_holder, bg_event))
                    t2.start()
                    t2.join(timeout=8)
                    stop_event.set()
                    npc_reply = result_holder.get('npc_reply', '')
                    print(Fore.MAGENTA + "NPC: " + Style.BRIGHT + npc_reply + Style.RESET_ALL)
                    log.append(f"[Player] asked: '{dict(DIALOGUE_OPTIONS)[d_opt]}' – [NPC] replied: {npc_reply}")
                else:
                    print(Style.RESET_ALL)
                    npc_reply = ''.join(reply_buf)
                    log.append(f"[Player] asked: '{dict(DIALOGUE_OPTIONS)[d_opt]}' – [NPC] replied: {npc_reply}")
                print(Fore.YELLOW + "\nHow do you feel about this exchange?\n" + Style.RESET_ALL)
                stop_event = show_loading_spinner("Recording your reaction...")
                fb = choose("React:", FEEDBACK_OPTIONS)
                stop_event.set()
                last_feedback = dict(FEEDBACK_OPTIONS)[fb]
                log.append(f"Player emotional feedback: {last_feedback}")
                maze.record_feedback(last_feedback)
                continue
            dialogue_label = dict(DIALOGUE_OPTIONS)[d_opt]
            stop_event = show_loading_spinner("NPC is thinking...")
            result_holder = {}
            bg_event = threading.Event()
            t = threading.Thread(target=get_npc_response_bg, args=(maze, d_opt, curr_room, log, result_holder, bg_event))
            t.start()
            t.join(timeout=8)  # Wait up to 8s for LLM, then continue
            stop_event.set()
            npc_reply = result_holder.get('npc_reply', '')
            npc_mem = result_holder.get('npc_mem', '')
            print(Fore.MAGENTA + "NPC: " + Style.BRIGHT + npc_reply + Style.RESET_ALL)
            log.append(f"[Player] asked: '{dialogue_label}' – [NPC] replied: {npc_reply}")
            if npc_mem:
                log.append(f"  (NPC remembered: {npc_mem})")
            print(Fore.YELLOW + "\nHow do you feel about this exchange?\n" + Style.RESET_ALL)
            stop_event = show_loading_spinner("Recording your reaction...")
            fb = choose("React:", FEEDBACK_OPTIONS)
            stop_event.set()
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
            stop_event = show_loading_spinner("Inspecting item...")
            npc_comment = maze.inspect_furniture(furniture)
            stop_event.set()
            print(Fore.MAGENTA + "NPC: " + Style.BRIGHT + npc_comment + Style.RESET_ALL)
            log.append(f"Inspected furniture: {furniture} – [NPC] commented: {npc_comment}")
            # Show items in the room
            items = maze.get_room_items()
            if items:
                print(Fore.YELLOW + f"\nYou see items here: {', '.join(items)}" + Style.RESET_ALL)
                print(Fore.YELLOW + "Type the name of an item to collect it, or press Enter to skip." + Style.RESET_ALL)
                item_choice = input(Fore.CYAN+"➤ "+Style.RESET_ALL).strip()
                if item_choice and item_choice in items:
                    if maze.collect_item(item_choice):
                        print(Fore.GREEN + f"Collected: {item_choice}" + Style.RESET_ALL)
                    else:
                        print(Fore.RED + "Couldn't collect that item." + Style.RESET_ALL)
            continue
        if ch == "i":
            # Show inventory
            inv = maze.get_inventory()
            print(Fore.YELLOW + "\nYour inventory:" + Style.RESET_ALL)
            if inv:
                for it in inv:
                    print(Fore.CYAN + f"- {it}" + Style.RESET_ALL)
            else:
                print(Fore.CYAN + "(empty)" + Style.RESET_ALL)
            continue

        print(Fore.RED+"❓ Unknown command."+Style.RESET_ALL)

if __name__ == "__main__":
    main()
