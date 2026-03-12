from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
import logging, pyperclip


REPLY_STYLE = """
QWidget {
    background: #0F3460;
    border: 1px solid #00C2A8;
    border-radius: 10px;
}
QTextEdit {
    background: #1A1A2E;
    color: #FFFFFF;
    border: 1px solid #2D3748;
    border-radius: 6px;
    font-size: 13px;
    padding: 6px;
}
QLabel#hint    { color: #94A3B8; font-size: 11px; padding: 2px; }
QLabel#preview { color: #00C2A8; font-size: 13px; padding: 4px; font-weight: bold; }
QPushButton#send {
    background: #00C2A8; color: #000;
    border-radius: 6px; padding: 6px 14px;
    font-weight: bold; font-size: 12px;
}
QPushButton#send:hover { background: #00A896; }
QPushButton#cancel {
    background: transparent; color: #64748B;
    border: 1px solid #2D3748; border-radius: 6px;
    padding: 6px 14px; font-size: 12px;
}
"""


class ReplyBox(QWidget):
    sent = pyqtSignal(str)   # emits translated text when user clicks send

    def __init__(self, flash, original_result: dict, parent=None):
        super().__init__(parent)
        self.flash          = flash
        self._tgt_lang_code = original_result.get('src_lang', 'jpn_Jpan')
        self._tgt_lang_name = original_result.get('src_lang', 'jpn')[:3].upper()
        self._pending       = ''
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(REPLY_STYLE)
        self.setFixedWidth(320)
        self._build()
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._update_preview)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)
        hint = QLabel(f'Type your reply — will be translated to {self._tgt_lang_name}')
        hint.setObjectName('hint')
        hint.setWordWrap(True)
        lay.addWidget(hint)
        self._input = QTextEdit()
        self._input.setFixedHeight(64)
        self._input.setPlaceholderText('gg wp, good game...')
        self._input.textChanged.connect(lambda: self._debounce.start(500))
        lay.addWidget(self._input)
        self._preview_lbl = QLabel('Translation will appear here...')
        self._preview_lbl.setObjectName('preview')
        self._preview_lbl.setWordWrap(True)
        lay.addWidget(self._preview_lbl)
        btns   = QHBoxLayout()
        cancel = QPushButton('Cancel')
        cancel.setObjectName('cancel')
        cancel.clicked.connect(self.close)
        send = QPushButton('Copy & Send →')
        send.setObjectName('send')
        send.clicked.connect(self._send)
        btns.addWidget(cancel)
        btns.addStretch()
        btns.addWidget(send)
        lay.addLayout(btns)
        self.adjustSize()

    def _update_preview(self):
        from core.slang import normalize_for_translation
        text = self._input.toPlainText().strip()
        if not text:
            self._preview_lbl.setText('Translation will appear here...')
            return
        if not self.flash:
            return
        try:
            clean, _ = normalize_for_translation(text)
            # Find target language name from code
            tgt_name = next(
                (name for name, code in self.flash.LANG_CODES.items()
                 if code == self._tgt_lang_code),
                'japanese'
            )
            result = self.flash.translate(clean, tgt_name)
            if result:
                self._pending = result['translation']
                self._preview_lbl.setText(self._pending)
        except Exception as e:
            logging.error(f'[REPLY] Preview failed: {type(e).__name__}: {e}')

    def _send(self):
        if not self._pending:
            return
        try:
            pyperclip.copy(self._pending)
            logging.info(f'[REPLY] Copied: {self._pending[:60]}')
            self.sent.emit(self._pending)
            self.close()
        except Exception as e:
            logging.error(f'[REPLY] Send failed: {e}')
