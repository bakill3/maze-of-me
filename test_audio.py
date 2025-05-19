import json
import random
from pathlib import Path
from audio.player import AudioPlayer

def main():
    data = json.loads(Path("user_profile.json").read_text())
    tracks = data.get("spotify", {}).get("top_tracks", [])
    if not tracks:
        print("❌ No Spotify tracks in profile.")
        return

    # Pick a random track
    t = random.choice(tracks)
    artist = t["artists"][0]
    title  = t["name"]

    preview_url = t.get("preview_url")
    player = AudioPlayer()

    if preview_url:
        print(f"▶️ Playing preview for: {title} by {artist}")
        player.play_preview(preview_url)
    else:
        print(f"▶️ No preview; playing full track via YouTube for: {title} by {artist}")
        player.play_full_from_youtube(artist, title)

    input("Press ENTER to stop.")
    player.stop()

if __name__ == "__main__":
    main()
