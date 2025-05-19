import subprocess, os, random, pygame, requests
from pathlib import Path
from yt_dlp import YoutubeDL

PROJECT = Path(__file__).parent.parent
CACHE   = PROJECT / "audio_cache"
RAW     = CACHE / "raw"
WAV     = CACHE / "wav"
for p in (RAW, WAV): p.mkdir(parents=True, exist_ok=True)

YDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "outtmpl": str(RAW / "%(id)s.%(ext)s"),
    "noplaylist": True,
    "cachedir": False,
}

EMOTION_PLAYLIST = {
    "happy":   range(0, 5),
    "vibrant": range(0, 5),
    "sad":     range(5, 10),
    "calm":    range(5, 10),
    "angry":   range(10, 15),
    "tense":   range(10, 15),
    "neutral": range(0, 20),
}

class AudioPlayer:
    def __init__(self):
        pygame.mixer.init()

    # ───── helpers ────────────────────────────────────────────────────
    def download_youtube(self, artist: str, title: str) -> Path:
        query = f"ytsearch1:{artist} - {title}"
        with YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(query, download=True)
        entry = info["entries"][0] if "entries" in info else info
        return RAW / f"{entry['id']}.{entry['ext']}"

    def convert_to_wav(self, src: Path) -> Path:
        wav = WAV / f"{src.stem}.wav"
        if wav.exists(): return wav
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), str(wav)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return wav

    def play_file(self, wav_path: Path):
        pygame.mixer.music.load(str(wav_path))
        pygame.mixer.music.play()

    # ───── public API ────────────────────────────────────────────────
    def play_main_music(self, stem: str, ext: str = "mp3"):
        path = PROJECT / f"{stem}.{ext}"
        if path.exists(): self.play_file(self.convert_to_wav(path))

    def play_full_from_youtube(self, artist: str, title: str):
        wav = self.convert_to_wav(self.download_youtube(artist, title))
        self.play_file(wav)

    def pick_track_index(self, emotion: str, total: int) -> int:
        pool = [i for i in EMOTION_PLAYLIST.get(emotion, range(total)) if i < total]
        return random.choice(pool or list(range(total)))
