import json, logging, os, hashlib, threading
from thefuzz import fuzz


class TranslationVault:
    """
    Translation cache. Exact match via SHA256. Fuzzy match via ratio.
    LRU eviction at 500 entries. Persists to data/vault.json.
    """
    PATH            = os.path.join('data', 'vault.json')
    MAX_ENTRIES     = 500
    FUZZY_THRESHOLD = 96

    def __init__(self):
        self._cache : dict[str, str] = {}   # hash  -> translation
        self._texts : dict[str, str] = {}   # hash  -> original text
        self._tgt   : dict[str, str] = {}   # hash  -> target lang code
        self._order : list[str]      = []   # LRU order
        self._lock  = threading.Lock()
        self._load()

    def _key(self, text: str, tgt: str) -> str:
        return hashlib.sha256(f'{text.strip()}|{tgt}'.encode()).hexdigest()

    def lookup(self, text: str, tgt: str) -> str | None:
        with self._lock:
            # Exact match
            k = self._key(text, tgt)
            if k in self._cache:
                self._touch(k)
                return self._cache[k]
            # Fuzzy match — only within same target language
            for h, original in self._texts.items():
                if self._tgt.get(h) == tgt:
                    if fuzz.ratio(text, original) >= self.FUZZY_THRESHOLD:
                        return self._cache[h]
            return None

    def store(self, text: str, tgt: str, translation: str):
        with self._lock:
            k = self._key(text, tgt)
            self._cache[k] = translation
            self._texts[k] = text.strip()
            self._tgt[k]   = tgt
            if k not in self._order:
                self._order.append(k)
            while len(self._order) > self.MAX_ENTRIES:
                old = self._order.pop(0)
                for d in (self._cache, self._texts, self._tgt):
                    d.pop(old, None)
            self._save()

    def _touch(self, k: str):
        if k in self._order:
            self._order.remove(k)
            self._order.append(k)

    def _load(self):
        if not os.path.exists(self.PATH):
            logging.info('[VAULT] No cache file — starting fresh')
            return
        try:
            with open(self.PATH, 'r', encoding='utf-8') as f:
                d = json.load(f)
            self._cache = d.get('cache', {})
            self._texts = d.get('texts', {})
            self._tgt   = d.get('tgt',   {})
            self._order = d.get('order', list(self._cache.keys()))
            logging.info(f'[VAULT] Loaded {len(self._cache)} cached translations')
        except Exception as e:
            logging.error(f'[VAULT] Load failed: {e} — starting fresh')

    def _save(self):
        try:
            os.makedirs('data', exist_ok=True)
            with open(self.PATH, 'w', encoding='utf-8') as f:
                json.dump(
                    {'cache': self._cache, 'texts': self._texts,
                     'tgt':   self._tgt,   'order': self._order},
                    f, ensure_ascii=False, indent=2
                )
        except Exception as e:
            logging.error(f'[VAULT] Save failed: {e}')
