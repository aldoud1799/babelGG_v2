from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QApplication,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal
from PyQt6.QtGui  import QCursor, QPainter, QColor, QPainterPath, QPen, QLinearGradient


LANG_FLAGS = {
    'jpn': '\U0001F1EF\U0001F1F5',
    'kor': '\U0001F1F0\U0001F1F7',
    'zho': '\U0001F1E8\U0001F1F3',
    'arb': '\U0001F30D',
    'tha': '\U0001F1F9\U0001F1ED',
    'rus': '\U0001F1F7\U0001F1FA',
    'fra': '\U0001F1EB\U0001F1F7',
    'spa': '\U0001F1EA\U0001F1F8',
    'deu': '\U0001F1E9\U0001F1EA',
    'por': '\U0001F1F5\U0001F1F9',
    'vie': '\U0001F1FB\U0001F1F3',
    'ind': '\U0001F1EE\U0001F1E9',
    'tur': '\U0001F1F9\U0001F1F7',
    'eng': '\U0001F1FA\U0001F1F8',
}

CARD_STYLE = """
QLabel#translation {
    color: #FFFFFF;
    font-size: 17px;
    font-weight: 800;
    font-family: 'Segoe UI Semibold';
}
QLabel#original {
    color: #A7B4CB;
    font-size: 12px;
    font-family: 'Segoe UI';
}
QLabel#badge {
    color: #93FFF1;
    font-size: 11px;
    font-weight: 700;
    font-family: 'Segoe UI Semibold';
    background: rgba(0, 194, 168, 0.15);
    border: 1px solid rgba(0, 194, 168, 0.45);
    border-radius: 10px;
    padding: 2px 8px;
}
QLabel#heading {
    color: #C8F7EE;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    font-family: 'Segoe UI Semibold';
}
QPushButton#reply_btn {
    background: #00C2A8;
    color: #051A22;
    border: none;
    border-radius: 9px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 800;
    font-family: 'Segoe UI Semibold';
}
QPushButton#reply_btn:hover { background: #1BE6CC; color: #041419; }
QPushButton#reply_btn:pressed { background: #00A895; }
QPushButton#close_btn {
    background: transparent;
    color: #9FB6CC;
    border: none;
    font-size: 16px;
    font-weight: 700;
    padding: 0;
}
QPushButton#close_btn:hover { color: #FFFFFF; }
"""


