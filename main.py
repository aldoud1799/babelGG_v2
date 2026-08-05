import sys
import io


def _wrap_text_stream(stream):
    if stream is None:
        return None
    try:
        buffer = getattr(stream, 'buffer', None)
        if buffer is None:
            return stream
        return io.TextIOWrapper(buffer, encoding='utf-8')
    except Exception:
        return stream


_wrapped_stdout = _wrap_text_stream(getattr(sys, 'stdout', None))
if _wrapped_stdout is not None:
    sys.stdout = _wrapped_stdout

_wrapped_stderr = _wrap_text_stream(getattr(sys, 'stderr', None))
if _wrapped_stderr is not None:
    sys.stderr = _wrapped_stderr

import logging, json, os, threading, msvcrt, tempfile, webbrowser, time, shutil
import ctypes

# Resolves correctly whether running from source or as a frozen exe.
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    USER_DATA_ROOT = os.path.join(os.environ.get('LOCALAPPDATA', tempfile.gettempdir()), 'BabelGG')
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    USER_DATA_ROOT = BASE_DIR


def app_path(*parts) -> str:
    """Build an absolute path anchored to the app base directory."""
    return os.path.join(BASE_DIR, *parts)


def user_config_path() -> str:
    if getattr(sys, 'frozen', False):
        os.makedirs(USER_DATA_ROOT, exist_ok=True)
        return os.path.join(USER_DATA_ROOT, 'config.json')
    return app_path('config.json')


def data_path(*parts) -> str:
    if getattr(sys, 'frozen', False):
        path = os.path.join(USER_DATA_ROOT, 'data', *parts)
        parent = os.path.dirname(path) if parts else path
        os.makedirs(parent, exist_ok=True)
        return path
    return app_path('data', *parts)


def asset_path(*parts) -> str:
    return _resource_path('assets', *parts)


def _resource_path(*parts) -> str:
    primary = app_path(*parts)
    if os.path.exists(primary):
        return primary
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', '')
        if meipass:
            fallback = os.path.join(meipass, *parts)
            if os.path.exists(fallback):
                return fallback
    return primary

# Insert runtime DLL directories for PyInstaller frozen app
import os as _os, sys as _sys
if hasattr(_sys, '_MEIPASS'):
    _base = _os.path.dirname(_sys.executable)
    for _sub in ['_internal', '_internal/nvidia/cublas/bin', 'data/cuda/bin']:
        _d = _os.path.join(_base, _sub)
        if _os.path.isdir(_d):
            try:
                _os.add_dll_directory(_d)
            except Exception:
                pass

# Keep Qt startup clean; translation backend now initializes lazily in FlashEngine.

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QSystemTrayIcon
from PyQt6.QtCore    import QObject, pyqtSignal, QMetaObject, Qt, pyqtSlot, QTimer, QRect
from PyQt6.QtGui     import QIcon, QGuiApplication

# keyboard â€” optional; hotkey registration silently degrades without admin rights
try:
    import keyboard as _keyboard
    _KEYBOARD_AVAILABLE = True
except Exception as _kb_err:
    _keyboard = None
    _KEYBOARD_AVAILABLE = False

# â”€â”€ Logging â€” must be first â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_EARLY_STARTUP_WARNING = ''
_log_handlers = []
if getattr(sys, 'stdout', None) is not None:
    _log_handlers.append(logging.StreamHandler(sys.stdout))
elif getattr(sys, 'stderr', None) is not None:
    _log_handlers.append(logging.StreamHandler(sys.stderr))
try:
    os.makedirs(data_path(), exist_ok=True)
    _log_handlers.append(logging.FileHandler(data_path('babelgg.log'), encoding='utf-8'))
except OSError as e:
    fallback_dir = os.path.join(tempfile.gettempdir(), 'BabelGG')
    try:
        os.makedirs(fallback_dir, exist_ok=True)
        _fallback_log = os.path.join(fallback_dir, 'babelgg.log')
        _log_handlers.append(logging.FileHandler(_fallback_log, encoding='utf-8'))
        _EARLY_STARTUP_WARNING = f'Primary data folder unavailable, using temp log: {_fallback_log}'
    except OSError as e2:
        _EARLY_STARTUP_WARNING = (
            f'Could not create log file in data or temp directories: '
            f'{type(e).__name__}: {e}; {type(e2).__name__}: {e2}'
        )

if getattr(sys, 'stdout', None) is not None and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if getattr(sys, 'stderr', None) is not None and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(message)s',
    handlers=_log_handlers,
)
if _EARLY_STARTUP_WARNING:
    logging.warning(f'[MAIN] {_EARLY_STARTUP_WARNING}')

