import json
from pathlib import Path
import re

import emoji


GAME_TERMS = [
    "respawn", "ult", "gg", "ff", "mid", "top", "bot",
    "adc", "jungle", "gank", "carry", "feed", "noob",
    "op", "nerf", "buff", "cd", "cooldown", "tower",
    "baron", "dragon", "minion", "ping", "afk", "ezz",
]

_DATA_DIR = Path(__file__).resolve().parent / "data"
with (_DATA_DIR / "untranslatable_patterns.json").open("r", encoding="utf-8") as f:
    pattern_defs = json.load(f)

PATTERNS = []
for item in pattern_defs:
    flags = re.IGNORECASE if item.get("label") == "GAMETERM" else 0
    PATTERNS.append((item.get("label", "PATTERN"), re.compile(item["pattern"], flags)))

PATTERNS.append(("GAMETERM", re.compile(r"\b(" + "|".join(GAME_TERMS) + r")\b", re.IGNORECASE)))

_PLACEHOLDER_RE = re.compile(r"__ph(\d+)__")


def _extract_emoji(text: str, protected: dict[int, str], counter: int) -> tuple[str, int]:
    if not text:
        return "", counter

    chunks = []
    cursor = 0
    for hit in emoji.emoji_list(text):
        start = hit["match_start"]
        end = hit["match_end"]
        chunks.append(text[cursor:start])
        ph = f"__ph{counter}__"
        protected[counter] = text[start:end]
        chunks.append(ph)
        counter += 1
        cursor = end
    chunks.append(text[cursor:])
    return "".join(chunks), counter


def extract_untranslatables(text: str) -> tuple[str, dict[int, str]]:
    protected: dict[int, str] = {}
    counter = 0

    result, counter = _extract_emoji(text, protected, counter)

    for _, pattern in PATTERNS:
        def replacer(m: re.Match) -> str:
            nonlocal counter
            ph = f"__ph{counter}__"
            protected[counter] = m.group(0)
            counter += 1
            return ph

        result = pattern.sub(replacer, result)

    return result, protected


def restore_untranslatables(text: str, protected: dict[int, str]) -> str:
    def repl(m: re.Match) -> str:
        idx = int(m.group(1))
        return protected.get(idx, m.group(0))

    return _PLACEHOLDER_RE.sub(repl, text or "")


def is_placeholders_only(text: str) -> bool:
    stripped = _PLACEHOLDER_RE.sub("", text or "")
    stripped = re.sub(r"\s+", "", stripped)
    stripped = re.sub(r"[\.,!?;:'\"`~\-_/\\()\[\]{}]+", "", stripped)
    return stripped == ""
