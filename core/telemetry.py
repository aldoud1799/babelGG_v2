import hashlib
import json
import logging
import os
import threading
import uuid
from collections import defaultdict
from datetime import datetime

from core.paths import data_path

_FLUSH_INTERVAL_SEC = 30.0


class Telemetry:
    def __init__(self, storage_path: str | None = None, max_events: int = 500):
        self.storage_path = storage_path or data_path('telemetry.json')
        self.max_events = int(max_events)
        self.session_id = hashlib.sha256(str(uuid.getnode()).encode('utf-8')).hexdigest()[:16]
        self._events: list[dict] = []
        self._dirty = False
        self._flush_timer: threading.Timer | None = None
        self._load()

    def _load(self):
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                self._events = data
        except FileNotFoundError:
            self._events = []
        except Exception as e:
            logging.warning(f'[TELEMETRY] Load failed: {type(e).__name__}: {e}')
            self._events = []

    def log_translation(
        self,
        src_lang,
        tgt_lang,
        text_length,
        translation_ms,
        cache_hit,
        phrase_db_hit,
        slang_normalized,
        emoji_cleaned,
        naturalizer_applied,
    ):
        event = {
            'event': 'translation',
            'ts': datetime.utcnow().isoformat(),
            'src_lang': str(src_lang or ''),
            'tgt_lang': str(tgt_lang or ''),
            'text_length': int(text_length or 0),
            'translation_ms': int(translation_ms or 0),
            'cache_hit': bool(cache_hit),
            'phrase_db_hit': bool(phrase_db_hit),
            'slang_normalized': bool(slang_normalized),
            'emoji_cleaned': bool(emoji_cleaned),
            'naturalizer_applied': bool(naturalizer_applied),
            'session_id': self.session_id,
        }
        self._append(event)

    def log_card_dismissed(self, src_lang: str, card_shown_ms: int, dismissed_by: str):
        event = {
            'event': 'card_dismissed',
            'ts': datetime.utcnow().isoformat(),
            'src_lang': str(src_lang or ''),
            'card_shown_ms': int(card_shown_ms or 0),
            'dismissed_by': str(dismissed_by or 'unknown'),
            'session_id': self.session_id,
        }
        self._append(event)

    def log_reply_opened(self, src_lang: str):
        event = {
            'event': 'reply_opened',
            'ts': datetime.utcnow().isoformat(),
            'src_lang': str(src_lang or ''),
            'session_id': self.session_id,
        }
        self._append(event)

    def get_quality_report(self) -> dict:
        per_lang = defaultdict(lambda: {'dismiss_total': 0, 'dismiss_count': 0, 'fast_dismiss': 0, 'reply_opened': 0})

        for ev in self._events:
            lang = ev.get('src_lang')
            if not lang:
                continue
            if ev.get('event') == 'card_dismissed':
                ms = int(ev.get('card_shown_ms') or 0)
                per_lang[lang]['dismiss_total'] += ms
                per_lang[lang]['dismiss_count'] += 1
                if ms < 800:
                    per_lang[lang]['fast_dismiss'] += 1
            elif ev.get('event') == 'reply_opened':
                per_lang[lang]['reply_opened'] += 1

        report = {}
        for lang, stats in per_lang.items():
            dismiss_count = max(1, stats['dismiss_count'])
            report[lang] = {
                'avg_read_ms': round(stats['dismiss_total'] / dismiss_count, 1),
                'fast_dismiss_rate': round(stats['fast_dismiss'] / dismiss_count, 3),
                'reply_opened': int(stats['reply_opened']),
            }
        return report

    def get_phrase_gaps(self) -> list[str]:
        by_lang = defaultdict(lambda: {'translations': 0, 'phrase_miss': 0, 'fast_dismiss': 0})

        for ev in self._events:
            if ev.get('event') == 'translation':
                lang = ev.get('src_lang')
                if not lang:
                    continue
                by_lang[lang]['translations'] += 1
                if not bool(ev.get('phrase_db_hit')):
                    by_lang[lang]['phrase_miss'] += 1
            elif ev.get('event') == 'card_dismissed':
                lang = ev.get('src_lang')
                if not lang:
                    continue
                if int(ev.get('card_shown_ms') or 0) < 800:
                    by_lang[lang]['fast_dismiss'] += 1

        gaps = []
        for lang, stats in by_lang.items():
            if stats['translations'] < 3:
                continue
            miss_rate = stats['phrase_miss'] / max(1, stats['translations'])
            fast_rate = stats['fast_dismiss'] / max(1, stats['translations'])
            if miss_rate >= 0.6 and fast_rate >= 0.3:
                gaps.append(lang)
        return sorted(gaps)

    def clear_data(self):
        timer = self._flush_timer
        self._flush_timer = None
        if timer:
            timer.cancel()
        self._events = []
        self._dirty = False
        try:
            if os.path.exists(self.storage_path):
                os.remove(self.storage_path)
                logging.info('[TELEMETRY] Cleared local telemetry file')
        except Exception as e:
            logging.warning(f'[TELEMETRY] clear_data failed: {type(e).__name__}: {e}')

    def flush(self):
        """Force an immediate flush of any pending telemetry to disk."""
        timer = self._flush_timer
        self._flush_timer = None
        if timer:
            timer.cancel()
        if self._dirty:
            self._write()

    def _append(self, event: dict):
        self._events.append(event)
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]
        self._dirty = True
        self._schedule_flush()

    def _schedule_flush(self):
        if self._flush_timer is not None:
            return
        self._flush_timer = threading.Timer(_FLUSH_INTERVAL_SEC, self._flush)
        self._flush_timer.daemon = True
        self._flush_timer.start()

    def _flush(self):
        self._flush_timer = None
        if self._dirty:
            self._write()

    def _write(self):
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self._events, f, indent=2, ensure_ascii=False)
            self._dirty = False
        except Exception as e:
            logging.warning(f'[TELEMETRY] Write failed: {type(e).__name__}: {e}')
