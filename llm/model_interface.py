"""
Tiny LLaMA wrapper – only NPC speech.
"""

from __future__ import annotations
import os, json
from pathlib import Path
from llama_cpp import Llama
from config import Config

MODEL_PATH = Config.MODELS_DIR / os.getenv(
    "LLAMA_MODEL_FILE", "tinyllama-1.1b-chat-v1.0.Q5_K_M.gguf"
)

# read given-name so we can halt on echoes
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
    except Exception:
        return ""

def query_npc(prompt: str) -> str:
    return _run(prompt, max_tokens=60, temperature=0.8)
