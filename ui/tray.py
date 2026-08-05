from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui    import QIcon, QAction
from PyQt6.QtCore   import pyqtSignal, pyqtSlot, QObject
import logging

from core.i18n import normalize_app_language, tr


class TrayManager(QSystemTrayIcon):
    settings_requested = pyqtSignal()
    upgrade_requested  = pyqtSignal()
    history_requested  = pyqtSignal()
    quit_requested     = pyqtSignal()
    pause_toggled      = pyqtSignal(bool)
    # (title, message, QSystemTrayIcon.MessageIcon int value)
    notify_requested   = pyqtSignal(str, str, int)

    def __init__(self, icon_path: str, app_language: str = 'english', parent: QObject = None):
        super().__init__(QIcon(icon_path), parent)
        self._paused = False
        self._is_pro = False
        self._app_language = normalize_app_language(app_language)
        self._build_menu()
        self.setToolTip(f"BabelGG - {tr('status_warming_flash', 'Warming FLASH engine...', lang=self._app_language)}")
        self.show()
        logging.info('[TRAY] Icon shown')

    def _build_menu(self):
        menu = QMenu()
        self._pause_action = QAction('', menu)
        self._pause_action.triggered.connect(self._toggle_pause)
        self._settings_action = QAction('', menu)
        self._settings_action.triggered.connect(self.settings_requested.emit)
        self._history_action = QAction('', menu)
        self._history_action.triggered.connect(self.history_requested.emit)
        self._upgrade_action = QAction('', menu)
        self._upgrade_action.triggered.connect(self.upgrade_requested.emit)
        self._quit_action = QAction('', menu)
        self._quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(self._pause_action)
        menu.addSeparator()
        menu.addAction(self._settings_action)
        menu.addAction(self._history_action)
        menu.addAction(self._upgrade_action)
        menu.addSeparator()
        menu.addAction(self._quit_action)
        self.setContextMenu(menu)
        # Wire notify signal — always delivered on main Qt thread
        self.notify_requested.connect(self._show_notification)
        self.set_pro_status(False)
        self._refresh_labels()

    def _refresh_labels(self):
        self._pause_action.setText(
            tr('tray_resume', 'Resume', lang=self._app_language)
            if self._paused
            else tr('tray_pause', 'Pause', lang=self._app_language)
        )
        self._settings_action.setText(f"⚙ {tr('tray_settings', 'Settings', lang=self._app_language)}")
        self._quit_action.setText(tr('tray_quit', 'Quit BabelGG', lang=self._app_language))
        self._history_action.setText(
            tr('tray_history', 'Translation History', lang=self._app_language)
            if self._is_pro
            else f"🔒 {tr('tray_history_locked', 'Locked Translation History', lang=self._app_language)}"
        )
        self._upgrade_action.setText(f"🔒 {tr('tray_upgrade', 'Upgrade to Pro', lang=self._app_language)}")

    def _toggle_pause(self):
        self._paused = not self._paused
        self._refresh_labels()
        self.pause_toggled.emit(self._paused)
        logging.info(f'[TRAY] {"Paused" if self._paused else "Resumed"}')

    def toggle_pause(self):
        """Public entry-point used by hotkeys (must be called on main thread)."""
        self._toggle_pause()

    @pyqtSlot(str, str, int)
    def _show_notification(self, title: str, message: str, icon_int: int):
        icon = QSystemTrayIcon.MessageIcon(icon_int)
        self.showMessage(title, message, icon, 8000)
        logging.info(f'[TRAY] Notification: {title} — {message}')

    def set_status(self, text: str):
        prefix = 'BabelGG Pro' if self._is_pro else 'BabelGG'
        self.setToolTip(f'{prefix} — {text}')
        logging.info(f'[TRAY] Status: {text}')

    def set_pro_status(self, is_pro: bool):
        self._is_pro = bool(is_pro)
        self._upgrade_action.setVisible(not self._is_pro)
        self._refresh_labels()
        state = 'Pro' if self._is_pro else 'Free'
        logging.info(f'[TRAY] License state: {state}')

    def set_language(self, app_language: str):
        self._app_language = normalize_app_language(app_language)
        self._refresh_labels()
