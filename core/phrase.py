"""
Gaming Phrase Database — instant lookup before NLLB.

Lookup order:
  1. Exact match
  2. Stutter-collapsed fuzzy match (kkkkk → kk, 草草草 → 草草)
  3. Case-insensitive match (for ASCII entries like "666", "gg")
"""

import json, re, logging
from core.paths import data_path


_DB: dict | None = None


def _load() -> dict:
    global _DB
    if _DB is None:
        try:
            path = data_path('phrases.json')
            with open(path, 'r', encoding='utf-8') as f:
                _DB = json.load(f)
            count = sum(len(v) for v in _DB.values())
            logging.info(f'[PHRASE] Loaded {count} expressions across {len(_DB)} languages')
        except Exception as e:
            logging.warning(f'[PHRASE] Could not load phrases.json: {e}')
            _DB = {}
    return _DB


def _stutter_collapse(text: str) -> str:
    """Collapse 3+ consecutive identical chars to 2: kkkkk→kk, 草草草→草草"""
    return re.sub(r'(.)\1{2,}', r'\1\1', text)


def _normalize_key(text: str) -> str:
    # Trim common trailing punctuation so "加油！！！" can match "加油".
    return text.strip().rstrip('!?.,;:~！？，。；：…')


def _lookup_in_phrases(phrases: dict, key: str, tgt: str) -> str | None:
    def _get(entry) -> str | None:
        if not entry:
            return None
        return entry.get(tgt) or entry.get('en') or None

    # 1. Exact match
    result = _get(phrases.get(key))
    if result:
        return result

    # 2. Stutter-collapsed fuzzy match
    collapsed = _stutter_collapse(key)
    if collapsed != key:
        result = _get(phrases.get(collapsed))
        if result:
            return result

    # 3. Case-insensitive match (useful for "666", "Gg", "FF" etc.)
    key_lower = key.lower()
    for phrase_key, entry in phrases.items():
        if phrase_key.lower() == key_lower:
            result = _get(entry)
            if result:
                return result

    return None


def lookup(text: str, src_lang_code: str, tgt: str = 'en') -> str | None:
    """
    Look up a foreign text snippet in the phrase database.

    src_lang_code : FLORES-200 code, e.g. 'jpn_Jpan', 'kor_Hang', 'zho_Hans'
    tgt           : target language key in the entry dict, default 'en'

    Returns the hand-written translation string, or None if no match.
    """
    db = _load()
    if not db:
        return None

    # Map FLORES code → 3-letter phrase-DB key  (jpn_Jpan → jpn)
    lang_key = src_lang_code[:3].lower()
    phrases  = db.get(lang_key)
    if not phrases:
        return None

    key = _normalize_key(text)

    result = _lookup_in_phrases(phrases, key, tgt)
    if result:
        logging.info(f'[PHRASE] {lang_key}: {key!r} → {result!r}')
        return result

    # Cross-language fallback: short slang often appears across neighboring scripts.
    for other_lang, other_phrases in db.items():
        if other_lang == lang_key:
            continue
        result = _lookup_in_phrases(other_phrases, key, tgt)
        if result:
            logging.info(f'[PHRASE] {lang_key}->{other_lang}: {key!r} → {result!r}')
            return result

    return None
