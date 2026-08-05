from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QScrollArea, QWidget, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QPalette, QColor
import logging, pyperclip

from core.i18n import tr


HISTORY_STYLE = """
QDialog {
    background: #141414;
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
}
QListWidget {
    background: #1E1E1E;
    color: #FFFFFF;
    border: 1px solid #3A3A3A;
    border-radius: 8px;
    outline: none;
}
QListWidget::item {
    padding: 6px 8px;
    border: none;
}
QListWidget::item:selected {
    background: #2A2A2A;
    color: #FFFFFF;
}
QListWidget::item:hover {
    background: #262626;
}
QPushButton {
    background: #E5E5E5;
    color: #000000;
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 700;
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
}
QPushButton:hover { background: #FFFFFF; }
QPushButton:pressed { background: #CCCCCC; }
"""


class HistoryDialog(QDialog):
    def __init__(self, vault, license_mgr, parent=None):
        super().__init__(parent)
        self._vault = vault
        self._license = license_mgr
        self._is_pro = license_mgr.check('history')
        self.setWindowTitle(tr('tray_history', 'Translation History'))
        self.setMinimumSize(540, 420)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(HISTORY_STYLE)
        self._build_ui()
        self._load_history()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

        footer = QHBoxLayout()
        footer.addStretch()

        self._clear_btn = QPushButton(tr('history_clear', 'Clear History'))
        self._clear_btn.clicked.connect(self._on_clear)
        footer.addWidget(self._clear_btn)

        close_btn = QPushButton(tr('common_close', 'Close'))
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)

        layout.addLayout(footer)

    def _load_history(self):
        entries = self._vault.recent(limit=50)
        if not entries:
            item = QListWidgetItem(tr('history_empty', 'No translations yet'))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(item)
            return

        for entry in entries:
            src = entry.get('original', '')
            tgt = entry.get('translation', '')
            target = entry.get('target', '')
            label = f'{src!r}  →  {tgt!r}  [{target}]'
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self._list.addItem(item)

    def _on_item_clicked(self, item):
        entry = item.data(Qt.ItemDataRole.UserRole)
        if not entry:
            return
        translation = entry.get('translation', '')
        if translation:
            try:
                pyperclip.copy(translation)
                logging.info('[HISTORY] Copied to clipboard')
            except Exception as e:
                logging.warning('[HISTORY] Clipboard copy failed: %s', e)

    def _on_clear(self):
        self._vault.invalidate_all()
        self._list.clear()
        self._list.addItem(tr('history_empty', 'No translations yet'))
