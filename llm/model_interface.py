"""
Phi-3 Mini LLaMA wrapper – only NPC speech.
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from llama_cpp import Llama
from config import Config

# Always use the correct model filename
MODEL_NAME = "Phi-3-mini-4k-instruct-q4.gguf"
MODEL_PATH = Config.MODELS_DIR / MODEL_NAME

print(f"\n[INFO] Loading model from: {MODEL_PATH}")
print(f"[INFO] Model file exists: {MODEL_PATH.exists()}")

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"\n[ERROR] Model not found: {MODEL_PATH}\n"
        f"Please run 'download.bat' in the 'models' folder before starting the game.\n"
    )

# Read given name for prompt stopping
try:
    GIVEN = json.loads(Config.PROFILE_PATH.read_text("utf-8")).get("full_name", "").split()[0]
except Exception:
    GIVEN = ""

STOP = ["\n", "Assistant:", f"{GIVEN}:", "<END>"]

_llm = Llama(
    model_path=str(MODEL_PATH),
    n_ctx=1024,
    n_threads=max(1, os.cpu_count() - 1),
    verbose=False,
)

def _run(prompt: str, max_tokens: int, temperature: float) -> str:
    try:
        res = _llm(prompt=prompt, max_tokens=max_tokens, temperature=temperature, stop=STOP)
        return res["choices"][0]["text"].strip()
    except Exception as e:
        print(f"[ERROR] Llama model inference failed: {e}")
        return ""

def query_npc(prompt: str) -> str:
    return _run(prompt, max_tokens=60, temperature=0.8)
