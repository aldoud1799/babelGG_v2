import sys, logging, json, os, threading, msvcrt

# Pre-load ML libraries before Qt — prevents DLL init conflicts on Windows
import ctranslate2  # noqa
from transformers import NllbTokenizer  # noqa: loads torch before Qt DLLs

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore    import QObject, pyqtSignal, QMetaObject, Qt, pyqtSlot

# keyboard — optional; hotkey registration silently degrades without admin rights
try:
    import keyboard as _keyboard
    _KEYBOARD_AVAILABLE = True
except Exception as _kb_err:
    _keyboard = None
    _KEYBOARD_AVAILABLE = False

# ── Logging — must be first ──────────────────────────────────────────────────
os.makedirs('data', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('data', 'babelgg.log'), encoding='utf-8'),
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
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f'[MAIN] Config load failed: {e}')
        return {}


def load_version() -> dict:
    try:
        with open('version.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f'[MAIN] version.json load failed: {e}')
        return {}


def save_config(cfg: dict):
    try:
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        logging.info('[MAIN] Config saved')
    except Exception as e:
        logging.error(f'[MAIN] Config save failed: {e}')


class BabelGG(QObject):
    # Emitted from background thread — shows card on main Qt thread
    card_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.config  = load_config()
        self.flash   = None
        self.vault   = None
        self.catch   = None
        self._paused = False
        self._cards: list[TranslationCard] = []
        # Wire signal to card display — runs on main Qt thread
        self.card_signal.connect(self._show_card)
        logging.info('[MAIN] BabelGG v2 initialised')

    def cfg(self, key, default=None):
        return self.config.get(key, default)

    # ── Startup ──────────────────────────────────────────────────────────────
    def start(self):
        # 1. Tray icon — shown immediately
        self.tray = TrayManager('assets/icon.ico', parent=self)
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
                # User cancelled — quit cleanly
                logging.info('[MAIN] Download cancelled by user — exiting')
                QApplication.instance().quit()
                return
            # Mark first_run complete
            self.config['first_run'] = False
            save_config(self.config)

        # 4. VAULT — synchronous, fast
        self.vault = TranslationVault()

        # 3. FLASH — background thread (loads model)
        self.tray.set_status('Warming FLASH engine...')
        threading.Thread(
            target=self._warm_flash, daemon=True, name='FlashWarmup'
        ).start()

    # ── Global hotkeys ────────────────────────────────────────────────────────
    def _register_hotkeys(self):
        if not _KEYBOARD_AVAILABLE:
            logging.warning('[MAIN] keyboard module unavailable — hotkeys disabled')
            self.tray.set_status('Hotkeys disabled (keyboard module missing)')
            return
        hk = self.cfg('hotkeys', {})
        bindings = [
            (hk.get('toggle',   'ctrl+shift+h'),     '_hotkey_toggle'),
            (hk.get('reply',    'ctrl+shift+r'),     '_hotkey_reply'),
            (hk.get('settings', 'ctrl+shift+comma'), '_hotkey_settings'),
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
                logging.info(f'[MAIN] Hotkey registered: {combo} → {slot_name}')
            except Exception as e:
                logging.error(f'[MAIN] Failed to register hotkey {combo!r}: {e}')
                failed.append(combo)
        if failed:
            self.tray.set_status(
                f'Hotkeys partial ({len(failed)} failed — try running as admin)'
            )

    @pyqtSlot()
    def _hotkey_toggle(self):
        self.tray.toggle_pause()

    @pyqtSlot()
    def _hotkey_reply(self):
        visible = [c for c in self._cards if c.isVisible()]
        if visible:
            self._open_reply(visible[-1].result)
        else:
            logging.info('[MAIN] Hotkey reply: no visible cards to reply to')

    @pyqtSlot()
    def _hotkey_settings(self):
        self._open_settings()

    # ── Warmup ────────────────────────────────────────────────────────────────
    def _warm_flash(self):
        try:
            hw     = hardware.detect()
            device = self.cfg('flash_device', hw['device'])
            self.flash = FlashEngine(device=device, vault=self.vault)
            if self.flash.ready:
                # CATCH starts only after FLASH is ready
                self.catch = ClipboardMonitor(
                    flash=self.flash,
                    callback=self.card_signal.emit   # thread-safe
                )
                self.catch.start()
                self.tray.set_status('Ready ⚡ — Copy foreign text to translate')
                logging.info('[MAIN] All systems go')
                # Spawn silent update check (once per day)
                _updater.start(
                    running_ver=self.config.get('version', '0.1.0'),
                    tray=self.tray,
                )
            else:
                self.tray.set_status('FLASH failed to load — check data/babelgg.log')
        except Exception as e:
            logging.error(f'[MAIN] Warmup failed: {type(e).__name__}: {e}')
            self.tray.set_status('Startup error — check logs')

    # ── Card display ─────────────────────────────────────────────────────────
    def _show_card(self, result: dict):
        # Always on main Qt thread via signal
        if self._paused:
            return
        timeout = self.cfg('card_timeout', 5)
        card    = TranslationCard(result, timeout_s=timeout, parent=None)
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
        for i, card in enumerate(reversed(visible[:-1])):
            card.move(base.x(), base.y() - (i + 1) * (base.height() + 8))

    # ── Reply ────────────────────────────────────────────────────────────────
    def _open_reply(self, result: dict):
        if not self.flash or not self.flash.ready:
            logging.warning('[MAIN] Reply requested but FLASH not ready')
            return
        reply = ReplyBox(self.flash, result, parent=None)
        reply.show()

    # ── Settings ─────────────────────────────────────────────────────────────
    def _open_settings(self):
        def on_save(new_cfg: dict):
            self.config = new_cfg
            save_config(new_cfg)
            # Apply device change if needed
            if self.flash and new_cfg.get('flash_device') != self.flash.device:
                logging.info('[MAIN] Device changed — will apply on next start')
        win = SettingsWindow(self.config, on_save, parent=None)
        win.exec()

    # ── Pause / Resume ───────────────────────────────────────────────────────
    def _on_pause_toggled(self, paused: bool):
        self._paused = paused
        if self.catch:
            if paused:
                self.catch.pause()
            else:
                self.catch.resume()

    # ── Quit ─────────────────────────────────────────────────────────────────
    def _quit(self):
        logging.info('[MAIN] Quitting')
        if self.catch:
            self.catch.stop()
        QApplication.instance().quit()


if __name__ == '__main__':
    # ── Single-instance lock ──────────────────────────────────────────────────
    os.makedirs('data', exist_ok=True)
    _lock_path = os.path.join('data', 'babelgg.lock')
    try:
        _lock_fh = open(_lock_path, 'w')
        msvcrt.locking(_lock_fh.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        # Another instance already holds the lock
        print('[MAIN] BabelGG is already running.', file=sys.stderr)
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    babelgg = BabelGG()
    babelgg.start()
    logging.info('[MAIN] Qt event loop started')
    sys.exit(app.exec())
