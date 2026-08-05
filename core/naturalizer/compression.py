import json
import re
from pathlib import Path

from .energy import EnergyProfile
from .punctuation import cleanup_spacing


_DATA_DIR = Path(__file__).resolve().parent / "data"
with (_DATA_DIR / "filler_words.json").open("r", encoding="utf-8") as f:
    FILLERS = sorted(json.load(f), key=len, reverse=True)


def compress(text: str, profile: EnergyProfile) -> str:
    source_count = max(profile.source_word_count, 1)
    ratio = profile.translated_word_count / source_count

    if ratio <= 1.2:
        return text

    result = text
    target_ratio = 1.15 if ratio <= 1.4 else 1.05

    for filler in FILLERS:
        if len(result.split()) / source_count <= target_ratio:
            break
        pattern = re.compile(r"\b" + re.escape(filler) + r"\b", re.IGNORECASE)
        result = pattern.sub("", result)

    result = cleanup_spacing(result)
    if not result:
        return text
    return result
