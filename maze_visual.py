import os, sys, pygame, random, time
from pathlib import Path
from utils.json_io import load_json
from maze.generator import MazeGenerator
from config import Config

ASSET_DIR = Path("assets")
WIN_W, WIN_H = 1100, 700
FONT_SIZE = 28
FONT_PATH = None  # Use system font for emojis if available

MUSIC_PATH = Path("main_music.mp3")  # Path to main music file
LOG_LINES = 10

EMOTION_COLORS = {
    "happy": (253, 242, 99),
    "sad": (105, 148, 190),
    "angry": (222, 74, 66),
    "neutral": (180, 180, 180)
}

def get_font(size):
    # Try emoji-support font if present, else system fallback
    if FONT_PATH and Path(FONT_PATH).exists():
        return pygame.font.Font(FONT_PATH, size)
    return pygame.font.SysFont("Segoe UI Emoji", size, bold=True)

def draw_text(surface, text, pos, font, color, max_width=1000):
    """Draw text with word-wrapping, returns next y."""
    x, y = pos
    words = text.split(' ')
    line = ""
    for word in words:
        test_line = line + word + " "
        if font.size(test_line)[0] > max_width:
            surf = font.render(line, True, color)
            surface.blit(surf, (x, y))
            y += surf.get_height() + 3
            line = word + " "
        else:
            line = test_line
    surf = font.render(line, True, color)
    surface.blit(surf, (x, y))
    return y + surf.get_height()

def random_furniture_sprite(asset_dir):
    pngs = [f for f in asset_dir.iterdir() if f.suffix == ".png" and not f.name.startswith("npc")]
    return random.choice(pngs) if pngs else None

def random_npc_sprite(asset_dir, emotion="neutral"):
    # Try to find an npc sprite matching the emotion, fallback to any npc
    files = [f for f in asset_dir.glob(f"npc_{emotion}*.png")]
    if not files:
        files = list(asset_dir.glob("npc*.png"))
    if files:
        return random.choice(files)
    return None

def load_sprite(path, fallback_color, size=(120, 120)):
    try:
        surf = pygame.image.load(str(path)).convert_alpha()
        return pygame.transform.smoothscale(surf, size)
    except Exception:
        surf = pygame.Surface(size)
        surf.fill(fallback_color)
        return surf

def play_music(music_path):
    try:
        pygame.mixer.music.load(str(music_path))
        pygame.mixer.music.set_volume(0.4)
        pygame.mixer.music.play(-1)
    except Exception as e:
        print("[Music] Error loading music:", e)

