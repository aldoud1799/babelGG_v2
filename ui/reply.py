from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
import logging, pyperclip


REPLY_STYLE = """
QWidget {
    background: #101A38;
    border: 1px solid #20D8BE;
    border-radius: 12px;
}
QTextEdit {
    background: #0D142B;
    color: #FFFFFF;
    border: 1px solid #334668;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    font-family: 'Segoe UI Semibold';
    padding: 8px;
}
QLabel#title {
    color: #E7F4FF;
    font-size: 14px;
    font-weight: 800;
    font-family: 'Segoe UI Semibold';
    padding: 0px 2px;
}
QLabel#hint {
    color: #B3C4DD;
    font-size: 11px;
    font-weight: 600;
    padding: 0px 2px;
}
QLabel#preview {
    color: #8AF6E5;
    font-size: 13px;
    padding: 6px 4px;
    font-weight: 800;
    font-family: 'Segoe UI Semibold';
}
QPushButton#send {
    background: #00C2A8;
    color: #03171F;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 800;
    font-size: 12px;
    font-family: 'Segoe UI Semibold';
}
QPushButton#send:hover { background: #20E1C9; }
QPushButton#send:pressed { background: #00A693; }
QPushButton#cancel {
    background: transparent;
    color: #9DB1CA;
    border: 1px solid #425477;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#cancel:hover {
    color: #D5E5F7;
    border-color: #5D759E;
}
"""


class ReplyBox(QWidget):
    sent = pyqtSignal(str)   # emits translated text when user clicks send

    def __init__(self, flash, original_result: dict, compact: bool = False, parent=None):
        super().__init__(parent)
        self.flash          = flash
        self.compact        = bool(compact)
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
        self.setFixedWidth(292 if self.compact else 320)
        self._build()
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._update_preview)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(5 if self.compact else 6)

        if not self.compact:
            title = QLabel('Reply Composer')
            title.setObjectName('title')
            lay.addWidget(title)

        hint_txt = (f'→ {self._tgt_lang_name}' if self.compact
                    else f'Type your reply — will be translated to {self._tgt_lang_name}')
        hint = QLabel(hint_txt)
        hint.setObjectName('hint')
        hint.setWordWrap(True)
        lay.addWidget(hint)
        self._input = QTextEdit()
        self._input.setFixedHeight(54 if self.compact else 72)
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
                preview = self._pending
                if self.compact and len(preview) > 62:
                    preview = preview[:62].rstrip() + '...'
                self._preview_lbl.setText(preview)
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
