import json, logging, os, hashlib, shutil, threading
from thefuzz import fuzz
from core.paths import data_path


class TranslationVault:
    """
    Translation cache. Exact match via SHA256. Fuzzy match via ratio.
    LRU eviction at 500 entries. Persists to data/vault.json.

    Writes are atomic: write to vault.json.tmp then os.replace() to vault.json.
    A vault.json.bak backup is kept before each write.
    On corrupted main file, attempts to restore from backup.
    """
    MAX_ENTRIES     = 500
    FUZZY_THRESHOLD = 96
    MIN_FUZZY_CHARS = 18
    MAX_FUZZY_LEN_DRIFT = 0.25
    _VERSION = 1  # schema version for future migrations

    @property
    def _path(self) -> str:
        return data_path('vault.json')

    @property
    def _tmp_path(self) -> str:
        return data_path('vault.json.tmp')

    @property
    def _bak_path(self) -> str:
        return data_path('vault.json.bak')

    def __init__(self):
        self._cache : dict[str, str] = {}   # hash  -> translation
        self._texts : dict[str, str] = {}   # hash  -> original text
        self._tgt   : dict[str, str] = {}   # hash  -> target lang code
        self._order : list[str]      = []   # LRU order
        self._lock  = threading.Lock()
        self._dirty = False
        self._save_timer: threading.Timer | None = None
        self._load()

    def _key(self, text: str, tgt: str) -> str:
        return hashlib.sha256(f'{text.strip()}|{tgt}'.encode()).hexdigest()

    def lookup_entry(self, text: str, tgt: str) -> dict | None:
        needle = (text or '').strip()
        if not needle:
            return None
        with self._lock:
            # Exact match
            k = self._key(needle, tgt)
            if k in self._cache:
                self._touch(k)
                return {
                    'key': k,
                    'translation': self._cache[k],
                    'match_type': 'exact',
                    'matched_text': self._texts.get(k, needle),
                    'score': 100,
                }

            # Fuzzy match — only within same target language and only for longer strings.
            if len(needle) < self.MIN_FUZZY_CHARS:
                return None

            best_key = None
            best_score = -1
            best_original = ''
            min_len = int(len(needle) * (1.0 - self.MAX_FUZZY_LEN_DRIFT))
            max_len = int(len(needle) * (1.0 + self.MAX_FUZZY_LEN_DRIFT))

            for h, original in self._texts.items():
                if self._tgt.get(h) != tgt:
                    continue
                orig = (original or '').strip()
                if not orig:
                    continue
                if len(orig) < min_len or len(orig) > max_len:
                    continue
                score = fuzz.ratio(needle, orig)
                if score >= self.FUZZY_THRESHOLD and score > best_score:
                    best_key = h
                    best_score = score
                    best_original = orig

            if best_key:
                self._touch(best_key)
                return {
                    'key': best_key,
                    'translation': self._cache.get(best_key, ''),
                    'match_type': 'fuzzy',
                    'matched_text': best_original,
                    'score': best_score,
                }
            return None

    def lookup(self, text: str, tgt: str) -> str | None:
        hit = self.lookup_entry(text, tgt)
        if not hit:
            return None
        return hit.get('translation')

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
            self._dirty = True
        self._schedule_save()

    def invalidate(self, text: str, tgt: str) -> bool:
        with self._lock:
            k = self._key(text, tgt)
            removed = False
            for d in (self._cache, self._texts, self._tgt):
                if k in d:
                    d.pop(k, None)
                    removed = True
            if k in self._order:
                self._order.remove(k)
                removed = True
            if removed:
                self._dirty = True
        if removed:
            self._schedule_save()
        return removed

    def invalidate_key(self, key: str) -> bool:
        if not key:
            return False
        with self._lock:
            removed = False
            for d in (self._cache, self._texts, self._tgt):
                if key in d:
                    d.pop(key, None)
                    removed = True
            if key in self._order:
                self._order.remove(key)
                removed = True
            if removed:
                self._dirty = True
        if removed:
            self._schedule_save()
        return removed

    def _schedule_save(self):
        with self._lock:
            if self._save_timer:
                self._save_timer.cancel()
            self._save_timer = threading.Timer(2.0, self._save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def _touch(self, k: str):
        if k in self._order:
            self._order.remove(k)
            self._order.append(k)

    def _load(self):
        path = self._path
        if not os.path.exists(path):
            logging.info('[VAULT] No cache file — starting fresh')
            return

        # Try main file first, then backup
        for try_path in (path, self._bak_path):
            if try_path and os.path.exists(try_path):
                try:
                    with open(try_path, 'r', encoding='utf-8') as f:
                        d = json.load(f)
                    self._cache = d.get('cache', {})
                    self._texts = d.get('texts', {})
                    self._tgt   = d.get('tgt',   {})
                    self._order = d.get('order', list(self._cache.keys()))
                    src = 'backup' if try_path == self._bak_path else 'main'
                    logging.info(f'[VAULT] Loaded {len(self._cache)} cached translations (from {src})')
                    return
                except Exception as e:
                    logging.warning(f'[VAULT] Load of {try_path} failed: {e} — trying next')

        logging.info('[VAULT] No usable cache file — starting fresh')

    def _save(self):
        try:
            with self._lock:
                payload = {
                    'version': self._VERSION,
                    'cache': dict(self._cache),
                    'texts': dict(self._texts),
                    'tgt': dict(self._tgt),
                    'order': list(self._order),
                }
            data_dir = data_path()
            os.makedirs(data_dir, exist_ok=True)

            # Backup current file before overwriting
            bak = self._bak_path
            path = self._path
            if os.path.exists(path):
                try:
                    shutil.copy2(path, bak)
                except Exception as e:
                    logging.warning('[VAULT] Backup failed: %s', e)
                    bak = None  # skip backup if it fails

            # Atomic write: tmp → rename
            tmp = self._tmp_path
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)  # atomic on Windows

            with self._lock:
                self._dirty = False
                self._save_timer = None
        except Exception as e:
            logging.error(f'[VAULT] Save failed: {e}')

    def recent(self, limit: int = 50) -> list[dict]:
        """Return the most recent `limit` translation entries, newest first."""
        with self._lock:
            order = list(self._order)
            entries = []
            for k in reversed(order):
                if len(entries) >= limit:
                    break
                entries.append({
                    'key': k,
                    'original': self._texts.get(k, ''),
                    'translation': self._cache.get(k, ''),
                    'target': self._tgt.get(k, ''),
                })
            return entries

    def invalidate_all(self):
        with self._lock:
            self._cache.clear()
            self._texts.clear()
            self._tgt.clear()
            self._order.clear()
            self._dirty = True
        self._schedule_save()

    def flush(self):
        timer = None
        with self._lock:
            timer = self._save_timer
            self._save_timer = None
            dirty = self._dirty
        if timer:
            timer.cancel()
        if dirty:
            self._save()
            with self._lock:
                self._dirty = False
