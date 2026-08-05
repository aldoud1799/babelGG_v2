from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QEvent, pyqtSignal, QRectF, QPoint
from PyQt6.QtGui import QKeyEvent, QTextCursor, QPainter, QColor, QPainterPath, QPen, QLinearGradient, QFont, QPalette, QCursor, QGuiApplication
import logging, pyperclip
import re

from core.i18n import tr


def preview_label_style(font_px: int) -> str:
    return (
        "color: #FFFFFF;"
        f"font-size: {font_px}px;"
        "padding: 6px 8px;"
        "font-weight: 700;"
        "font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;"
        "background: rgba(30, 30, 30, 0.9);"
        "border: 1px solid rgba(255, 255, 255, 0.15);"
        "border-radius: 8px;"
    )


REPLY_STYLE = """
QWidget#reply_root {
    background: transparent;
    border: none;
}
QTextEdit {
    background: rgba(20, 20, 20, 0.95);
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
    padding: 7px;
    selection-background-color: rgba(255, 255, 255, 0.2);
}
QTextEdit[transparent='true'] {
    background: rgba(20, 20, 20, 0.8);
}
QLabel#title {
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 700;
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
    padding: 0px 2px;
}
QLabel#hint {
    color: #AAAAAA;
    font-size: 10px;
    font-weight: 600;
    padding: 0px 2px;
}
QLabel#preview {
    color: #FFFFFF;
    font-size: 11px;
    padding: 6px 8px;
    font-weight: 700;
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
    background: rgba(30, 30, 30, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
}
QComboBox {
    background: rgba(20, 20, 20, 0.9);
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    padding: 3px 7px;
    font-size: 11px;
    font-weight: 700;
    min-width: 108px;
}
QComboBox:hover {
    border-color: rgba(255, 255, 255, 0.5);
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QPushButton#send {
    background: rgba(229, 229, 229, 0.9);
    color: #000000;
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 8px;
    padding: 4px 10px;
    font-weight: 900;
    font-size: 11px;
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
    min-height: 24px;
    min-width: 78px;
}
QPushButton#send:hover { background: #FFFFFF; }
QPushButton#send:pressed { background: #CCCCCC; }
QPushButton#cancel {
    background: rgba(50, 50, 50, 0.8);
    color: #AAAAAA;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 900;
    min-height: 24px;
    min-width: 58px;
}
QPushButton#cancel:hover {
    color: #FFFFFF;
    border-color: rgba(255, 255, 255, 0.4);
}
"""


