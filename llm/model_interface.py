# File: llm/model_interface.py
"""
Tiny wrapper round llama-cpp with two helpers:
    • query_room() – one spooky sentence   (≤ 50 tokens)
    • query_npc()  – one cryptic NPC line (≤ 30 tokens)

Both return plain strings and fail-soft (empty string on error).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final

from llama_cpp import Llama

# ---------------------------------------------------------------------
# 1.  Model location – defaults to TinyLlama chat Q5_K_M
# ---------------------------------------------------------------------
MODEL_PATH: Final[Path] = (
    Path(__file__).parent.parent / "models" /
    os.getenv("LLAMA_MODEL_FILE", "tinyllama-1.1b-chat-v1.0.Q5_K_M.gguf")
)

# ---------------------------------------------------------------------
# 2.  (Optional) read player's first name so we can stop on “Gabriel:”
# ---------------------------------------------------------------------
PROFILE = Path(__file__).parent.parent / "user_profile.json"
try:
    GIVEN_NAME = json.loads(PROFILE.read_text(encoding="utf-8")).get("full_name", "").split()[0]
except Exception:
    GIVEN_NAME = ""

# Tokens that *immediately* end generation if the model starts echoing
STOP_TOKENS = ["\n", "Assistant:", f"{GIVEN_NAME}:", "<END>"]

# ---------------------------------------------------------------------
# 3.  Single global Llama instance
# ---------------------------------------------------------------------
_llm = Llama(
    model_path=str(MODEL_PATH),
    n_ctx=1024,
    n_threads=max(1, os.cpu_count() - 1),
    verbose=False,
)

# ---------------------------------------------------------------------
# 4.  Thin helper
# ---------------------------------------------------------------------
def _call_llm(prompt: str, *, max_tokens: int, temperature: float) -> str:
    """
    Internal: run the model and always return a *string* (possibly empty).
    Any exception becomes an empty string so the game UI never crashes.
    """
    try:
        res = _llm(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=STOP_TOKENS,
        )
        # llama-cpp Python binding returns a dict → normalise to str
        return res["choices"][0]["text"].strip()
    except Exception:
        return ""

# ---------------------------------------------------------------------
# 5.  Public helpers
# ---------------------------------------------------------------------
def query_room(prompt: str) -> str:
    """Return one ominous room sentence (~½ tweet)."""
    return _call_llm(prompt, max_tokens=50, temperature=0.8)


def query_npc(prompt: str) -> str:
    """Return one unsettling NPC line."""
    return _call_llm(prompt, max_tokens=30, temperature=0.9)
