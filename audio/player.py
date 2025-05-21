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
        self._last_wav_path = None
        self._last_raw_path = None

    def download_youtube(self, artist: str, title: str) -> Path:
        query = f"ytsearch1:{artist} - {title}"
        with YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(query, download=True)
        entry = info["entries"][0] if "entries" in info else info
        raw_path = RAW / f"{entry['id']}.{entry['ext']}"
        self._last_raw_path = raw_path
        return raw_path

    def convert_to_wav(self, src: Path) -> Path:
        wav = WAV / f"{src.stem}.wav"
        if wav.exists(): return wav
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), str(wav)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._last_wav_path = wav
        return wav

    def play_file(self, wav_path: Path):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        pygame.mixer.music.load(str(wav_path))
        pygame.mixer.music.play()

    def play_main_music(self, stem: str, ext: str = "mp3"):
        path = PROJECT / f"{stem}.{ext}"
        if path.exists(): self.play_file(self.convert_to_wav(path))

    def play_full_from_youtube(self, artist: str, title: str):
        self.delete_last_cache()
        wav = self.convert_to_wav(self.download_youtube(artist, title))
        self.play_file(wav)

    def pick_track_index(self, emotion: str, total: int) -> int:
        pool = [i for i in EMOTION_PLAYLIST.get(emotion, range(total)) if i < total]
        return random.choice(pool or list(range(total)))

    def pick_track_by_emotion(self, emotion, tracks, feats):
        if not feats or not tracks:
            return random.randrange(len(tracks))
        emotion_map = {
            "happy": lambda v,e: v > 0.7,
            "sad": lambda v,e: v < 0.3,
            "angry": lambda v,e: e > 0.7 and v < 0.4,
            "neutral": lambda v,e: 0.4 <= v <= 0.7 and 0.3 <= e <= 0.7,
        }
        test = emotion_map.get(emotion, lambda v,e: True)
        candidates = []
        for i, t in enumerate(tracks):
            feat = feats.get(t["id"], {})
            v = feat.get("valence", 0.5)
            e = feat.get("energy", 0.5)
            if test(v, e):
                candidates.append(i)
        return random.choice(candidates) if candidates else random.randrange(len(tracks))

    def preload_track(self, idx, tracks, buf, q, done, feats=None):
        if idx in done or idx in buf: return
        t = tracks[idx]
        try:
            src = self.download_youtube(t["artists"][0], t["name"])
            wav = self.convert_to_wav(src)
            buf[idx] = wav; q.append(idx)
        except Exception:
            pass

    def delete_last_cache(self):
        # Remove last played wav and raw file from previous room
        try:
            if self._last_wav_path and self._last_wav_path.exists():
                self._last_wav_path.unlink()
            if self._last_raw_path and self._last_raw_path.exists():
                self._last_raw_path.unlink()
        except Exception:
            pass
        self._last_wav_path = None
        self._last_raw_path = None