class ReplyBox(QWidget):
    sent = pyqtSignal(str)   # emits translated text when user clicks send
    opened = pyqtSignal(str) # emits target src language code when reply opens

    def __init__(self, flash, original_result: dict | None = None, compact: bool = False, default_tgt_lang_code: str = 'jpn_Jpan', parent=None):
        super().__init__(parent)
        self.setObjectName('reply_root')
        self.flash          = flash
        self.compact        = bool(compact)
        self._tgt_lang_code = (original_result or {}).get('src_lang', default_tgt_lang_code)
        self._tgt_lang_name = str(self._tgt_lang_code)[:3].upper()
        self._pending       = ''
        self._pending_src   = ''
        self._last_preview_lang = ''
        self._preview_font_sizes = [11, 10, 9]
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(REPLY_STYLE)
        self.setMinimumWidth(248 if self.compact else 280)
        self.resize(260 if self.compact else 292, 138 if self.compact else 154)
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._update_preview)
        self._focus_retry_intervals_ms = (0, 110, 240, 420)
        self._auto_close_armed = False
        self._drag_offset: QPoint | None = None
        self._dragging = False
        self._draggable_widgets: tuple[QWidget, ...] = tuple()
        self._build()

    def _place_near_cursor(self):
        try:
            pos = QCursor.pos()
            screens = QGuiApplication.screens()
            if not screens:
                self.move(pos.x() + 14, pos.y() + 14)
                return

            screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
            if screen is None:
                self.move(pos.x() + 14, pos.y() + 14)
                return

            geom = screen.availableGeometry()
            pad = 10
            x = pos.x() + 14
            y = pos.y() + 16

            if x + self.width() > geom.right() - pad:
                x = pos.x() - self.width() - 14
            if y + self.height() > geom.bottom() - pad:
                y = pos.y() - self.height() - 16

            x = max(geom.left() + pad, min(x, geom.right() - self.width() - pad))
            y = max(geom.top() + pad, min(y, geom.bottom() - self.height() - pad))
            self.move(x, y)
        except Exception as e:
            logging.warning(f'[REPLY] Cursor placement failed: {type(e).__name__}: {e}')

    def _activate_foreground(self):
        self.raise_()
        self.activateWindow()

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            SW_SHOW = 5
            HWND_TOPMOST = -1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_SHOWWINDOW = 0x0040

            # Keep reply window always-on-top while visible.
            user32.ShowWindow(wintypes.HWND(hwnd), SW_SHOW)
            user32.SetWindowPos(
                wintypes.HWND(hwnd),
                wintypes.HWND(HWND_TOPMOST),
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW,
            )

            # Some fullscreen games clip the cursor to the game window. Release it for reply input.
            user32.ClipCursor(None)

            fg_hwnd = user32.GetForegroundWindow()
            if fg_hwnd:
                current_tid = user32.GetCurrentThreadId()
                target_tid = user32.GetWindowThreadProcessId(wintypes.HWND(fg_hwnd), None)
                if target_tid and target_tid != current_tid:
                    user32.AttachThreadInput(current_tid, target_tid, True)
                    try:
                        user32.BringWindowToTop(wintypes.HWND(hwnd))
                        user32.SetForegroundWindow(wintypes.HWND(hwnd))
                    finally:
                        user32.AttachThreadInput(current_tid, target_tid, False)
                else:
                    user32.BringWindowToTop(wintypes.HWND(hwnd))
                    user32.SetForegroundWindow(wintypes.HWND(hwnd))
            else:
                user32.BringWindowToTop(wintypes.HWND(hwnd))
                user32.SetForegroundWindow(wintypes.HWND(hwnd))
        except Exception as e:
            logging.debug(f'[REPLY] Foreground activation fallback: {type(e).__name__}: {e}')

    def _is_cjk_text(self, text: str) -> bool:
        for ch in text:
            cp = ord(ch)
            if (
                0x3040 <= cp <= 0x30FF  # Japanese kana
                or 0x4E00 <= cp <= 0x9FFF  # CJK ideographs
                or 0xAC00 <= cp <= 0xD7A3  # Hangul
            ):
                return True
        return False

    def _norm_compare(self, text: str) -> str:
        t = (text or '').strip().lower()
        t = re.sub(r'\s+', ' ', t)
        # Ignore trivial punctuation-only differences for "same text" checks.
        t = re.sub(r'[\s\.,!?;:\-\'"`~]+', '', t)
        return t

    def _has_target_script(self, text: str, tgt_code: str) -> bool:
        ranges = {
            'jpn_Jpan': [(0x3040, 0x30FF), (0x4E00, 0x9FFF)],
            'kor_Hang': [(0xAC00, 0xD7A3), (0x1100, 0x11FF)],
            'zho_Hans': [(0x4E00, 0x9FFF)],
            'arb_Arab': [(0x0600, 0x06FF), (0x0750, 0x077F)],
            'tha_Thai': [(0x0E00, 0x0E7F)],
            'rus_Cyrl': [(0x0400, 0x04FF)],
        }
        rr = ranges.get(tgt_code)
        if not rr:
            return True
        for ch in (text or ''):
            cp = ord(ch)
            for lo, hi in rr:
                if lo <= cp <= hi:
                    return True
        return False

    def _looks_untranslated(self, src_text: str, translated: str) -> bool:
        src = (src_text or '').strip()
        out = (translated or '').strip()
        if not out:
            return True

        # Same-text checks should be resilient to case/punctuation drift.
        if self._norm_compare(src) == self._norm_compare(out):
            return True

        # For non-Latin target scripts, require visible target script signal.
        if not self._has_target_script(out, self._tgt_lang_code):
            return True

        return False

    def _debounce_ms_for_text(self, text: str) -> int:
        t = text or ''
        stripped = t.strip()
        if not stripped:
            return 120

        n = len(stripped)
        ends_word = t.endswith((' ', '.', ',', '!', '?', ';', ':', '\n', '\t'))

        if self._is_cjk_text(stripped):
            # CJK inputs are often meaningful at shorter lengths.
            ms = 210 if n <= 1 else 170
        else:
            # Latin typing benefits from stronger debounce on very short inputs.
            if n <= 1:
                ms = 380
            elif n <= 3:
                ms = 300
            elif n <= 8:
                ms = 240
            else:
                ms = 180

        if ends_word:
            ms = max(140, ms - 60)
        return ms

    def _schedule_preview_update(self, force_ms: int | None = None):
        if not hasattr(self, '_input'):
            return
        text = self._input.toPlainText()
        delay_ms = int(force_ms) if force_ms is not None else self._debounce_ms_for_text(text)
        self._debounce.start(max(80, delay_ms))

    def _on_input_changed(self):
        self._schedule_preview_update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect().adjusted(0, 0, -1, -1))
        path = QPainterPath()
        path.addRoundedRect(rect, 12.0, 12.0)

        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QColor(30, 30, 30, 230))
        gradient.setColorAt(0.55, QColor(26, 26, 26, 218))
        gradient.setColorAt(1.0, QColor(20, 20, 20, 226))
        painter.fillPath(path, gradient)

        painter.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
        painter.drawPath(path)

        inner = rect.adjusted(1.0, 1.0, -1.0, -1.0)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner, 11.0, 11.0)
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        painter.drawPath(inner_path)
        painter.end()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)

        lang_row = QHBoxLayout()
        lang_label = QLabel(tr('reply_language', 'Reply language'))
        lang_label.setObjectName('hint')
        self._lang_combo = QComboBox()
        self._populate_language_combo()
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(lang_label)
        lang_row.addStretch()
        lang_row.addWidget(self._lang_combo)
        lay.addLayout(lang_row)

        if not self.compact:
            title = QLabel(tr('reply_composer', 'Reply Composer'))
            title.setObjectName('title')
            lay.addWidget(title)
            self._title_lbl = title
        else:
            self._title_lbl = None

        hint_txt = (
            tr('reply_hint_compact', '-> {target}', target=self._tgt_lang_name)
            if self.compact
            else tr('reply_hint', 'Type your reply - will be translated to {target}', target=self._tgt_lang_name)
        )
        hint = QLabel(hint_txt)
        hint.setObjectName('hint')
        hint.setWordWrap(True)
        self._hint_lbl = hint
        lay.addWidget(hint)
        self._input = QTextEdit()
        self._input.setProperty('transparent', True)
        self._input.setMinimumHeight(44 if self.compact else 52)
        self._input.setMaximumHeight(66 if self.compact else 74)
        self._input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._input.setPlaceholderText(tr('reply_placeholder', 'gg wp, good game...'))
        input_palette = self._input.palette()
        input_palette.setColor(QPalette.ColorRole.Text, QColor('#F4F7FF'))
        input_palette.setColor(QPalette.ColorRole.PlaceholderText, QColor('#96A6C8'))
        input_palette.setColor(QPalette.ColorRole.Base, QColor(12, 19, 35, 210))
        self._input.setPalette(input_palette)
        self._input.textChanged.connect(self._on_input_changed)
        self._input.installEventFilter(self)
        self._input.style().unpolish(self._input)
        self._input.style().polish(self._input)
        lay.addWidget(self._input)

        self._preview_box = QWidget()
        preview_box_lay = QVBoxLayout(self._preview_box)
        preview_box_lay.setContentsMargins(0, 0, 0, 0)
        preview_box_lay.setSpacing(0)
        self._preview_lbl = QLabel(tr('reply_preview_empty', 'Translation will appear here...'))
        self._preview_lbl.setObjectName('preview')
        self._preview_lbl.setWordWrap(True)
        self._set_preview_font_size(self._preview_font_sizes[0])
        preview_box_lay.addWidget(self._preview_lbl)
        lay.addWidget(self._preview_box)
        self._preview_box.hide()

        btns   = QHBoxLayout()
        btns.setSpacing(6)
        cancel = QPushButton(tr('reply_cancel', 'Cancel'))
        self._cancel_btn = cancel
        cancel.setObjectName('cancel')
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        cancel.clicked.connect(self.close)
        send = QPushButton(tr('reply_send', 'Copy and Send ->'))
        send.setObjectName('send')
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._send_btn = send
        send.clicked.connect(self._send)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(send)
        lay.addLayout(btns)

        draggable = [self, self._hint_lbl, self._preview_box, self._preview_lbl]
        if self._title_lbl is not None:
            draggable.append(self._title_lbl)
        self._draggable_widgets = tuple(draggable)
        for widget in self._draggable_widgets:
            widget.installEventFilter(self)

        self._apply_compact_geometry()

    def _preview_height_for_text(self, text: str) -> int:
        available_width = max(160, self.width() - 24)
        metrics = self._preview_lbl.fontMetrics()
        rect = metrics.boundingRect(0, 0, available_width, 1000, int(Qt.TextFlag.TextWordWrap), text)
        min_height = 18
        max_height = 78 if self.compact else 120
        return max(min_height, min(rect.height() + 6, max_height))

    def _preview_width_bounds(self) -> tuple[int, int]:
        return ((260, 420) if self.compact else (292, 520))

    def _preview_height_limits(self) -> tuple[int, int]:
        return ((38, 96) if self.compact else (52, 132))

    def _set_preview_font_size(self, point_size: int):
        font = QFont(self._preview_lbl.font())
        font.setPixelSize(point_size)
        self._preview_lbl.setFont(font)
        self._preview_lbl.setStyleSheet(preview_label_style(point_size))

    def _measure_preview_height(self, text: str, widget_width: int, point_size: int) -> int:
        font = QFont(self._preview_lbl.font())
        font.setPixelSize(point_size)
        metrics = self._preview_lbl.fontMetrics() if self._preview_lbl.font().pixelSize() == point_size else None
        if metrics is None:
            from PyQt6.QtGui import QFontMetrics
            metrics = QFontMetrics(font)
        available_width = max(150, widget_width - 24)
        rect = metrics.boundingRect(0, 0, available_width, 2000, int(Qt.TextFlag.TextWordWrap), text)
        return max(18, rect.height() + 8)

    def _resolve_preview_layout(self, text: str) -> tuple[int, int, int]:
        base_width, max_width = self._preview_width_bounds()
        preferred_height, max_height = self._preview_height_limits()
        width_steps = [base_width, min(max_width, base_width + 36), min(max_width, base_width + 72), max_width]
        width_steps = list(dict.fromkeys(width_steps))

        for point_size in self._preview_font_sizes:
            for width in width_steps:
                height = self._measure_preview_height(text, width, point_size)
                if height <= preferred_height:
                    return width, height, point_size

            max_width_height = self._measure_preview_height(text, max_width, point_size)
            if max_width_height <= max_height:
                return max_width, max_width_height, point_size

        fallback_font = self._preview_font_sizes[-1]
        fallback_height = min(max_height, self._measure_preview_height(text, max_width, fallback_font))
        return max_width, fallback_height, fallback_font

    def _apply_compact_geometry(self):
        preview_text = self._preview_lbl.text().strip()
        empty_preview = tr('reply_preview_empty', 'Translation will appear here...')
        has_preview = bool(self._pending and preview_text and preview_text != empty_preview)
        self._preview_box.setVisible(has_preview)
        if has_preview:
            target_width, preview_height, font_size = self._resolve_preview_layout(preview_text)
            self._set_preview_font_size(font_size)
            self.resize(target_width, self.height())
            self._preview_lbl.setFixedHeight(preview_height)
        else:
            self._set_preview_font_size(self._preview_font_sizes[0])
        base_height = 124 if self.compact else 140
        target_height = base_height + (self._preview_lbl.height() if has_preview else 0)
        max_height = 220 if self.compact else 270
        base_width, _ = self._preview_width_bounds()
        target_width = self.width() if has_preview else base_width
        self.resize(target_width, min(target_height, max_height))

    def showEvent(self, event):
        super().showEvent(event)
        self._auto_close_armed = False
        self.opened.emit(self._tgt_lang_code)
        self._place_near_cursor()
        # Delay long enough for hotkey release, then retry activation to survive focus contention.
        for delay in self._focus_retry_intervals_ms:
            QTimer.singleShot(delay, self.focus_input)
        QTimer.singleShot(max(self._focus_retry_intervals_ms) + 180, self._arm_auto_close)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() != QEvent.Type.ActivationChange:
            return
        if not self._auto_close_armed or not self.isVisible() or self._dragging:
            return
        if self.isActiveWindow():
            return
        QTimer.singleShot(0, self._close_if_deactivated)

    def _arm_auto_close(self):
        if self.isVisible():
            self._auto_close_armed = True

    def _close_if_deactivated(self):
        if not self._auto_close_armed or not self.isVisible() or self.isActiveWindow() or self._dragging:
            return
        if hasattr(self, '_lang_combo') and self._lang_combo.view().isVisible():
            return
        self.close()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)

    def focus_input(self):
        self._activate_foreground()
        self._input.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self._input.moveCursor(QTextCursor.MoveOperation.End)

    def _input_is_send_enter(self, event: QKeyEvent) -> bool:
        if event.key() not in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return False
        mods = event.modifiers()
        blocked = (
            Qt.KeyboardModifier.ShiftModifier |
            Qt.KeyboardModifier.ControlModifier |
            Qt.KeyboardModifier.AltModifier |
            Qt.KeyboardModifier.MetaModifier
        )
        return (mods & blocked) == Qt.KeyboardModifier.NoModifier

    def _update_preview(self):
        from core.slang import normalize_for_translation
        text = self._input.toPlainText().strip()
        if not text:
            self._pending = ''
            self._pending_src = ''
            self._last_preview_lang = ''
            self._preview_lbl.setText(tr('reply_preview_empty', 'Translation will appear here...'))
            self._apply_compact_geometry()
            return
        if not self.flash:
            return
        # Skip redundant work when neither text nor target language changed.
        if text == self._pending_src and self._tgt_lang_code == self._last_preview_lang and self._pending:
            return
        self._preview_lbl.setText(tr('reply_translating', 'Translating...'))
        self._apply_compact_geometry()
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
                translated = str(result.get('translation') or '').strip()
                if self._looks_untranslated(clean, translated):
                    self._pending = ''
                    self._pending_src = ''
                    self._preview_lbl.setText(
                        tr(
                            'reply_timeout',
                            'Translation timed out - try shorter text or retry.',
                        )
                    )
                    self._apply_compact_geometry()
                    return
                self._pending = translated
                self._pending_src = text
                self._last_preview_lang = self._tgt_lang_code
                preview = self._pending
                self._preview_lbl.setText(preview)
                self._apply_compact_geometry()
        except Exception as e:
            logging.error(f'[REPLY] Preview failed: {type(e).__name__}: {e}')

    def _populate_language_combo(self):
        if not self.flash:
            return
        items = sorted(self.flash.LANG_CODES.items(), key=lambda x: x[0])
        current_idx = 0
        for i, (name, code) in enumerate(items):
            self._lang_combo.addItem(name.capitalize(), code)
            if code == self._tgt_lang_code:
                current_idx = i
        self._lang_combo.setCurrentIndex(current_idx)
        self._on_language_changed(current_idx)

    def _on_language_changed(self, _index: int):
        code = self._lang_combo.currentData()
        if code:
            self._tgt_lang_code = str(code)
        self._tgt_lang_name = self._tgt_lang_code[:3].upper()
        if hasattr(self, '_hint_lbl'):
            if self.compact:
                self._hint_lbl.setText(tr('reply_hint_compact', '-> {target}', target=self._tgt_lang_name))
            else:
                self._hint_lbl.setText(
                    tr('reply_hint', 'Type your reply - will be translated to {target}', target=self._tgt_lang_name)
                )
        self.opened.emit(self._tgt_lang_code)
        if hasattr(self, '_input') and self._input.toPlainText().strip():
            self._schedule_preview_update(force_ms=140)

    def eventFilter(self, watched, event):
        if watched in self._draggable_widgets:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self._dragging = True
                event.accept()
                return True
            if event.type() == QEvent.Type.MouseMove and self._dragging and self._drag_offset is not None:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    self.move(event.globalPosition().toPoint() - self._drag_offset)
                    event.accept()
                    return True
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._dragging = False
                self._drag_offset = None
                event.accept()
                return True

        if watched is self._input and isinstance(event, QKeyEvent):
            if event.type() == QEvent.Type.KeyPress and self._input_is_send_enter(event):
                self._send_btn.click()
                return True
        return super().eventFilter(watched, event)

    def closeEvent(self, event):
        # Clean up timers and event filters on close
        if hasattr(self, '_debounce') and self._debounce:
            self._debounce.stop()
            self._debounce.deleteLater()
        if hasattr(self, '_input') and self._input:
            self._input.removeEventFilter(self)
        super().closeEvent(event)

    def _send(self):
        text = self._input.toPlainText().strip()
        if text and text != self._pending_src:
            self._update_preview()
        if not self._pending:
            return
        try:
            # Arm clipboard suppression before copy to avoid listener race.
            self.sent.emit(self._pending)
            pyperclip.copy(self._pending)
            logging.info(f'[REPLY] Copied: {self._pending[:60]}')
            self.close()
        except Exception as e:
            logging.error(f'[REPLY] Send failed: {e}')
