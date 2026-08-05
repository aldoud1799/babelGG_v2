from enum import Enum
import json
from pathlib import Path
import re

from .energy import EnergyProfile


class Register(Enum):
    CASUAL = "casual"
    NEUTRAL = "neutral"
    FORMAL = "formal"


CASUAL_MARKERS = [
    "lol", "lmao", "wtf", "omg", "bruh", "bro", "ngl",
    "tbh", "imo", "idk", "nah", "yeah", "yep", "nope",
    "dude", "man", "babe", "lowkey", "highkey", "fr",
    "deadass", "slay", "vibe", "lit", "sus", "cap", "no cap",
    "based", "cringe", "bussin", "goated", "mid", "ratio",
]

FORMAL_MARKERS = [
    "therefore", "furthermore", "however", "consequently",
    "i believe", "in my opinion", "it appears", "regarding",
    "nevertheless", "accordingly", "subsequently",
]


_DATA_DIR = Path(__file__).resolve().parent / "data"
with (_DATA_DIR / "casual_swaps.json").open("r", encoding="utf-8") as f:
    _swaps = json.load(f)
CASUAL_SWAPS = dict(sorted(_swaps.items(), key=lambda kv: len(kv[0]), reverse=True))


def detect_register(source: str, profile: EnergyProfile) -> Register:
    source_lower = (source or "").lower()
    casual_score = 0
    formal_score = 0

    for marker in CASUAL_MARKERS:
        if marker in source_lower:
            casual_score += 2

    if profile.exclamation_count >= 2:
        casual_score += 2
    if profile.caps_ratio > 0.5:
        casual_score += 2
    if profile.emoji_count > 0:
        casual_score += 1
    if profile.has_laughter:
        casual_score += 3
    if profile.is_very_short:
        casual_score += 1

    for marker in FORMAL_MARKERS:
        if marker in source_lower:
            formal_score += 2

    if (source or "").count(",") >= 2:
        formal_score += 1
    if len((source or "").split()) > 15:
        formal_score += 1

    if casual_score >= 3:
        return Register.CASUAL
    if formal_score >= 3:
        return Register.FORMAL
    return Register.NEUTRAL


def apply_register_swaps(text: str, register: Register) -> str:
    if register != Register.CASUAL:
        return text

    result = text
    for formal, casual in CASUAL_SWAPS.items():
        pattern = re.compile(re.escape(formal), re.IGNORECASE)
        result = pattern.sub(casual, result)
    return result
