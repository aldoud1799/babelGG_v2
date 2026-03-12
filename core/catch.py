import time, logging, threading


class ClipboardMonitor:
    """
    Polls clipboard every 0.5s.
    Detects foreign text, normalizes slang, calls FLASH, emits result.
    Runs in its own daemon thread. Thread-safe.
    """
    POLL_INTERVAL    = 0.5
    MAX_LENGTH       = 600
    MIN_FOREIGN_RATIO = 0.10

    def __init__(self, flash, callback, tgt_language: str = 'english', min_emit_interval_s: float = 1.2):
        self.flash        = flash
        self.callback     = callback   # fn(result: dict) — called on translation ready
        self.tgt_language = tgt_language
        self.min_emit_interval_s = max(0.0, float(min_emit_interval_s))
        self._last        = ''
        self._ignore_text = ''
        self._ignore_until = 0.0
        self._last_emit_ts = 0.0
        self._stop        = threading.Event()
        self._paused      = False

    def ignore_once(self, text: str, ttl_s: float = 3.0):
        """Ignore one known app-originated clipboard payload for a short time."""
        if not text:
            return
        self._ignore_text = text
        self._ignore_until = time.time() + max(0.5, float(ttl_s))
        # Prevent immediate reprocessing even if clipboard stays unchanged.
        self._last = text
        logging.info('[CATCH] Suppressing app-originated clipboard text once')

    def _should_ignore(self, text: str) -> bool:
        now = time.time()
        if self._ignore_text and now > self._ignore_until:
            self._ignore_text = ''
            self._ignore_until = 0.0
        if self._ignore_text and text == self._ignore_text and now <= self._ignore_until:
            return True
        return False

    def set_language(self, tgt_language: str):
        """Update target language live — thread-safe (simple attribute write)."""
        self.tgt_language = tgt_language
        logging.info(f'[CATCH] Target language updated to: {tgt_language}')

    def set_rate_limit(self, min_emit_interval_s: float):
        self.min_emit_interval_s = max(0.0, float(min_emit_interval_s))
        logging.info(f'[CATCH] Rate limit updated: {self.min_emit_interval_s:.1f}s between cards')

    def start(self):
        self._stop.clear()
        # Baseline current clipboard on startup to avoid replaying stale text
        # from before app launch/relaunch.
        try:
            import pyperclip
            self._last = pyperclip.paste() or ''
        except Exception:
            self._last = ''
        t = threading.Thread(target=self._loop, daemon=True, name='CATCH')
        t.start()
        logging.info('[CATCH] Clipboard monitor started')

    def stop(self):
        self._stop.set()
        logging.info('[CATCH] Stopped')

    def pause(self):
        self._paused = True
        logging.info('[CATCH] Paused')

    def resume(self):
        self._paused = False
        logging.info('[CATCH] Resumed')

    def _loop(self):
        while not self._stop.is_set():
            if not self._paused:
                try:
                    import pyperclip
                    text = pyperclip.paste()
                except Exception as e:
                    logging.debug(f'[CATCH] Clipboard read error: {e}')
                    time.sleep(self.POLL_INTERVAL)
                    continue

                if text and self._should_ignore(text):
                    time.sleep(self.POLL_INTERVAL)
                    continue

                if (text
                        and text != self._last
                        and len(text) <= self.MAX_LENGTH
                        and self._is_foreign(text)):
                    self._last = text
                    logging.info(f'[CATCH] Detected {len(text)} chars: {text[:50]!r}')
                    self._handle(text)
            time.sleep(self.POLL_INTERVAL)

    def _is_foreign(self, text: str) -> bool:
        # Reject URLs
        s = text.strip()
        if s.startswith(('http://', 'https://', 'www.')):
            return False
        # Reject file paths
        if s.startswith(('C:\\', 'D:\\', 'E:\\', '/', '\\\\')):
            return False
        # Count foreign characters
        foreign = sum(1 for ch in text if (
            0x3040 <= ord(ch) <= 0x9FFF    # Japanese + CJK
            or 0xAC00 <= ord(ch) <= 0xD7A3  # Korean
            or 0x0600 <= ord(ch) <= 0x06FF  # Arabic
            or 0x0E00 <= ord(ch) <= 0x0E7F  # Thai
            or 0x0400 <= ord(ch) <= 0x04FF  # Cyrillic
        ))
        return foreign / max(len(text), 1) >= self.MIN_FOREIGN_RATIO

    def _handle(self, text: str):
        try:
            now = time.time()
            if (self.min_emit_interval_s > 0
                    and (now - self._last_emit_ts) < self.min_emit_interval_s):
                logging.info('[CATCH] Rate-limited clipboard event')
                return

            from core.slang import normalize_for_translation
            clean, was_slang = normalize_for_translation(text)
            result = self.flash.translate(clean, self.tgt_language)
            if result:
                result['original']   = text         # show original on card
                result['normalized'] = clean if was_slang else None
                self.callback(result)
                self._last_emit_ts = time.time()
        except Exception as e:
            logging.error(f'[CATCH] _handle failed: {type(e).__name__}: {e}')