from core   import hardware
from core.i18n     import apply_auto_language_preferences, set_runtime_language, tr
from core.vault     import TranslationVault
from core.flash     import FlashEngine
from core.catch     import ClipboardMonitor
from core.license   import LicenseManager
from core.ocr       import OCRReader
from core.telemetry import Telemetry
from core   import updater as _updater
from ui.card        import TranslationCard
from ui.reply       import ReplyBox
from ui.ocr_overlay import OCRSelectionOverlay
from ui.tray        import TrayManager
from ui.settings    import SettingsWindow
from ui.downloader  import DownloaderDialog, needs_download
from ui.history      import HistoryDialog


def load_config() -> dict:
    user_cfg = user_config_path()
    try:
        load_path = user_cfg if os.path.isfile(user_cfg) else _resource_path('config.json')
        with open(load_path, 'r', encoding='utf-8-sig') as f:
            cfg = json.load(f)
        return apply_auto_language_preferences(cfg, FlashEngine.LANG_CODES.keys())
    except Exception as e:
        logging.error(f'[MAIN] Config load failed: {e}')
        return apply_auto_language_preferences({}, FlashEngine.LANG_CODES.keys())


def load_version() -> dict:
    try:
        with open(_resource_path('version.json'), 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f'[MAIN] version.json load failed: {e}')
        return {}


def save_config(cfg: dict):
    try:
        save_path = user_config_path()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        logging.info('[MAIN] Config saved')
    except Exception as e:
        logging.error(f'[MAIN] Config save failed: {e}')


def ensure_runtime_data_files():
    # Seed user data folder with packaged defaults on first run.
    defaults = ['phrases.json', 'meta.json', 'telemetry.json', 'vault.json']
    for name in defaults:
        dst = data_path(name)
        if os.path.isfile(dst):
            continue
        src = _resource_path('data', name)
        if not os.path.isfile(src):
            continue
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            logging.info('[MAIN] Seeded runtime data: %s', name)
        except Exception as e:
            logging.warning(f'[MAIN] Failed to seed runtime data {name}: {type(e).__name__}: {e}')


