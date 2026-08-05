from dataclasses import dataclass
import re

import emoji


LAUGHTER_PATTERNS = re.compile(
    r"\b(lol|lmao|lmfao|haha|hehe|hihi|keke|www|笑|kkk|jaja)\b",
    re.IGNORECASE,
)
LAUGHTER_EMOJI = {"😂", "🤣", "😹", "💀", "☠", "☠️"}


@dataclass
class EnergyProfile:
    exclamation_count: int
    question_count: int
    caps_ratio: float
    emoji_count: int
    has_ellipsis: bool
    has_laughter: bool
    source_word_count: int
    translated_word_count: int
    is_very_short: bool
    is_all_caps: bool


def analyze_energy(source: str, translated: str) -> EnergyProfile:
    alpha_chars = [c for c in source if c.isalpha()]
    caps_count = sum(1 for c in alpha_chars if c.isupper())
    caps_ratio = caps_count / len(alpha_chars) if alpha_chars else 0.0

    emoji_count = len(emoji.emoji_list(source or ""))
    has_laughter = bool(LAUGHTER_PATTERNS.search(source or "")) or any(e in (source or "") for e in LAUGHTER_EMOJI)

    source_words = (source or "").split()
    translated_words = (translated or "").split()

    return EnergyProfile(
        exclamation_count=(source or "").count("!"),
        question_count=(source or "").count("?"),
        caps_ratio=caps_ratio,
        emoji_count=emoji_count,
        has_ellipsis=(("..." in (source or "")) or ("…" in (source or ""))),
        has_laughter=has_laughter,
        source_word_count=len(source_words),
        translated_word_count=len(translated_words),
        is_very_short=len(source_words) <= 3,
        is_all_caps=(caps_ratio > 0.85 and len(alpha_chars) > 2),
    )


def restore_energy(text: str, profile: EnergyProfile) -> str:
    result = (text or "").rstrip()

    if profile.exclamation_count >= 1 and result.endswith("."):
        result = result[:-1] + "!"
    if profile.exclamation_count >= 2 and not result.endswith("!"):
        result = result + "!"

    if profile.question_count >= 1 and "?" not in result:
        result = result.rstrip(".!") + "?"
    if profile.question_count >= 2 and not result.endswith("??"):
        if result.endswith("?"):
            result = result + "?"

    if profile.is_all_caps:
        words = result.split()
        if 0 < len(words) <= 8:
            result = result.upper()

    if profile.has_laughter:
        result_lower = result.lower()
        has_laugh_already = any(w in result_lower for w in ["lol", "haha", "lmao", "😂"])
        if not has_laugh_already:
            result = result.rstrip(".!") + " lol"

    if profile.has_ellipsis and not result.endswith("..."):
        result = result.rstrip(".") + "..."

    if profile.is_very_short and len(result.split()) > 5:
        clause_end = re.search(r"[,;]", result)
        if clause_end:
            result = result[: clause_end.start()].strip()

    return result
