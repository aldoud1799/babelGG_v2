import re

import emoji

from .compression import compress
from .energy import analyze_energy, restore_energy
from .passthrough import extract_untranslatables, is_placeholders_only, restore_untranslatables
from .register import apply_register_swaps, detect_register


_SINGLE_NUMBER_RE = re.compile(r"\s*\d+(?:\.\d+)?[kKmM]?\s*")


def _is_pure_emoji(text: str) -> bool:
    s = (text or "").strip()
    if not s:
        return False
    emoji_hits = emoji.emoji_list(s)
    if not emoji_hits:
        return False

    cursor = 0
    for hit in emoji_hits:
        start = hit["match_start"]
        end = hit["match_end"]
        if s[cursor:start].strip():
            return False
        cursor = end
    return not s[cursor:].strip()


def naturalize(source_text: str, translated_text: str) -> str:
    source_text = source_text or ""
    translated_text = translated_text or ""

    if translated_text == "":
        return ""
    if _is_pure_emoji(source_text):
        return translated_text
    protected_source, _ = extract_untranslatables(source_text)
    if is_placeholders_only(protected_source):
        return source_text
    if translated_text.strip() == source_text.strip() and source_text.strip():
        return source_text
    if _SINGLE_NUMBER_RE.fullmatch(source_text or ""):
        return source_text.strip()

    protected_translation, protected_map = extract_untranslatables(translated_text)
    if is_placeholders_only(protected_translation):
        return source_text

    profile = analyze_energy(source_text, protected_translation)
    register = detect_register(source_text, profile)
    swapped = apply_register_swaps(protected_translation, register)
    compressed = compress(swapped, profile)
    energized = restore_energy(compressed, profile)
    result = restore_untranslatables(energized, protected_map)

    return result.strip()