class BabelGG(QObject):
    # Emitted from background thread â€” shows card on main Qt thread
    card_signal = pyqtSignal(dict)
    ocr_done_signal = pyqtSignal(dict)

    def __init__(self, instance_lock_fh=None, instance_lock_name=None):
        super().__init__()
        self.config  = load_config()
        set_runtime_language(self.config.get('app_language', 'english'))
        ensure_runtime_data_files()
        self.config.setdefault('translation_cache_enabled', False)
        self.flash   = None
        self.vault   = None
        self.catch   = None
        self.license = LicenseManager()
        self.telemetry = Telemetry()
        self.ocr = OCRReader()
        self._instance_lock_fh = instance_lock_fh
        self._paused = False
        self._cards: list[TranslationCard] = []
        self._reply_boxes: list[ReplyBox] = []
        self._last_result: dict | None = None
        self._settings_open = False
        self._ocr_overlay: OCRSelectionOverlay | None = None
        self._hotkey_last_reply_at = 0.0
        self._hotkey_last_settings_at = 0.0
        self._hotkey_last_reshow_at = 0.0
        self._hotkey_cooldown_s = 0.9
        self._hotkey_handles = []
        self._startup_device_override = None
        self._detected_startup_device = 'cpu'
        # Wire signal to card display â€” runs on main Qt thread
        self.card_signal.connect(self._show_card)
        self.ocr_done_signal.connect(self._on_ocr_done)
        logging.info('[MAIN] BabelGG v2 initialised')

    def _check_cuda_runtime(self):
        try:
            hw = hardware.detect()
            self._detected_startup_device = str(hw.get('device', 'cpu')).lower()
            configured_device = str(self.cfg('flash_device', self._detected_startup_device)).lower().strip()
            if configured_device not in ('cpu', 'cuda'):
                configured_device = self._detected_startup_device
            device = configured_device
        except Exception:
            configured_device = str(self.cfg('flash_device', 'cpu')).lower().strip()
            device = configured_device if configured_device in ('cpu', 'cuda') else 'cpu'
            hw = {}

        if device != 'cuda':
            return

        cuda_ok = bool(hw.get('cuda_available', False))
        if not cuda_ok:
            reason = str(hw.get('cuda_reason') or 'CUDA runtime unavailable')
            self._startup_device_override = 'cpu'
            logging.warning('[MAIN] CUDA unavailable at startup: %s', reason)
            warn_icon = getattr(QSystemTrayIcon.MessageIcon.Warning, 'value', QSystemTrayIcon.MessageIcon.Warning)
            self.tray.notify_requested.emit(
                'BabelGG',
                f'GPU acceleration unavailable ({reason}). Running in CPU mode. Translations may be slower.',
                int(warn_icon),
            )

    def cfg(self, key, default=None):
        return self.config.get(key, default)

    def cfg_int(self, key: str, default: int, min_val: int = None, max_val: int = None) -> int:
        try:
            val = int(self.config.get(key, default))
            if min_val is not None:
                val = max(min_val, val)
            if max_val is not None:
                val = min(max_val, val)
            return val
        except (ValueError, TypeError):
            logging.warning(f'[MAIN] Config key {key} invalid, using default {default}')
            return default

    def cfg_float(self, key: str, default: float, min_val: float = None, max_val: float = None) -> float:
        try:
            val = float(self.config.get(key, default))
            if min_val is not None:
                val = max(min_val, val)
            if max_val is not None:
                val = min(max_val, val)
            return val
        except (ValueError, TypeError):
            logging.warning(f'[MAIN] Config key {key} invalid, using default {default}')
            return default

    def _telemetry_enabled(self) -> bool:
        return bool(self.config.get('telemetry_local_enabled', True))

    # â”€â”€ Startup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def start(self):
        # 1. Tray icon â€” shown immediately
        self.tray = TrayManager(
            asset_path('traylogo.png'),
            app_language=self.config.get('app_language', 'english'),
            parent=self,
        )
        self.tray.set_status(tr('status_starting', 'Starting...'))
        if _EARLY_STARTUP_WARNING:
            self.tray.set_status('Data folder issue detected — using fallback log path')
        self.tray.settings_requested.connect(self._open_settings)
        self.tray.upgrade_requested.connect(self._open_upgrade_page)
        self.tray.history_requested.connect(self._open_history)
        self.tray.quit_requested.connect(self._quit)
        self.tray.pause_toggled.connect(self._on_pause_toggled)
        self.tray.set_pro_status(self.license.is_pro())
        self._check_cuda_runtime()

        # 2. Global hotkeys
        self._register_hotkeys()

        # 3. First-run download (blocks until done or user cancels)
        ver_cfg = load_version()
        configured_device = str(self.cfg('flash_device', self._detected_startup_device)).lower().strip()
        if configured_device not in ('cpu', 'cuda'):
            configured_device = self._detected_startup_device
        effective_device = str(self._startup_device_override or configured_device).lower()
        if needs_download(ver_cfg, required_device=effective_device):
            dlg = DownloaderDialog(ver_cfg, required_device=effective_device, parent=None)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                # User cancelled â€” quit cleanly
                logging.info('[MAIN] Download cancelled by user â€” exiting')
                QApplication.instance().quit()
                return
            # Mark first_run complete
            self.config['first_run'] = False
            save_config(self.config)

        # 4. VAULT — optional. Disabled by default for max translation fidelity.
        if bool(self.config.get('translation_cache_enabled', False)):
            self.vault = TranslationVault()
            logging.info('[MAIN] Translation cache enabled')
        else:
            self.vault = None
            logging.info('[MAIN] Translation cache disabled (fresh LLM inference)')

        # 3. FLASH â€” background thread (loads model)
        self.tray.set_status(tr('status_warming_flash', 'Warming FLASH engine...'))
        threading.Thread(
            target=self._warm_flash, daemon=True, name='FlashWarmup'
        ).start()

    # â”€â”€ Global hotkeys â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _register_hotkeys(self):
        if not _KEYBOARD_AVAILABLE:
            logging.warning('[MAIN] keyboard module unavailable â€” hotkeys disabled')
            self.tray.set_status('Hotkeys disabled (keyboard module missing)')
            return

        # Rebind cleanly so settings changes can apply live without duplicates.
        for handle in list(self._hotkey_handles):
            try:
                _keyboard.remove_hotkey(handle)
            except Exception:
                pass
        self._hotkey_handles = []

        hk = self.cfg('hotkeys', {})

        def _hotkey(name: str, default: str) -> str:
            raw = hk.get(name, default)
            combo = str(raw).strip() or default
            # keyboard library expects named keys like "comma" instead of ","
            combo = combo.replace('+,', '+comma')
            return combo

        def _hotkeys(name: str, default: str) -> list[str]:
            raw = hk.get(name, default)
            if isinstance(raw, list):
                values = [str(v).strip() for v in raw]
            else:
                values = [str(raw).strip()]
            out = []
            for value in values:
                if value:
                    out.append(value.replace('+,', '+comma'))
            if not out:
                out.append(default)
            return out

        bindings = [
            (_hotkey('toggle', 'ctrl+shift+h'), '_hotkey_toggle'),
            (_hotkey('settings', 'ctrl+shift+comma'), '_hotkey_settings'),
            # OCR hotkey disabled — hide for now
            # (_hotkey('ocr', 'ctrl+shift+g'), '_hotkey_ocr'),
            (_hotkey('reshow', 'ctrl+shift+t'), '_hotkey_reshow'),
        ]

        for combo in _hotkeys('reply', 'ctrl+shift+r'):
            bindings.append((combo, '_hotkey_reply'))
        # Near-hand backup hotkeys for games that swallow Ctrl+Shift combos.
        for combo in _hotkeys('reply_alt', 'alt+r'):
            bindings.append((combo, '_hotkey_reply'))
        # Keep legacy far-key fallback as tertiary option.
        for combo in _hotkeys('reply_legacy_alt', 'f8'):
            bindings.append((combo, '_hotkey_reply'))

        # Keep first registration of each exact combo only.
        deduped = []
        seen = set()
        for combo, slot_name in bindings:
            key = (combo.lower(), slot_name)
            if key in seen:
                continue
            seen.add(key)
            deduped.append((combo, slot_name))

        failed = []
        for combo, slot_name in deduped:
            try:
                handle = _keyboard.add_hotkey(
                    combo,
                    lambda s=slot_name: QMetaObject.invokeMethod(
                        self, s, Qt.ConnectionType.QueuedConnection
                    ),
                    suppress=False,
                    trigger_on_release=False,
                )
                self._hotkey_handles.append(handle)
                logging.info(f'[MAIN] Hotkey registered: {combo} -> {slot_name}')
            except Exception as e:
                logging.error(f'[MAIN] Failed to register hotkey {combo!r}: {e}')
                failed.append(combo)
        if failed:
            self.tray.set_status(
                f'Hotkeys partial ({len(failed)} failed â€” try running as admin)'
            )

        reply_registered = [combo for combo, slot in deduped if slot == '_hotkey_reply' and combo not in failed]
        if reply_registered:
            logging.info(f'[MAIN] Reply hotkeys active: {", ".join(reply_registered)}')

    @pyqtSlot()
    def _hotkey_toggle(self):
        self.tray.toggle_pause()

    @pyqtSlot()
    def _hotkey_reply(self):
        now = time.monotonic()
        if now - self._hotkey_last_reply_at < self._hotkey_cooldown_s:
            logging.info('[MAIN] Hotkey reply ignored (cooldown)')
            return
        self._hotkey_last_reply_at = now
        logging.info('[MAIN] Hotkey reply fired')
        # If a reply box is already open, focus it instead of opening another
        visible_reply = [r for r in self._reply_boxes if r.isVisible()]
        if visible_reply:
            visible_reply[-1].focus_input()
            return
        visible_cards = [c for c in self._cards if c.isVisible()]
        if visible_cards:
            self._open_reply(visible_cards[-1].result)
        elif self._last_result:
            self._open_reply(self._last_result)
        else:
            logging.info('[MAIN] Hotkey reply: opening compose mode without context')
            self._open_reply(None)

    @pyqtSlot()
    def _hotkey_settings(self):
        now = time.monotonic()
        if now - self._hotkey_last_settings_at < self._hotkey_cooldown_s:
            logging.info('[MAIN] Hotkey settings ignored (cooldown)')
            return
        self._hotkey_last_settings_at = now
        logging.info('[MAIN] Hotkey settings fired')
        self._open_settings()

    @pyqtSlot()
    def _hotkey_reshow(self):
        now = time.monotonic()
        if now - self._hotkey_last_reshow_at < self._hotkey_cooldown_s:
            logging.info('[MAIN] Hotkey reshow ignored (cooldown)')
            return
        self._hotkey_last_reshow_at = now
        if not self._last_result:
            logging.info('[MAIN] Hotkey reshow: no last result to show')
            return
        logging.info('[MAIN] Hotkey reshow fired')
        # Use signal path to keep UI updates on Qt main thread.
        self.card_signal.emit(dict(self._last_result))

    @pyqtSlot()
    def _hotkey_ocr(self):
        logging.info('[MAIN] Hotkey OCR fired')
        # OCR capture is local/offline; allow launching regardless of plan.
        self._do_ocr()

    # â”€â”€ Warmup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _warm_flash(self):
        try:
            hw     = hardware.detect()
            device = self._startup_device_override or self.cfg('flash_device', hw['device'])
            self.flash = FlashEngine(device=device, vault=self.vault)
            if self.flash.ready:
                # CATCH starts only after FLASH is ready
                self.catch = ClipboardMonitor(
                    flash=self.flash,
                    callback=self.card_signal.emit,   # thread-safe
                    tgt_language=self.cfg('my_language', 'english'),
                    min_emit_interval_s=self.cfg_float('card_rate_limit_s', 0.0, min_val=0.0, max_val=10.0),
                )
                self.catch.start()
                self.tray.set_pro_status(self.license.is_pro())
                self.tray.set_status(tr('status_ready', 'Ready - Copy foreign text to translate'))
                logging.info('[MAIN] All systems go')
                threading.Thread(target=self.license.validate_cached, daemon=True, name='LicenseValidate').start()
                # Spawn silent update check (once per day)
                _updater.start(
                    running_ver=self.config.get('version', '0.1.0'),
                    tray=self.tray,
                )
            else:
                msg = getattr(self.flash, 'last_error_message', '') or 'FLASH failed to load — check logs'
                self.tray.set_status(msg)
        except Exception as e:
            logging.error(f'[MAIN] Warmup failed: {type(e).__name__}: {e}')
            self.tray.set_status('Startup error â€” check logs')

    # â”€â”€ Card display â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _show_card(self, result: dict):
        # Always on main Qt thread via signal
        # Keep manual OCR usable even while clipboard monitoring is paused.
        if self._paused and not bool(result.get('ocr_source')):
            return
        self._last_result = result
        timeout = self.cfg_int('card_timeout', 5, min_val=1, max_val=30)
        card_anchor = self.cfg('card_anchor', 'bottom_right')
        compact = bool(self.cfg('card_compact', True))
        card = TranslationCard(
            result,
            timeout_s=timeout,
            anchor=card_anchor,
            compact=compact,
            parent=None,
        )
        card.reply_requested.connect(self._open_reply)
        card.closed.connect(lambda shown_ms, dismissed_by, c=card: self._on_card_closed(c, shown_ms, dismissed_by))
        card.show()
        self._cards.append(card)
        self._stack_cards()
        if self._telemetry_enabled():
            self.telemetry.log_translation(
                src_lang=result.get('src_lang'),
                tgt_lang=result.get('tgt_lang'),
                text_length=len(str(result.get('original') or '')),
                translation_ms=int(result.get('ms') or 0),
                cache_hit=bool(result.get('cache_hit', False)),
                phrase_db_hit=bool(result.get('phrase_hit', False)),
                slang_normalized=bool(result.get('normalized')),
                emoji_cleaned=bool(result.get('emoji_cleaned', False)),
                naturalizer_applied=bool(result.get('naturalizer_applied', False)),
            )
        logging.info(f'[MAIN] Card: {result.get("translation", "")[:50]}')

    def _on_card_closed(self, card: TranslationCard, shown_ms: int, dismissed_by: str):
        if card in self._cards:
            self._cards.remove(card)
        src_lang = str(card.result.get('src_lang', ''))
        if self._telemetry_enabled():
            self.telemetry.log_card_dismissed(src_lang=src_lang, card_shown_ms=shown_ms, dismissed_by=dismissed_by)

    def _stack_cards(self):
        # Stack visible cards vertically so they don't overlap
        visible = [c for c in self._cards if c.isVisible()]
        if len(visible) <= 1:
            return
        base = visible[-1]
        anchor = str(self.cfg('card_anchor', 'bottom_right')).lower()
        is_top_anchor = anchor.startswith('top')
        for i, card in enumerate(reversed(visible[:-1])):
            offset = (i + 1) * (base.height() + 8)
            y = base.y() + offset if is_top_anchor else base.y() - offset
            card.move(base.x(), y)

    # â”€â”€ Reply â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _open_reply(self, result: dict | None):
        if not self.flash or not self.flash.ready:
            logging.warning('[MAIN] Reply requested but FLASH not ready')
            return
        try:
            if result:
                self._last_result = result

            default_tgt_lang_code = str(self.config.get('reply_default_lang_code', 'jpn_Jpan'))
            reply = ReplyBox(
                self.flash,
                result,
                compact=bool(self.cfg('card_compact', True)),
                default_tgt_lang_code=default_tgt_lang_code,
                parent=None,
            )
            reply.sent.connect(self._on_reply_sent)
            if self._telemetry_enabled():
                reply.opened.connect(self.telemetry.log_reply_opened)
            reply.destroyed.connect(
                lambda *_args, r=reply: self._reply_boxes.remove(r)
                if r in self._reply_boxes else None
            )
            self._reply_boxes.append(reply)

            reply.show()
            reply.showNormal()
            reply.raise_()
            reply.activateWindow()
            reply.focus_input()
        except Exception as e:
            logging.error(f'[MAIN] Failed to open reply widget: {type(e).__name__}: {e}')
            self.tray.set_status('Reply widget failed to open — check logs')

    def _on_reply_sent(self, text: str):
        if self.catch:
            self.catch.ignore_once(text)
        logging.info('[MAIN] Reply sent: clipboard suppression armed')

    # â”€â”€ Settings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _open_settings(self):
        if self._settings_open:
            return
        self._settings_open = True
        def on_save(new_cfg: dict):
            new_cfg = apply_auto_language_preferences(new_cfg, FlashEngine.LANG_CODES.keys())
            self.config = new_cfg
            set_runtime_language(self.config.get('app_language', 'english'))
            if self.tray:
                self.tray.set_language(self.config.get('app_language', 'english'))
            save_config(new_cfg)
            # Apply language change live
            if self.catch:
                self.catch.set_language(new_cfg.get('my_language', 'english'))
                self.catch.set_rate_limit(self.cfg_float('card_rate_limit_s', 0.0, min_val=0.0, max_val=10.0))
            # Apply device change if needed
            if self.flash and new_cfg.get('flash_device') != self.flash.device:
                logging.info('[MAIN] Device changed — will apply on next start')

            # Apply hotkeys live.
            self._register_hotkeys()

        def on_license_changed(is_pro: bool):
            self.tray.set_pro_status(is_pro)
            status = tr('status_ready', 'Ready - Copy foreign text to translate')
            self.tray.set_status(status)

        win = SettingsWindow(
            self.config,
            on_save,
            license_manager=self.license,
            on_license_changed=on_license_changed,
            telemetry=self.telemetry,
            parent=None,
        )
        win.exec()
        self._settings_open = False

    def _open_upgrade_page(self):
        webbrowser.open('https://babelgg.gg/pro')

    def _show_upgrade_dialog(self, feature_name: str):
        msg = QMessageBox()
        msg.setWindowTitle('BabelGG Pro')
        msg.setText(f'{feature_name} is a Pro feature.')
        msg.setInformativeText('Upgrade to Pro for $4.99/month or $29 lifetime.')
        upgrade_btn = msg.addButton(tr('tray_upgrade', 'Upgrade to Pro'), QMessageBox.ButtonRole.AcceptRole)
        msg.addButton(tr('btn_cancel', 'Cancel'), QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        if msg.clickedButton() == upgrade_btn:
            self._open_upgrade_page()

    def _do_ocr(self):
        if not self.flash or not self.flash.ready:
            self.tray.set_status('OCR unavailable: FLASH not ready')
            return
        if self._ocr_overlay and self._ocr_overlay.isVisible():
            self.tray.set_status('OCR already active')
            return
        if not self.ocr.is_available():
            msg = self.ocr.availability_error()
            self.tray.set_status('OCR backend missing (install easyocr)')
            logging.warning(f'[OCR] Backend unavailable: {msg}')
            return
        logging.info('[MAIN] OCR capture requested')
        self.tray.set_status('OCR: drag to select region')
        # Delay slightly to let hotkey keys release before overlay focus.
        QTimer.singleShot(70, self._start_ocr_overlay)

    def _start_ocr_overlay(self):
        try:
            overlay = OCRSelectionOverlay(parent=None)
            self._ocr_overlay = overlay
            overlay.selected.connect(self._on_ocr_region_selected)
            overlay.cancelled.connect(self._on_ocr_cancelled)
            overlay.destroyed.connect(lambda *_args: setattr(self, '_ocr_overlay', None))
            overlay.show()
            overlay.raise_()
            overlay.activateWindow()
        except Exception as e:
            logging.error(f'[OCR] Failed to start overlay: {type(e).__name__}: {e}')
            self.tray.set_status('OCR failed to start')

    def _on_ocr_cancelled(self):
        logging.info('[OCR] Capture cancelled')
        self.tray.set_status(tr('status_ready', 'Ready - Copy foreign text to translate'))

    def _expand_capture_rect(self, rect: QRect) -> QRect:
        """Pad small OCR selections so single-line crops remain readable."""
        try:
            screens = QGuiApplication.screens()
            if not screens:
                return rect

            left = min(s.geometry().left() for s in screens)
            top = min(s.geometry().top() for s in screens)
            right = max(s.geometry().right() for s in screens)
            bottom = max(s.geometry().bottom() for s in screens)
            bounds = QRect(left, top, (right - left) + 1, (bottom - top) + 1)

            # Add adaptive context and enforce a practical minimum crop size.
            # Smaller selections need more aggressive expansion to preserve
            # enough character context for OCR engines.
            src_w = max(1, rect.width())
            src_h = max(1, rect.height())
            short_side = min(src_w, src_h)

            if short_side <= 28:
                margin = 28
                min_w = 200
                min_h = 96
            elif short_side <= 44:
                margin = 24
                min_w = 180
                min_h = 84
            elif short_side <= 72:
                margin = 20
                min_w = 150
                min_h = 72
            else:
                margin = 16
                min_w = 120
                min_h = 56

            out = QRect(rect)
            out.adjust(-margin, -margin, margin, margin)

            if out.width() < min_w:
                pad = (min_w - out.width()) // 2 + 1
                out.adjust(-pad, 0, pad, 0)
            if out.height() < min_h:
                pad = (min_h - out.height()) // 2 + 1
                out.adjust(0, -pad, 0, pad)

            out = out.intersected(bounds)
            return out if out.width() > 0 and out.height() > 0 else rect
        except Exception as e:
            logging.warning(f'[OCR] Failed to expand crop rect: {type(e).__name__}: {e}')
            return rect

    def _capture_region_to_file(self, rect: QRect) -> str:
        try:
            expanded = self._expand_capture_rect(rect)
            screen = QGuiApplication.screenAt(expanded.center()) or QGuiApplication.primaryScreen()
            if screen is None:
                logging.error('[OCR] No screen available for capture')
                return ''
            sg = screen.geometry()
            sx = expanded.x() - sg.x()
            sy = expanded.y() - sg.y()
            pix = screen.grabWindow(0, sx, sy, expanded.width(), expanded.height())
            if pix.isNull():
                logging.error('[OCR] Screen grab returned empty image')
                return ''
            logging.info(
                '[OCR] Capture rect raw=(%d,%d %dx%d) expanded=(%d,%d %dx%d)',
                rect.x(), rect.y(), rect.width(), rect.height(),
                expanded.x(), expanded.y(), expanded.width(), expanded.height(),
            )
            path = data_path(f'ocr_capture_{int(time.time() * 1000)}.png')
            ok = pix.save(path, 'PNG')
            if not ok:
                logging.error('[OCR] Failed to save capture image')
                return ''
            return path
        except Exception as e:
            logging.error(f'[OCR] Capture failed: {type(e).__name__}: {e}')
            return ''

    def _on_ocr_region_selected(self, rect: QRect):
        if rect.width() < 12 or rect.height() < 12:
            self._on_ocr_cancelled()
            return
        self.tray.set_status('OCR: reading text...')
        image_path = self._capture_region_to_file(rect)
        if not image_path:
            self.tray.set_status('OCR capture failed')
            return
        threading.Thread(
            target=self._run_ocr_pipeline,
            args=(image_path,),
            daemon=True,
            name='OCRCaptureWorker',
        ).start()

    def _run_ocr_pipeline(self, image_path: str):
        try:
            ocr_result = self.ocr.extract_text_from_image(image_path)
        finally:
            try:
                os.remove(image_path)
            except OSError:
                pass

        if not ocr_result.text:
            self.ocr_done_signal.emit({
                'ok': False,
                'message': ocr_result.error or 'OCR found no text',
            })
            return

        # Single garbled-text gate: keep rejection policy in app pipeline
        # to avoid duplicate filtering across OCR backend and caller.
        if self.ocr.is_likely_garbled(ocr_result.text):
            self.ocr_done_signal.emit({
                'ok': False,
                'message': 'OCR result looks noisy. Crop a bit wider and keep text high-contrast.',
            })
            return

        tgt_lang = self.cfg('my_language', 'english')
        translated = self.flash.translate(ocr_result.text, tgt_lang) if self.flash else None
        if not translated:
            # For OCR, still show the extracted text as a card so the user
            # gets immediate feedback even when src==tgt.
            src_lang = self.flash.detect_lang(ocr_result.text) if self.flash else 'unknown'
            tgt_code = self.flash.LANG_CODES.get(str(tgt_lang).lower(), 'eng_Latn') if self.flash else 'eng_Latn'
            translated = {
                'original': ocr_result.text,
                'translation': ocr_result.text,
                'src_lang': src_lang,
                'tgt_lang': tgt_code,
                'ms': 0,
                'cache_hit': False,
                'phrase_hit': False,
                'naturalizer_applied': False,
                'ocr_source': True,
                'ocr_backend': ocr_result.backend,
            }
            self.ocr_done_signal.emit({
                'ok': True,
                'result': translated,
                'message': f"OCR extracted text ({ocr_result.backend}); already in target language",
            })
            return

        translated['ocr_source'] = True
        translated['ocr_backend'] = ocr_result.backend
        self.ocr_done_signal.emit({
            'ok': True,
            'result': translated,
            'message': f"OCR complete ({ocr_result.backend})",
        })

    @pyqtSlot(dict)
    def _on_ocr_done(self, payload: dict):
        if payload.get('ok') and payload.get('result'):
            self.card_signal.emit(payload['result'])
            self.tray.set_status(payload.get('message') or 'OCR translated')
            return

        msg = payload.get('message', 'OCR failed')
        self.tray.set_status(msg)
        self.tray.showMessage('BabelGG OCR', msg, QSystemTrayIcon.MessageIcon.Information, 2500)

    def _open_history(self):
        if not self.license.check('history'):
            self._show_upgrade_dialog('Translation History')
            return
        dlg = HistoryDialog(self.vault, self.license, self)
        dlg.exec()

    # â”€â”€ Pause / Resume â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _on_pause_toggled(self, paused: bool):
        self._paused = paused
        if self.catch:
            if paused:
                self.catch.pause()
            else:
                self.catch.resume()

    # â”€â”€ Quit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _quit(self):
        logging.info('[MAIN] Quitting')
        if self.catch:
            self.catch.stop()
        if self.vault:
            self.vault.flush()
        if self.telemetry:
            self.telemetry.flush()
        self._release_instance_lock()
        QApplication.instance().quit()

    def _release_instance_lock(self):
        if self._instance_lock_fh:
            _release_single_instance_lock(self._instance_lock_fh)
            self._instance_lock_fh = None


def _acquire_single_instance_lock() -> tuple[object | None, str, str]:
    """
    Acquire a named Windows mutex for single-instance enforcement.
    Returns (mutex_handle, lock_path, state) where state is 'acquired', 'busy', or 'error'.
    On success, caller must call _release_single_instance_lock(mutex_handle) on shutdown.
    """
    import ctypes
    from ctypes import wintypes

    MUTEX_NAME = 'BabelGG_SingleInstance_Mutex'
    WAIT_ABANDONED = 0x80
    WAIT_OBJECT_0 = 0x0

    kernel32 = ctypes.windll.kernel32
    CreateMutexW = kernel32.CreateMutexW
    CreateMutexW.restype = wintypes.HANDLE
    CreateMutexW.argtypes = (wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCWSTR)

    WaitForSingleObject = kernel32.WaitForSingleObject
    WaitForSingleObject.restype = wintypes.DWORD
    WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)

    ReleaseMutex = kernel32.ReleaseMutex
    ReleaseMutex.restype = wintypes.BOOL
    ReleaseMutex.argtypes = (wintypes.HANDLE,)

    CloseHandle = kernel32.CloseHandle
    CloseHandle.restype = wintypes.BOOL
    CloseHandle.argtypes = (wintypes.HANDLE,)

    mutex = CreateMutexW(None, False, MUTEX_NAME)
    if not mutex or mutex == -1:
        return None, MUTEX_NAME, 'error'

    wait = WaitForSingleObject(mutex, 0)
    if wait == WAIT_OBJECT_0:
        # We own the mutex — we're the first instance
        return mutex, MUTEX_NAME, 'acquired'
    elif wait == WAIT_ABANDONED:
        # Previous owner crashed without releasing — take ownership anyway
        logging.warning('[MAIN] Previous instance crashed; taking ownership of mutex')
        return mutex, MUTEX_NAME, 'acquired'
    else:
        # Another instance already holds it
        CloseHandle(mutex)
        return None, MUTEX_NAME, 'busy'


