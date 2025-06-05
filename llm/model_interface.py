"""
Phi-3 Mini LLaMA wrapper – only NPC speech.
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from llama_cpp import Llama
from config import Config
import threading
from functools import lru_cache
import hashlib
import re
import random
from typing import Dict, Set

from utils.parsers import get_random_personal_ref

MODEL_NAME = "Phi-3-mini-4k-instruct-q4.gguf"
MODEL_PATH = Config.MODELS_DIR / MODEL_NAME

print(f"\n[INFO] Loading model from: {MODEL_PATH}")
print(f"[INFO] Model file exists: {MODEL_PATH.exists()}")

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"\n[ERROR] Model not found: {MODEL_PATH}\n"
        f"Please run 'download.bat' in the 'models' folder before starting the game.\n"
    )

# High performance configuration tuned via environment variables. Uses all
# available CPU cores and optional GPU layers for maximum speed on capable
# hardware.
_llm = Llama(
    model_path=str(MODEL_PATH),
    n_ctx=Config.CTX_SIZE,
    n_threads=Config.N_THREADS,
    n_gpu_layers=Config.GPU_LAYERS,
    verbose=False,
)

# Read given name for prompt stopping
try:
    GIVEN = json.loads(Config.PROFILE_PATH.read_text("utf-8")).get("full_name", "").split()[0]
except Exception:
    GIVEN = ""

# STOP = ["\n", "Assistant:", f"{GIVEN}:", "<END>"]
STOP = ["Assistant:", f"{GIVEN}:", "<END>"]

# Simple in-memory cache for LLM responses (prompt -> reply)
_llm_cache = {}

LLM_LOCK = threading.Lock()

FALLBACK_NPC = "The figure seems lost in thought and does not respond right now."

def _run(prompt: str, max_tokens: int, temperature: float) -> str:
    # Aggressive cache: use hash of prompt for similar situations
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    cache_key = (prompt_hash, max_tokens, temperature)
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]
    try:
        with LLM_LOCK:
            res = _llm(prompt=prompt, max_tokens=max_tokens, temperature=temperature, stop=STOP)
        text = res["choices"][0]["text"].strip()
        text = _clean_output(text)
        if text:
            _llm_cache[cache_key] = text
        return text
    except Exception as e:
        print(f"[ERROR] Llama model inference failed: {e}")
        return ""

def query_npc(prompt: str, max_tokens: int = 100) -> str:
    # Try up to 2 times, fallback if still empty
    for _ in range(2):
        reply = _run(prompt, max_tokens=max_tokens, temperature=0.8)
        if reply:
            return reply
    return FALLBACK_NPC

def streaming_query_npc(prompt: str, max_tokens: int = 60, temperature: float = 0.8):
    """Return a single cleaned sentence from the model."""
    try:
        with LLM_LOCK:
            buf = ""
            got_chunk = False
            for chunk in _llm(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=STOP,
                stream=True,
            ):
                token = chunk["choices"][0]["text"].encode("ascii", "ignore").decode()
                token = token.replace("from=\"", "").replace("to=\"", "")
                token = token.replace("djvu", "")
                token = re.sub(r"\[\d{1,3}\]", "", token)
                token = re.sub(r"<!--.*?-->", "", token)
                if token.strip():
                    got_chunk = True
                buf += token
                if re.search(r"[.!?]", buf):
                    break
                if len(buf.split()) > 45:
                    break
            if got_chunk:
                yield _clean_output(buf)
            else:
                fallback = _run(prompt, max_tokens, temperature)
                if fallback:
                    yield fallback
                else:
                    yield "[NO CHUNKS]"
    except Exception as e:
        print(f"[ERROR] Streaming Llama model inference failed: {e}")
        yield "[AI error]"


_GENRE_TONES = {
    "folk": "nostalgic",
    "rap": "assertive",
    "hip hop": "assertive",
    "house": "upbeat",
    "dance": "upbeat",
    "rock": "intense",
    "metal": "intense",
    "classical": "thoughtful",
    "jazz": "smooth",
    "blues": "melancholic",
}


def _tone_from_genres(genres):
    for g in genres:
        g = g.lower()
        for key, tone in _GENRE_TONES.items():
            if key in g:
                return tone
    return "mysterious"


_ARTIFACT_RE = re.compile(r"(?:<!--.*?-->|### .*?###|Assistant:|USER:|SYSTEM:)", re.IGNORECASE)


def _clean_output(text: str) -> str:
    """Remove common instruction artifacts from LLM output."""
    text = _ARTIFACT_RE.sub("", text)
    text = text.replace("NPC:", "").replace("\n\n", "\n")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def generate_npc_reply(user_input: str, user_data: Dict, memory: Dict) -> str:
    """Generate a short NPC reply referencing user data and genre tone."""
    used = memory.setdefault("used_refs", set())

    ref = get_random_personal_ref(user_data, used)
    if ref:
        used.add(ref)

    genres = user_data.get("spotify", {}).get("genres", [])
    tone = _tone_from_genres(genres)

    prompt = (
        "### SYSTEM ###\n"
        f"You are The Whisperer, speaking in a {tone} tone. "
        "Blend the provided personal detail naturally. "
        "Respond in one immersive sentence, max 26 words. End with <END>.\n"
        "### USER ###\n"
        f"Player said: '{user_input.strip()}'\n"
    )
    if ref:
        prompt += f"Reference: {ref}\n"
    prompt += "### ASSISTANT ###\n"

    reply = _run(prompt, max_tokens=60, temperature=0.9)
    reply = reply.replace("<END>", "")
    reply = _clean_output(reply)
    return reply or FALLBACK_NPC
