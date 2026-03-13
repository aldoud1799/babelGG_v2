import sys, logging, json, os, threading, msvcrt

# Pre-load ML libraries before Qt â€” prevents DLL init conflicts on Windows
import ctranslate2  # noqa
from transformers import NllbTokenizer  # noqa: loads torch before Qt DLLs

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore    import QObject, pyqtSignal, QMetaObject, Qt, pyqtSlot
from PyQt6.QtGui     import QIcon
from core.paths      import BASE_DIR, base_path, data_path, asset_path

# keyboard â€” optional; hotkey registration silently degrades without admin rights
try:
    import keyboard as _keyboard
    _KEYBOARD_AVAILABLE = True
except Exception as _kb_err:
    _keyboard = None
    _KEYBOARD_AVAILABLE = False

# â”€â”€ Logging â€” must be first â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
os.makedirs(data_path(), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(message)s',
    handlers=[
        logging.FileHandler(data_path('babelgg.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)

from core   import hardware
from core.vault     import TranslationVault
from core.flash     import FlashEngine
from core.catch     import ClipboardMonitor
from core   import updater as _updater
from ui.card        import TranslationCard
from ui.reply       import ReplyBox
from ui.tray        import TrayManager
from ui.settings    import SettingsWindow
from ui.downloader  import DownloaderDialog, needs_download


def load_config() -> dict:
    try:
        with open(base_path('config.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f'[MAIN] Config load failed: {e}')
        return {}


def load_version() -> dict:
    try:
        with open(base_path('version.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f'[MAIN] version.json load failed: {e}')
        return {}


def save_config(cfg: dict):
    try:
        with open(base_path('config.json'), 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        logging.info('[MAIN] Config saved')
    except Exception as e:
        logging.error(f'[MAIN] Config save failed: {e}')


class BabelGG(QObject):
    # Emitted from background thread â€” shows card on main Qt thread
    card_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.config  = load_config()
        self.flash   = None
        self.vault   = None
        self.catch   = None
        self._paused = False
        self._cards: list[TranslationCard] = []
        self._reply_boxes: list[ReplyBox] = []
        self._last_result: dict | None = None
        self._settings_open = False
        # Wire signal to card display â€” runs on main Qt thread
        self.card_signal.connect(self._show_card)
        logging.info('[MAIN] BabelGG v2 initialised')

    def cfg(self, key, default=None):
        return self.config.get(key, default)

    # â”€â”€ Startup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def start(self):
        # 1. Tray icon â€” shown immediately
        self.tray = TrayManager(asset_path('icon.ico'), parent=self)
        self.tray.set_status('Starting...')
        self.tray.settings_requested.connect(self._open_settings)
        self.tray.quit_requested.connect(self._quit)
        self.tray.pause_toggled.connect(self._on_pause_toggled)

        # 2. Global hotkeys
        self._register_hotkeys()

        # 3. First-run download (blocks until done or user cancels)
        ver_cfg = load_version()
        if needs_download(ver_cfg):
            dlg = DownloaderDialog(ver_cfg, parent=None)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                # User cancelled â€” quit cleanly
                logging.info('[MAIN] Download cancelled by user â€” exiting')
                QApplication.instance().quit()
                return
            # Mark first_run complete
            self.config['first_run'] = False
            save_config(self.config)

        # 4. VAULT â€” synchronous, fast
        self.vault = TranslationVault()

        # 3. FLASH â€” background thread (loads model)
        self.tray.set_status('Warming FLASH engine...')
        threading.Thread(
            target=self._warm_flash, daemon=True, name='FlashWarmup'
        ).start()

    # â”€â”€ Global hotkeys â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _register_hotkeys(self):
        if not _KEYBOARD_AVAILABLE:
            logging.warning('[MAIN] keyboard module unavailable â€” hotkeys disabled')
            self.tray.set_status('Hotkeys disabled (keyboard module missing)')
            return
        hk = self.cfg('hotkeys', {})

        def _hotkey(name: str, default: str) -> str:
            raw = hk.get(name, default)
            combo = str(raw).strip() or default
            # keyboard library expects named keys like "comma" instead of ","
            combo = combo.replace('+,', '+comma')
            return combo

        bindings = [
            (_hotkey('toggle', 'ctrl+shift+h'), '_hotkey_toggle'),
            (_hotkey('reply', 'ctrl+shift+r'), '_hotkey_reply'),
            (_hotkey('settings', 'ctrl+shift+comma'), '_hotkey_settings'),
        ]
        failed = []
        for combo, slot_name in bindings:
            try:
                _keyboard.add_hotkey(
                    combo,
                    lambda s=slot_name: QMetaObject.invokeMethod(
                        self, s, Qt.ConnectionType.QueuedConnection
                    )
                )
                logging.info(f'[MAIN] Hotkey registered: {combo} â†’ {slot_name}')
            except Exception as e:
                logging.error(f'[MAIN] Failed to register hotkey {combo!r}: {e}')
                failed.append(combo)
        if failed:
            self.tray.set_status(
                f'Hotkeys partial ({len(failed)} failed â€” try running as admin)'
            )

    @pyqtSlot()
    def _hotkey_toggle(self):
        self.tray.toggle_pause()

    @pyqtSlot()
    def _hotkey_reply(self):
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
            logging.info('[MAIN] Hotkey reply: no translation context available')

    @pyqtSlot()
    def _hotkey_settings(self):
        self._open_settings()

    # â”€â”€ Warmup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _warm_flash(self):
        try:
            hw     = hardware.detect()
            device = self.cfg('flash_device', hw['device'])
            self.flash = FlashEngine(device=device, vault=self.vault)
            if self.flash.ready:
                # CATCH starts only after FLASH is ready
                self.catch = ClipboardMonitor(
                    flash=self.flash,
                    callback=self.card_signal.emit,   # thread-safe
                    tgt_language=self.cfg('my_language', 'english'),
                    min_emit_interval_s=float(self.cfg('card_rate_limit_s', 1.2)),
                )
                self.catch.start()
                self.tray.set_status('Ready âš¡ â€” Copy foreign text to translate')
                logging.info('[MAIN] All systems go')
                # Spawn silent update check (once per day)
                _updater.start(
                    running_ver=self.config.get('version', '0.1.0'),
                    tray=self.tray,
                )
            else:
                self.tray.set_status('FLASH failed to load â€” check data/babelgg.log')
        except Exception as e:
            logging.error(f'[MAIN] Warmup failed: {type(e).__name__}: {e}')
            self.tray.set_status('Startup error â€” check logs')

    # â”€â”€ Card display â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _show_card(self, result: dict):
        # Always on main Qt thread via signal
        if self._paused:
            return
        self._last_result = result
        timeout = self.cfg('card_timeout', 5)
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
        card.closed.connect(
            lambda: self._cards.remove(card) if card in self._cards else None
        )
        card.show()
        self._cards.append(card)
        self._stack_cards()
        logging.info(f'[MAIN] Card: {result.get("translation", "")[:50]}')

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
    def _open_reply(self, result: dict):
        if not self.flash or not self.flash.ready:
            logging.warning('[MAIN] Reply requested but FLASH not ready')
            return
        self._last_result = result
        reply = ReplyBox(
            self.flash,
            result,
            compact=bool(self.cfg('card_compact', True)),
            parent=None,
        )
        reply.sent.connect(self._on_reply_sent)
        reply.destroyed.connect(
            lambda *_args, r=reply: self._reply_boxes.remove(r)
            if r in self._reply_boxes else None
        )
        self._reply_boxes.append(reply)
        reply.show()
        reply.focus_input()

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
            self.config = new_cfg
            save_config(new_cfg)
            # Apply language change live
            if self.catch:
                self.catch.set_language(new_cfg.get('my_language', 'english'))
                self.catch.set_rate_limit(float(new_cfg.get('card_rate_limit_s', 1.2)))
            # Apply device change if needed
            if self.flash and new_cfg.get('flash_device') != self.flash.device:
                logging.info('[MAIN] Device changed — will apply on next start')
        win = SettingsWindow(self.config, on_save, parent=None)
        win.exec()
        self._settings_open = False

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
        QApplication.instance().quit()



if __name__ == '__main__':
    # ── Single-instance lock ──────────────────────────────────────────────────
    os.makedirs(data_path(), exist_ok=True)
    _lock_path = data_path('babelgg.lock')
    try:
        _lock_fh = open(_lock_path, 'w')
        msvcrt.locking(_lock_fh.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        print('[MAIN] BabelGG is already running.', file=sys.stderr)
        sys.exit(0)

    # Tell Windows this process is BabelGG, not pythonw.exe — fixes taskbar icon.
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('BabelGG.v2')
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(asset_path('icon.ico')))
    app.setQuitOnLastWindowClosed(False)
    babelgg = BabelGG()
    babelgg.start()
    logging.info('[MAIN] Qt event loop started')
    sys.exit(app.exec())
