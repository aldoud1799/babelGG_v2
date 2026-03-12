from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui    import QIcon, QAction
from PyQt6.QtCore   import pyqtSignal, QObject
import logging


class TrayManager(QSystemTrayIcon):
    settings_requested = pyqtSignal()
    quit_requested     = pyqtSignal()
    pause_toggled      = pyqtSignal(bool)

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

    def _toggle_pause(self):
        self._paused = not self._paused
        self._pause_action.setText('Resume' if self._paused else 'Pause')
        self.pause_toggled.emit(self._paused)
        logging.info(f'[TRAY] {"Paused" if self._paused else "Resumed"}')

    def set_status(self, text: str):
        self.setToolTip(f'BabelGG — {text}')
        logging.info(f'[TRAY] Status: {text}')