def spinner_animation(surface, msg, font, tick):
    surface.fill((24,24,32))
    dots = "." * (tick % 4)
    text = f"{msg}{dots}"
    txtsurf = font.render(text, True, (253,242,99))
    surface.blit(txtsurf, (WIN_W//2 - txtsurf.get_width()//2, WIN_H//2-20))
    pygame.display.flip()

def show_loading_screen(screen, big_font):
    tick = 0
    for _ in range(16):  # ~2 seconds
        spinner_animation(screen, "Maze of Me is loading", big_font, tick)
        pygame.time.wait(120)
        tick += 1

def main():
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_caption("Maze of Me (Visual)")
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    clock = pygame.time.Clock()
    font = get_font(FONT_SIZE)
    small_font = get_font(19)
    big_font = get_font(38)

    # --- Loading screen & music ---
    show_loading_screen(screen, big_font)
    if MUSIC_PATH.exists():
        play_music(MUSIC_PATH)

    # -- Load profile, Maze --
    profile = load_json(Config.PROFILE_PATH)
    if not profile:
        screen.fill((30,0,0))
        draw_text(screen, "Profile not found. Please run CLI first!", (40, WIN_H//2), big_font, (220,40,40))
        pygame.display.flip()
        time.sleep(3)
        return

    maze = MazeGenerator(profile)
    log = []
    npc_text = ""

    # -- First Room
    room = maze.move(str(random.randint(1,3)))
    screen.fill(EMOTION_COLORS.get(room.theme, (100,100,100)))
    draw_text(screen, "Generating NPC...", (WIN_W//2-120, WIN_H//2), font, (60,0,80))
    pygame.display.flip()
    t0 = time.time()
    npc_text, _ = maze.talk_with_context("greeting", room, log)
    log.append(f"[NPC]: {npc_text}")
    t1 = time.time()
    print(f"[INFO] First room NPC generated in {t1-t0:.1f}s")

    running = True
    show_log = False
    footer_msg = "[←/→]: Move | [Space]: Talk | [L]: Log | [Q]: Quit"
    last_npc_text = npc_text
    npc_thinking = False

    # --- Room Music per mood (Spotify logic, simplified, uses only local mp3 for now) ---
    # For real Spotify preview logic, use your AudioPlayer and integrate here.

    while running:
        screen.fill(EMOTION_COLORS.get(room.theme, (100,100,100)))

        # --- Draw furniture sprite ---
        furn_path = random_furniture_sprite(ASSET_DIR)
        if furn_path:
            furniture_sprite = load_sprite(furn_path, (120,80,60), (170, 130))
            screen.blit(furniture_sprite, (WIN_W//4, WIN_H//2 - 80))

        # --- Draw NPC sprite (by mood) ---
        npc_path = random_npc_sprite(ASSET_DIR, room.theme)
        if npc_path:
            npc_sprite = load_sprite(npc_path, (200,100,200), (110, 160))
            screen.blit(npc_sprite, (WIN_W//2 + 180, WIN_H//2 - 120))

        # --- Room description, top bar ---
        draw_text(screen, f"Room: {room.theme.title()} | {room.furniture.title()}", (24, 24), big_font, (40,30,35))
        ydesc = 70
        ydesc = draw_text(screen, room.description, (24, ydesc), font, (20,20,24), max_width=WIN_W-48)

        # --- Draw NPC text ---
        if last_npc_text:
            # Emojis: replace :) etc with real unicode emoji
            text_disp = last_npc_text.replace(":)", "😊").replace(":(", "😢").replace(">:(", "😡").replace(":|", "😐")
            draw_text(screen, text_disp.replace("[NPC]: ", ""), (WIN_W//2-240, WIN_H-180), big_font, (60,0,80), max_width=500)

        # --- Draw log (L key) ---
        if show_log:
            pygame.draw.rect(screen, (255,255,252,245), (16, WIN_H-240, WIN_W-32, 220))
            log_lines = log[-LOG_LINES:]
            for i, entry in enumerate(log_lines):
                draw_text(screen, entry, (30, WIN_H-230 + i*20), small_font, (22,22,22), max_width=WIN_W-80)

        # -- Footer
        draw_text(screen, footer_msg, (24, WIN_H-34), small_font, (110,110,100))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN and not npc_thinking:
                if event.key == pygame.K_RIGHT:
                    # Next room
                    room = maze.move("2")
                    # Play music per room (use audio logic here)
                    # Show spinner
                    t = 0
                    for _ in range(8):
                        spinner_animation(screen, "Moving...", font, t)
                        pygame.time.wait(65)
                        t += 1
                    npc_thinking = True
                    spinner_animation(screen, "NPC is thinking", font, t)
                    pygame.display.flip()
                    last_npc_text, _ = maze.talk_with_context("greeting", room, log)
                    log.append(f"[NPC]: {last_npc_text}")
                    npc_thinking = False

                if event.key == pygame.K_LEFT:
                    room = maze.move("1")
                    t = 0
                    for _ in range(8):
                        spinner_animation(screen, "Moving...", font, t)
                        pygame.time.wait(65)
                        t += 1
                    npc_thinking = True
                    spinner_animation(screen, "NPC is thinking", font, t)
                    pygame.display.flip()
                    last_npc_text, _ = maze.talk_with_context("greeting", room, log)
                    log.append(f"[NPC]: {last_npc_text}")
                    npc_thinking = False

                if event.key == pygame.K_SPACE:
                    # Player talks to NPC: block main thread, show spinner
                    npc_thinking = True
                    for j in range(10):
                        spinner_animation(screen, "NPC is thinking", font, j)
                        pygame.time.wait(90)
                    pygame.display.flip()
                    last_npc_text, _ = maze.talk_with_context("a", room, log)
                    log.append(f"[NPC]: {last_npc_text}")
                    npc_thinking = False

                if event.key == pygame.K_l:
                    show_log = not show_log

                if event.key == pygame.K_q:
                    running = False

        clock.tick(35)

    pygame.quit()

if __name__ == "__main__":
    main()