class TranslationCard(QWidget):
    reply_requested = pyqtSignal(dict)
    closed          = pyqtSignal()

    def __init__(
            self,
            result: dict,
            timeout_s: int = 5,
            anchor: str = 'bottom_right',
            compact: bool = False,
            parent=None,
    ):
        super().__init__(parent)
        self.result    = result
        self.anchor    = str(anchor or 'bottom_right').lower()
        self.compact   = bool(compact)
        self._pinned   = False
        self._drag_pos = None
        self._timeout_ms = max(0, timeout_s * 1000)
        self._remaining_ms = self._timeout_ms
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.timeout.connect(self._auto_close)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(CARD_STYLE)
        self._apply_responsive_size()
        self._build()
        self._position()
        if self._timeout_ms > 0:
            self._close_timer.start(self._timeout_ms)

    def paintEvent(self, event):
        """Draw the dark rounded background manually.
        WA_TranslucentBackground + QWidget stylesheet background is unreliable
        on Windows - text would float over whatever is behind the window."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 12.0, 12.0)
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor('#151A35'))
        grad.setColorAt(0.55, QColor('#11172F'))
        grad.setColorAt(1.0, QColor('#0D1124'))
        painter.fillPath(path, grad)
        painter.setPen(QPen(QColor('#20D8BE'), 1.1))
        painter.drawPath(path)
        painter.end()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        # Row 1: flag + language + close
        top = QHBoxLayout()
        src = self.result.get('src_lang', '')[:3]
        flag = LANG_FLAGS.get(src, '\U0001F310')
        lang_lbl = QLabel(f'{flag}  {src.upper()}')
        lang_lbl.setObjectName('badge')
        close_btn = QPushButton('\u00d7')
        close_btn.setObjectName('close_btn')
        close_btn.setFixedSize(22, 22)
        close_btn.clicked.connect(self.close)
        top.addWidget(lang_lbl)
        top.addStretch()
        top.addWidget(close_btn)
        lay.addLayout(top)

        content_wrap = QWidget()
        content_lay = QVBoxLayout(content_wrap)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(4)

        # Row 2: original text (small, grey)
        orig = self.result.get('original', '')
        if len(orig) > 80:
            orig = orig[:80] + '...'
        if not self.compact:
            heading = QLabel('INCOMING')
            heading.setObjectName('heading')
            content_lay.addWidget(heading)

            orig_lbl = QLabel(orig)
            orig_lbl.setObjectName('original')
            orig_lbl.setWordWrap(True)
            orig_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            content_lay.addWidget(orig_lbl)

        # Row 3: normalized hint (if slang was expanded)
        norm = self.result.get('normalized')
        if norm and not self.compact:
            norm_lbl = QLabel(f'\u2192 {norm}')
            norm_lbl.setObjectName('original')
            norm_lbl.setWordWrap(True)
            norm_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            content_lay.addWidget(norm_lbl)

        # Row 4: translation (large, white, bold)
        if not self.compact:
            translated_heading = QLabel('TRANSLATION')
            translated_heading.setObjectName('heading')
            content_lay.addWidget(translated_heading)

        translation = self.result.get('translation', '')
        if self.compact and len(translation) > 90:
            translation = translation[:90].rstrip() + '...'
        trans_lbl = QLabel(translation)
        trans_lbl.setObjectName('translation')
        trans_lbl.setWordWrap(True)
        trans_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        trans_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        content_lay.addWidget(trans_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setWidget(content_wrap)
        scroll.setMaximumHeight(self._content_max_height())
        lay.addWidget(scroll)

        # Row 5: ms badge + reply button
        bot = QHBoxLayout()
        ms  = self.result.get('ms', 0)
        ms_lbl = QLabel('cached \u26a1' if ms == 0 else f'{ms}ms')
        ms_lbl.setObjectName('badge')
        reply_btn = QPushButton('\u21a9  Reply')
        reply_btn.setObjectName('reply_btn')
        reply_btn.clicked.connect(lambda: self.reply_requested.emit(self.result))
        bot.addWidget(ms_lbl)
        bot.addStretch()
        bot.addWidget(reply_btn)
        lay.addLayout(bot)
        self.adjustSize()

    def _apply_responsive_size(self):
        screen = QApplication.primaryScreen().availableGeometry()
        if self.compact:
            target_width = max(290, min(380, int(screen.width() * 0.24)))
        else:
            target_width = max(320, min(460, int(screen.width() * 0.28)))
        self.setFixedWidth(target_width)
        self.setMaximumHeight(max(220, min(520, int(screen.height() * 0.55))))

    def _content_max_height(self):
        screen = QApplication.primaryScreen().availableGeometry()
        if self.compact:
            return max(64, min(110, int(screen.height() * 0.12)))
        return max(110, min(300, int(screen.height() * 0.32)))

    def _position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        margin = 18

        if self.anchor == 'top_left':
            x = screen.left() + margin
            y = screen.top() + margin
        elif self.anchor == 'top_right':
            x = screen.right() - self.width() - margin
            y = screen.top() + margin
        elif self.anchor == 'bottom_left':
            x = screen.left() + margin
            y = screen.bottom() - self.height() - margin
        elif self.anchor == 'bottom_right':
            x = screen.right() - self.width() - margin
            y = screen.bottom() - self.height() - margin
        else:
            # Fallback to cursor-relative behavior for unknown anchors.
            pos = QCursor.pos()
            x = pos.x() + 16
            y = pos.y() + 8
            if x + self.width() > screen.right():
                x = pos.x() - self.width() - 8
            if y + self.height() > screen.bottom():
                y = pos.y() - self.height() - 8
        self.move(x, y)

    def mousePressEvent(self, event):
        self._pinned   = True
        self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def enterEvent(self, event):
        if self._close_timer.isActive():
            self._remaining_ms = max(1, self._close_timer.remainingTime())
            self._close_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._pinned and self._timeout_ms > 0 and not self._close_timer.isActive():
            self._close_timer.start(max(1, self._remaining_ms))
        super().leaveEvent(event)

    def _auto_close(self):
        if not self._pinned:
            self.close()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)