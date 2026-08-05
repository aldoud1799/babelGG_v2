from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QApplication,
    QScrollArea, QSizePolicy, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal
from PyQt6.QtGui  import QCursor, QPainter, QColor, QPainterPath, QPen, QLinearGradient, QKeySequence, QShortcut, QAction
import time

from core.i18n import tr


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
    font-size: 15px;
    font-weight: 900;
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
}
QLabel#original {
    color: #AAAAAA;
    font-size: 11px;
    font-weight: 700;
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
}
QLabel#badge {
    color: #FFFFFF;
    font-size: 10px;
    font-weight: 900;
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 10px;
    padding: 2px 7px;
}
QLabel#heading {
    color: #666666;
    font-size: 9px;
    font-weight: 900;
    letter-spacing: 0.8px;
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
}
QPushButton#reply_btn {
    background: #E5E5E5;
    color: #000000;
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 9px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 900;
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
    min-height: 28px;
    min-width: 96px;
}
QPushButton#reply_btn:hover { background: #FFFFFF; }
QPushButton#reply_btn:pressed { background: #CCCCCC; }
QPushButton#copy_btn {
    background: #2A2A2A;
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 9px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 900;
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
    min-height: 28px;
    min-width: 74px;
}
QPushButton#copy_btn:hover { background: #3A3A3A; }
QPushButton#copy_btn:pressed { background: #1A1A1A; }
QPushButton#close_btn {
    background: transparent;
    color: #888888;
    border: none;
    font-size: 15px;
    font-weight: 900;
    padding: 0;
    min-height: 24px;
    min-width: 24px;
}
QPushButton#close_btn:hover { color: #FFFFFF; }
"""


class TranslationCard(QWidget):
    reply_requested = pyqtSignal(dict)
    closed          = pyqtSignal(int, str)

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
        self._translation_len = len(str(result.get('translation', '')))
        self._translation_text = str(result.get('translation', ''))
        self._pinned   = False
        self._drag_pos = None
        try:
            self._timeout_ms = max(0, int(timeout_s) * 1000)
        except (ValueError, TypeError):
            self._timeout_ms = 5000
        self._remaining_ms = self._timeout_ms
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.timeout.connect(self._auto_close)
        self._shown_at_ms = int(time.time() * 1000)
        self._dismissed_by = 'user_click'
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(CARD_STYLE)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_copy_menu)
        self._apply_responsive_size()
        self._build()
        self._position()
        self._bind_copy_shortcuts()
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
        path.addRoundedRect(rect, 15.0, 15.0)
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor('#1E1E1E'))
        grad.setColorAt(0.55, QColor('#1A1A1A'))
        grad.setColorAt(1.0, QColor('#141414'))
        painter.fillPath(path, grad)
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
        painter.drawPath(path)
        painter.end()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(3)

        # Row 1: flag + language + close
        top = QHBoxLayout()
        src = self.result.get('src_lang', '')[:3]
        flag = LANG_FLAGS.get(src, '\U0001F310')
        lang_lbl = QLabel(f'{flag}  {src.upper()}')
        lang_lbl.setObjectName('badge')
        close_btn = QPushButton('\u00d7')
        close_btn.setObjectName('close_btn')
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._on_close_clicked)
        top.addWidget(lang_lbl)
        top.addStretch()
        top.addWidget(close_btn)
        lay.addLayout(top)

        content_wrap = QWidget()
        content_lay = QVBoxLayout(content_wrap)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(3)

        # Row 2: original text (small, grey)
        orig = self.result.get('original', '')
        if len(orig) > 80:
            orig = orig[:80] + '...'
        if not self.compact:
            heading = QLabel('INCOMING')
            heading.setObjectName('heading')
            content_lay.addWidget(heading)

            orig_lbl = QLabel(orig)
            self._orig_lbl = orig_lbl
            orig_lbl.setObjectName('original')
            orig_lbl.setWordWrap(True)
            orig_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            orig_lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            orig_lbl.customContextMenuRequested.connect(lambda p: self._show_copy_menu(orig_lbl.mapTo(self, p)))
            content_lay.addWidget(orig_lbl)

        # Row 3: normalized hint (if slang was expanded)
        norm = self.result.get('normalized')
        if norm and not self.compact:
            norm_lbl = QLabel(f'\u2192 {norm}')
            norm_lbl.setObjectName('original')
            norm_lbl.setWordWrap(True)
            norm_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            norm_lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            norm_lbl.customContextMenuRequested.connect(lambda p: self._show_copy_menu(norm_lbl.mapTo(self, p)))
            content_lay.addWidget(norm_lbl)

        # Row 4: translation (large, white, bold)
        if not self.compact:
            translated_heading = QLabel(tr('card_translation', 'TRANSLATION'))
            translated_heading.setObjectName('heading')
            content_lay.addWidget(translated_heading)

        translation = self.result.get('translation', '')
        trans_lbl = QLabel(translation)
        self._trans_lbl = trans_lbl
        trans_lbl.setObjectName('translation')
        trans_lbl.setWordWrap(True)
        trans_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        trans_lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        trans_lbl.customContextMenuRequested.connect(lambda p: self._show_copy_menu(trans_lbl.mapTo(self, p)))
        trans_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        content_lay.addWidget(trans_lbl)

        scroll = QScrollArea()
        self._scroll = scroll
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setWidget(content_wrap)
        self._content_wrap = content_wrap
        scroll.setMaximumHeight(self._content_max_height())
        lay.addWidget(scroll)

        # Row 5: ms badge + reply button
        bot = QHBoxLayout()
        ms  = self.result.get('ms', 0)
        ms_lbl = QLabel('cached \u26a1' if ms == 0 else f'{ms}ms')
        ms_lbl.setObjectName('badge')
        copy_btn = QPushButton(tr('card_copy', 'Copy'))
        copy_btn.setObjectName('copy_btn')
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setToolTip(f"{tr('card_copy', 'Copy')} (Ctrl+C)")
        copy_btn.clicked.connect(self._copy_translation)
        reply_btn = QPushButton(f"\u21a9  {tr('card_reply', 'Reply')}")
        reply_btn.setObjectName('reply_btn')
        reply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reply_btn.clicked.connect(lambda: self.reply_requested.emit(self.result))
        bot.addWidget(ms_lbl)
        bot.addStretch()
        bot.addWidget(copy_btn)
        bot.addWidget(reply_btn)
        lay.addLayout(bot)
        self.adjustSize()
        self._fit_to_content()

    def _apply_responsive_size(self):
        screen = QApplication.primaryScreen().availableGeometry()
        if self.compact:
            # Keep compact style, but allow long messages to expand meaningfully.
            target_width = max(
                250,
                min(int(screen.width() * 0.42), int(screen.width() * 0.18) + int(self._translation_len * 0.72)),
            )
        else:
            # Scale width by translation length but cap at ~55% of screen.
            target_width = max(
                300,
                min(int(screen.width() * 0.46), int(screen.width() * 0.21) + int(self._translation_len * 0.94)),
            )
        self.resize(target_width, self.height() or 200)
        self.setMinimumWidth(max(250, int(screen.width() * 0.15)))
        self.setMaximumWidth(max(360, int(screen.width() * 0.46)))
        self.setMaximumHeight(max(240, min(720, int(screen.height() * 0.78))))

    def _content_max_height(self):
        screen = QApplication.primaryScreen().availableGeometry()
        if self.compact:
            # Compact can still be multi-line for long translations.
            return max(96, min(280, int(screen.height() * 0.32)))
        return max(130, min(380, int(screen.height() * 0.46)))

    def _fit_to_content(self):
        if not hasattr(self, '_scroll') or not hasattr(self, '_content_wrap') or not hasattr(self, '_trans_lbl'):
            return

        scroll = self._scroll
        content_wrap = self._content_wrap
        trans_lbl = self._trans_lbl
        screen = QApplication.primaryScreen().availableGeometry()

        # Recompute wrapped translation height with current width.
        wrap_width = max(190, self.width() - 48)
        rect = trans_lbl.fontMetrics().boundingRect(
            0,
            0,
            wrap_width,
            10000,
            int(Qt.TextFlag.TextWordWrap),
            self._translation_text,
        )
        trans_h = max(34, rect.height() + 8)
        trans_lbl.setMinimumHeight(trans_h)

        # Refresh layout sizes after setting translation height.
        content_wrap.layout().activate()
        content_wrap.adjustSize()

        desired_scroll_h = min(self._content_max_height(), content_wrap.sizeHint().height() + 8)
        scroll.setMinimumHeight(min(84, desired_scroll_h))
        scroll.setMaximumHeight(desired_scroll_h)

        self.layout().activate()
        self.adjustSize()
        chrome_h = 78 if self.compact else 102
        desired_h = desired_scroll_h + chrome_h
        fitted_h = min(max(170, desired_h), int(screen.height() * 0.78))
        self.resize(self.width(), fitted_h)

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
            self._dismissed_by = 'auto'
            self.close()

    def _on_close_clicked(self):
        self._dismissed_by = 'user_x'
        self.close()

    def _copy_translation(self):
        text = self._selected_text() or str(self.result.get('translation', '') or '').strip()
        if not text:
            return
        cb = QApplication.clipboard()
        cb.setText(text, mode=cb.Mode.Clipboard)

    def _selected_text(self) -> str:
        labels = [getattr(self, '_trans_lbl', None), getattr(self, '_orig_lbl', None)]
        for lbl in labels:
            if lbl is None:
                continue
            try:
                sel = str(lbl.selectedText() or '').strip()
            except Exception:
                sel = ''
            if sel:
                return sel
        return ''

    def _bind_copy_shortcuts(self):
        self._copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self)
        self._copy_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._copy_shortcut.activated.connect(self._copy_translation)

        self._copy_insert_shortcut = QShortcut(QKeySequence('Ctrl+Insert'), self)
        self._copy_insert_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._copy_insert_shortcut.activated.connect(self._copy_translation)

    def _show_copy_menu(self, pos):
        menu = QMenu(self)
        act_copy_sel = QAction('Copy Selected', menu)
        act_copy_sel.setEnabled(bool(self._selected_text()))
        act_copy_sel.triggered.connect(self._copy_translation)
        menu.addAction(act_copy_sel)

        act_copy_all = QAction('Copy Translation', menu)
        act_copy_all.triggered.connect(
            lambda: QApplication.clipboard().setText(
                str(self.result.get('translation', '') or '').strip(),
                mode=QApplication.clipboard().Mode.Clipboard,
            )
        )
        menu.addAction(act_copy_all)

        menu.exec(self.mapToGlobal(pos))

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Copy):
            self._copy_translation()
            event.accept()
            return
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Insert:
            self._copy_translation()
            event.accept()
            return
        super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def closeEvent(self, event):
        shown_ms = max(0, int(time.time() * 1000) - self._shown_at_ms)
        self.closed.emit(shown_ms, self._dismissed_by)
        # Clean up child widgets and shortcuts to prevent memory leaks
        if hasattr(self, '_copy_shortcut') and self._copy_shortcut:
            self._copy_shortcut.disconnect()
            self._copy_shortcut.deleteLater()
        if hasattr(self, '_copy_insert_shortcut') and self._copy_insert_shortcut:
            self._copy_insert_shortcut.disconnect()
            self._copy_insert_shortcut.deleteLater()
        for attr in ('_trans_lbl', '_orig_lbl', '_close_timer', '_scroll',
                     '_content_wrap', 'lang_lbl', 'close_btn', 'copy_btn', 'reply_btn',
                     'ms_lbl', 'heading', 'norm_lbl'):
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.deleteLater()
        super().closeEvent(event)