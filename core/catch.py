import os
import time
import logging
import threading


class ClipboardMonitor:
    """
    Polls clipboard every 0.5s.
    Detects foreign text, normalizes slang, calls FLASH, emits result.
    Runs in its own daemon thread. Thread-safe.
    """
    POLL_INTERVAL    = 0.5
    # 0 disables app-level clipboard text length rejection. Configurable via max_length constructor arg.
    MAX_LENGTH       = 0
    MIN_FOREIGN_RATIO = 0.10
    # Threshold above which a warning is logged (0 = disabled)
    MAX_LENGTH_WARN_THRESHOLD = 10000
    WM_CLIPBOARDUPDATE = 0x031D
    WM_CLOSE = 0x0010
    WM_QUIT = 0x0012

    def __init__(self, flash, callback, tgt_language: str = 'english', min_emit_interval_s: float = 0.0, max_length: int = 0):
        self.flash        = flash
        self.callback     = callback   # fn(result: dict) — called on translation ready
        self.tgt_language = tgt_language
        self.min_emit_interval_s = max(0.0, float(min_emit_interval_s))
        self.max_length   = int(max_length or self.MAX_LENGTH)
        self._last        = ''
        self._ignore_text = ''
        self._ignore_until = 0.0
        self._last_emit_ts = 0.0
        self._last_clipboard_error_log_ts = 0.0
        self._stop        = threading.Event()
        self._paused      = False
        self._state_lock  = threading.Lock()
        self._thread = None
        self._listener_hwnd = None
        self._listener_thread_id = None
        self._mode = 'poll'

    def _read_clipboard_text(self) -> str:
        # Primary path: pyperclip
        try:
            import pyperclip

            return pyperclip.paste() or ''
        except Exception as e:
            now = time.time()
            if (now - self._last_clipboard_error_log_ts) >= 5.0:
                logging.warning('[CATCH] pyperclip read failed: %s: %s; trying WinAPI fallback', type(e).__name__, e)
                self._last_clipboard_error_log_ts = now

        # Windows fallback path: direct CF_UNICODETEXT read.
        try:
            import ctypes

            CF_UNICODETEXT = 13
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            if not user32.OpenClipboard(None):
                raise OSError('OpenClipboard failed')
            try:
                handle = user32.GetClipboardData(CF_UNICODETEXT)
                if not handle:
                    return ''
                ptr = kernel32.GlobalLock(handle)
                if not ptr:
                    raise OSError('GlobalLock failed')
                try:
                    text = ctypes.wstring_at(ptr)
                    return text or ''
                finally:
                    kernel32.GlobalUnlock(handle)
            finally:
                user32.CloseClipboard()
        except Exception as e:
            now = time.time()
            if (now - self._last_clipboard_error_log_ts) >= 5.0:
                logging.warning('[CATCH] WinAPI clipboard fallback failed: %s: %s', type(e).__name__, e)
                self._last_clipboard_error_log_ts = now
            return ''

    def ignore_once(self, text: str, ttl_s: float = 3.0):
        """Ignore one known app-originated clipboard payload for a short time."""
        if not text:
            return
        with self._state_lock:
            self._ignore_text = text
            self._ignore_until = time.time() + max(0.5, float(ttl_s))
            # Prevent immediate reprocessing even if clipboard stays unchanged.
            self._last = text
        logging.info('[CATCH] Suppressing app-originated clipboard text once')

    def _should_ignore(self, text: str) -> bool:
        now = time.time()
        with self._state_lock:
            if self._ignore_text and now > self._ignore_until:
                self._ignore_text = ''
                self._ignore_until = 0.0
            if self._ignore_text and text == self._ignore_text and now <= self._ignore_until:
                return True
            return False

    def set_language(self, tgt_language: str):
        """Update target language live — thread-safe (simple attribute write)."""
        with self._state_lock:
            self.tgt_language = tgt_language
        logging.info(f'[CATCH] Target language updated to: {tgt_language}')

    def set_rate_limit(self, min_emit_interval_s: float):
        with self._state_lock:
            self.min_emit_interval_s = max(0.0, float(min_emit_interval_s))
        logging.info(f'[CATCH] Rate limit updated: {self.min_emit_interval_s:.1f}s between cards')

    def start(self):
        self._stop.clear()
        # Baseline current clipboard on startup to avoid replaying stale text
        # from before app launch/relaunch.
        try:
            self._last = self._read_clipboard_text()
        except Exception as e:
            logging.warning(f'[CATCH] Initial clipboard read failed: {type(e).__name__}: {e}')
            self._last = ''

        force_poll = str(os.getenv('BABELGG_CATCH_FORCE_POLL', '')).strip().lower() in {'1', 'true', 'yes', 'on'}
        if os.name == 'nt' and not force_poll:
            self._mode = 'event'
            self._thread = threading.Thread(target=self._event_loop_windows, daemon=True, name='CATCH')
            self._thread.start()
            logging.info('[CATCH] Clipboard monitor started (event-driven)')
            return

        self._mode = 'poll'
        self._thread = threading.Thread(target=self._loop, daemon=True, name='CATCH')
        self._thread.start()
        logging.info('[CATCH] Clipboard monitor started (polling)')

    def stop(self):
        self._stop.set()
        if os.name == 'nt':
            try:
                import ctypes

                user32 = ctypes.windll.user32
                if self._listener_hwnd:
                    user32.PostMessageW(int(self._listener_hwnd), self.WM_CLOSE, 0, 0)
                if self._listener_thread_id:
                    user32.PostThreadMessageW(int(self._listener_thread_id), self.WM_QUIT, 0, 0)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
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
                    text = self._read_clipboard_text()
                except Exception as e:
                    logging.debug(f'[CATCH] Clipboard read error: {e}')
                    time.sleep(self.POLL_INTERVAL)
                    continue

                if text and self._should_ignore(text):
                    time.sleep(self.POLL_INTERVAL)
                    continue

                self._process_clipboard_text(text)
            time.sleep(self.POLL_INTERVAL)

    def _event_loop_windows(self):
        try:
            import ctypes

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            HWND_MESSAGE = -3

            hwnd = user32.CreateWindowExW(
                0,
                'Static',
                'BabelGGClipboardListener',
                0,
                0,
                0,
                0,
                0,
                ctypes.c_void_p(HWND_MESSAGE),
                None,
                kernel32.GetModuleHandleW(None),
                None,
            )
            if not hwnd:
                raise OSError('CreateWindowExW failed for clipboard listener')

            if not user32.AddClipboardFormatListener(hwnd):
                user32.DestroyWindow(hwnd)
                raise OSError('AddClipboardFormatListener failed')

            self._listener_hwnd = int(hwnd)
            self._listener_thread_id = int(kernel32.GetCurrentThreadId())

            MSG = ctypes.wintypes.MSG
            msg = MSG()
            PM_REMOVE = 0x0001
            last_poll = 0.0

            while not self._stop.is_set():
                had_message = False
                while user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, PM_REMOVE):
                    had_message = True
                    if msg.message in (self.WM_CLOSE, self.WM_QUIT):
                        self._stop.set()
                        break
                    if msg.message == self.WM_CLIPBOARDUPDATE and not self._paused:
                        text = self._read_clipboard_text()
                        if text and self._should_ignore(text):
                            continue
                        self._process_clipboard_text(text)
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))

                # Safety net: some apps/environments may not reliably deliver
                # WM_CLIPBOARDUPDATE for every change, so keep a light poll.
                now = time.time()
                if not self._paused and (now - last_poll) >= self.POLL_INTERVAL:
                    last_poll = now
                    text = self._read_clipboard_text()
                    if text and not self._should_ignore(text):
                        self._process_clipboard_text(text)

                if not had_message:
                    time.sleep(0.05)

            try:
                user32.RemoveClipboardFormatListener(hwnd)
            except Exception:
                pass
            try:
                user32.DestroyWindow(hwnd)
            except Exception:
                pass
        except Exception as e:
            logging.warning('[CATCH] Event-driven listener failed (%s: %s); falling back to polling', type(e).__name__, e)
            self._mode = 'poll'
            self._loop()
        finally:
            self._listener_hwnd = None
            self._listener_thread_id = None

    def _process_clipboard_text(self, text: str):
        if not text:
            return
        if text == self._last:
            return
        if self.max_length > 0 and len(text) > self.max_length:
            if self.MAX_LENGTH_WARN_THRESHOLD > 0 and len(text) > self.MAX_LENGTH_WARN_THRESHOLD:
                logging.warning('[CATCH] Clipboard text exceeds %d chars (%d) — skipping', self.MAX_LENGTH_WARN_THRESHOLD, len(text))
            return
        if not self._is_foreign(text):
            return
        self._last = text
        logging.info(f'[CATCH] Detected {len(text)} chars: {text[:50]!r}')
        self._handle(text)

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
            with self._state_lock:
                min_emit_interval_s = self.min_emit_interval_s
                tgt_language = self.tgt_language
            if (min_emit_interval_s > 0
                    and (now - self._last_emit_ts) < min_emit_interval_s):
                logging.info('[CATCH] Rate-limited clipboard event')
                return

            from core.slang import normalize_for_translation
            from core import emoji_cleaner

            clean, was_slang = normalize_for_translation(text)
            clean_text, emoji_list = emoji_cleaner.clean(clean)
            logging.info(f'[CATCH] Translating with my_language={tgt_language}')
            result = self.flash.translate(clean_text, tgt_language)
            if not result:
                logging.warning('[CATCH] Translation returned None — all profiles failed')
                return
            translated = result.get('translation')
            unchanged = (translated or '').strip() == clean_text.strip()
            if unchanged:
                result['warning'] = 'Translation may be identical to source'
                logging.warning('[CATCH] LLM returned unchanged translation: %s', clean_text[:50])
            elif translated:
                result['translation'] = emoji_cleaner.restore(translated, emoji_list)
            result['original']   = text
            result['normalized'] = clean_text if was_slang else None
            result['emoji_cleaned'] = bool(emoji_list) or (clean_text != clean)
            self.callback(result)
            self._last_emit_ts = time.time()
        except Exception as e:
            logging.error(f'[CATCH] _handle failed: {type(e).__name__}: {e}')