def _release_single_instance_lock(mutex_handle):
    """Release the named mutex and close the handle."""
    if not mutex_handle:
        return
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        ReleaseMutex = kernel32.ReleaseMutex
        ReleaseMutex.restype = wintypes.BOOL
        ReleaseMutex.argtypes = (wintypes.HANDLE,)
        CloseHandle = kernel32.CloseHandle
        CloseHandle.restype = wintypes.BOOL
        CloseHandle.argtypes = (wintypes.HANDLE,)
        ReleaseMutex(mutex_handle)
        CloseHandle(mutex_handle)
    except Exception as e:
        logging.warning(f'[MAIN] Failed to release mutex: {type(e).__name__}: {e}')



if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(asset_path('traylogo.png')))
    app.setQuitOnLastWindowClosed(False)

    # ── Single-instance lock ──────────────────────────────────────────────────
    _mutex, _mutex_name, _lock_state = _acquire_single_instance_lock()
    if _mutex is None:
        if _lock_state == 'busy':
            logging.warning('[MAIN] Single instance check failed: already running')
            QMessageBox.information(None, 'BabelGG', 'BabelGG is already running')
            sys.exit(0)

        # Do not block app startup when lock mechanism itself fails unexpectedly.
        logging.warning('[MAIN] Instance lock unavailable; continuing without single-instance guard')

    # Tell Windows this process is BabelGG, not pythonw.exe — fixes taskbar icon.
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('BabelGG')
    except Exception as e:
        logging.warning(f'[MAIN] AppUserModelID failed: {e}')

    babelgg = BabelGG(instance_lock_fh=_mutex, instance_lock_name=_mutex_name)
    babelgg.start()
    logging.info('[MAIN] Qt event loop started')
    sys.exit(app.exec())
