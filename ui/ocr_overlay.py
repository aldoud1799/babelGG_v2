from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen


class OCRSelectionOverlay(QWidget):
    selected = pyqtSignal(QRect)
    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._origin = None
        self._current = None
        self._virtual_rect = self._compute_virtual_rect()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(self._virtual_rect)

    def _compute_virtual_rect(self) -> QRect:
        screens = QApplication.screens()
        if not screens:
            return QRect(0, 0, 1920, 1080)
        left = min(s.geometry().left() for s in screens)
        top = min(s.geometry().top() for s in screens)
        right = max(s.geometry().right() for s in screens)
        bottom = max(s.geometry().bottom() for s in screens)
        return QRect(left, top, (right - left) + 1, (bottom - top) + 1)

    def _selection_rect_local(self) -> QRect:
        if self._origin is None or self._current is None:
            return QRect()
        return QRect(self._origin, self._current).normalized()

    def _selection_rect_global(self) -> QRect:
        local = self._selection_rect_local()
        if local.isNull():
            return QRect()
        return QRect(
            local.x() + self._virtual_rect.x(),
            local.y() + self._virtual_rect.y(),
            local.width(),
            local.height(),
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._current = self._origin
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.cancelled.emit()
            self.close()

    def mouseMoveEvent(self, event):
        if self._origin is not None:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._current = event.position().toPoint()
        rect = self._selection_rect_global()
        if rect.width() < 12 or rect.height() < 12:
            self.cancelled.emit()
        else:
            self.selected.emit(rect)
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dim full desktop area.
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))

        selection = self._selection_rect_local()
        if not selection.isNull():
            # Clear selection region.
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(selection, QColor(0, 0, 0, 0))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            painter.setPen(QPen(QColor(132, 176, 255, 230), 2))
            painter.drawRect(selection)

            painter.fillRect(selection, QColor(50, 100, 180, 28))

        painter.setPen(QColor(225, 235, 255, 220))
        painter.drawText(
            20,
            30,
            'OCR Capture: drag to select region, Esc/right-click to cancel',
        )
