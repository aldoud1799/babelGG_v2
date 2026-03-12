from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui    import QIcon, QAction
from PyQt6.QtCore   import pyqtSignal, pyqtSlot, QObject
import logging


class TrayManager(QSystemTrayIcon):
    settings_requested = pyqtSignal()
    quit_requested     = pyqtSignal()
    pause_toggled      = pyqtSignal(bool)
    # (title, message, QSystemTrayIcon.MessageIcon int value)
    notify_requested   = pyqtSignal(str, str, int)

    def __init__(self, icon_path: str, parent: QObject = None):
        super().__init__(QIcon(icon_path), parent)
        self._paused = False
        self._build_menu()
        self.setToolTip('BabelGG — warming up...')
        self.show()
        logging.info('[TRAY] Icon shown')

    def _build_menu(self):
        menu = QMenu()
        self._pause_action = QAction('Pause', menu)
        self._pause_action.triggered.connect(self._toggle_pause)
        settings_action = QAction('⚙ Settings', menu)
        settings_action.triggered.connect(self.settings_requested.emit)
        quit_action = QAction('Quit BabelGG', menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(self._pause_action)
        menu.addSeparator()
        menu.addAction(settings_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.setContextMenu(menu)
        # Wire notify signal — always delivered on main Qt thread
        self.notify_requested.connect(self._show_notification)

    def _toggle_pause(self):
        self._paused = not self._paused
        self._pause_action.setText('Resume' if self._paused else 'Pause')
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
        self.setToolTip(f'BabelGG — {text}')
        logging.info(f'[TRAY] Status: {text}')
