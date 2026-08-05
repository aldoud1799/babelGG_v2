import logging
import re
import unicodedata


_DISCORD_CUSTOM_RE = re.compile(r"<a?:[A-Za-z0-9_~\-]{2,32}:\d{2,}>")

# Common text emoticons used in gaming chat.
_ASCII_EMOTICON_RE = re.compile(
    r"(?:(?<=\s)|^)(?:"
    r":\)|:-\)|:D|:-D|:\(|:-\(|;\)|;-\)|xD|XD|\^\^|>_<|o7|:/|:-/|:\||:-\||:P|:-P|:O|:-O"
    r")(?:$|(?=\s|[.!?,]))",
    re.IGNORECASE,
)

# Broad kaomoji matcher using common bracketed forms.
_KAOMOJI_RE = re.compile(
    r"(?:[\(\[\{](?:[^\n\r]{1,20})[\)\]\}]|[（](?:[^\n\r]{1,20})[）])"
)

_EMOJI_RANGES = (
    (0x1F300, 0x1FAFF),
    (0x2600, 0x27BF),
    (0xFE00, 0xFE0F),
)


def _is_unicode_emoji(ch: str) -> bool:
    if not ch:
        return False
    cp = ord(ch)
    for lo, hi in _EMOJI_RANGES:
        if lo <= cp <= hi:
            return True
    return unicodedata.category(ch) == "So"


def _strip_by_regex(text: str, pattern: re.Pattern, kind: str) -> tuple[str, list[tuple[str, int, str]]]:
    removed: list[tuple[str, int, str]] = []

    def repl(match: re.Match) -> str:
        removed.append((match.group(0), match.start(), kind))
        return " "

    return pattern.sub(repl, text), removed


def _strip_unicode_emoji(text: str) -> tuple[str, list[tuple[str, int, str]]]:
    cleaned_chars: list[str] = []
    removed: list[tuple[str, int, str]] = []
    for i, ch in enumerate(text):
        if _is_unicode_emoji(ch):
            removed.append((ch, i, "unicode"))
            continue
        cleaned_chars.append(ch)
    return "".join(cleaned_chars), removed


def _squash_spaces(text: str) -> str:
    return re.sub(r"\s{2,}", " ", text).strip()


def clean(text: str) -> tuple[str, list[tuple[str, int, str]]]:
    """Strip emoji-like tokens before translation.

    Returns a tuple of (cleaned_text, emoji_list), where emoji_list contains
    tuples of (emoji, position, type).
    """
    if not text:
        return text, []

    working = text
    all_removed: list[tuple[str, int, str]] = []

    working, removed = _strip_by_regex(working, _DISCORD_CUSTOM_RE, "discord")
    all_removed.extend(removed)

    working, removed = _strip_by_regex(working, _ASCII_EMOTICON_RE, "ascii")
    all_removed.extend(removed)

    # Only strip bracketed patterns that look like kaomoji, not normal prose.
    kaomoji_hits: list[tuple[str, int, str]] = []
    for m in list(_KAOMOJI_RE.finditer(working)):
        token = m.group(0)
        if re.search(r"[^\w\s]", token):
            kaomoji_hits.append((token, m.start(), "kaomoji"))
    if kaomoji_hits:
        for token, _, _ in kaomoji_hits:
            working = working.replace(token, " ")
        all_removed.extend(kaomoji_hits)

    working, removed = _strip_unicode_emoji(working)
    all_removed.extend(removed)

    cleaned = _squash_spaces(working)

    if all_removed:
        logging.info('[EMOJI] Stripped: %s', ", ".join(f"{t}:{v}" for v, _, t in all_removed))

    unicode_only = [item for item in all_removed if item[2] == "unicode"]
    return cleaned, unicode_only


def restore(translated: str, emoji_list: list[tuple[str, int, str]]) -> str:
    """Re-attach Unicode emoji to the end of translated text."""
    if not translated:
        return translated
    if not emoji_list:
        return translated

    unicode_emoji = [emoji for emoji, _pos, kind in emoji_list if kind == "unicode"]
    if not unicode_emoji:
        return translated

    suffix = "".join(unicode_emoji)
    restored = f"{translated.rstrip()} {suffix}".rstrip()
    logging.info('[EMOJI] Restored unicode emoji at end: %s', suffix)
    return restored
