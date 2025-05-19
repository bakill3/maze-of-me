# File: audio/player.py
import subprocess, requests, os
from pathlib import Path
import pygame
from yt_dlp import YoutubeDL

ROOT   = Path(__file__).parent.parent
RAW    = ROOT / "audio_cache" / "raw"
WAV    = ROOT / "audio_cache" / "wav"
RAW.mkdir(parents=True, exist_ok=True)
WAV.mkdir(parents=True, exist_ok=True)

YTDLP = {"format":"bestaudio", "quiet":True, "outtmpl":str(RAW / "%(id)s.%(ext)s")}

class AudioPlayer:
    def __init__(self):
        pygame.mixer.init()

    # ── helpers ──────────────────────────────────────────────────────
    def _yt(self, query_or_url:str) -> Path:
        with YoutubeDL(YTDLP) as ydl:
            info = ydl.extract_info(query_or_url, download=True)
        entry = info["entries"][0] if "entries" in info else info
        return RAW / f"{entry['id']}.{entry['ext']}"

    def _wav(self, src:Path) -> Path:
        dst = WAV / f"{src.stem}.wav"
        if not dst.exists():
            subprocess.run(["ffmpeg","-y","-i",str(src),str(dst)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return dst

    # ── public API ───────────────────────────────────────────────────
    def play_main_music(self, fname:str, ext:str="mp3"):
        p = Path(fname).with_suffix(f".{ext}")
        if not p.exists(): return
        pygame.mixer.music.load(str(p)); pygame.mixer.music.play(-1)

    def play_track(self, artist:str, title:str):
        src = self._yt(f"ytsearch1:{artist} - {title}")
        wav = self._wav(src)
        pygame.mixer.music.load(str(wav)); pygame.mixer.music.play()

    def play_file(self, wav:Path):     # from preload
        pygame.mixer.music.load(str(wav)); pygame.mixer.music.play()
        
    def play_full_from_youtube(self, artist: str, title: str):
        """alias kept for legacy code – just forwards to play_track()"""
        self.play_track(artist, title)
