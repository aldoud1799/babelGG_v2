import sys, logging, json, os, threading

# Pre-load ML libraries before Qt — prevents DLL init conflicts on Windows
import ctranslate2  # noqa
from transformers import NllbTokenizer  # noqa: loads torch before Qt DLLs

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore    import QObject, pyqtSignal

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
from ui.card        import TranslationCard
from ui.reply       import ReplyBox
from ui.tray        import TrayManager
from ui.settings    import SettingsWindow


def load_config() -> dict:
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f'[MAIN] Config load failed: {e}')
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

        # 2. VAULT — synchronous, fast
        self.vault = TranslationVault()

        # 3. FLASH — background thread (loads model)
        self.tray.set_status('Warming FLASH engine...')
        threading.Thread(
            target=self._warm_flash, daemon=True, name='FlashWarmup'
        ).start()

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
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    babelgg = BabelGG()
    babelgg.start()
    logging.info('[MAIN] Qt event loop started')
    sys.exit(app.exec())
