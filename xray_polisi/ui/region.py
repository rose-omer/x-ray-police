"""Taranacak alanı fareyle seçtiren tam ekran pencere."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from . import theme

MIN_SIZE = 64


class RegionSelector(QWidget):
    selected = pyqtSignal(QRect)   # global mantıksal koordinat
    cancelled = pyqtSignal()

    def __init__(self, screen_geo: QRect) -> None:
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(screen_geo)
        self._origin: QPoint | None = None
        self._rect = QRect()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.RightButton:
            self._cancel()
            return
        self._origin = e.position().toPoint()
        self._rect = QRect(self._origin, self._origin)
        self.update()

    def mouseMoveEvent(self, e) -> None:
        if self._origin is not None:
            self._rect = QRect(self._origin, e.position().toPoint()).normalized()
            self.update()

    def mouseReleaseEvent(self, e) -> None:
        if self._origin is None:
            return
        self._origin = None
        if self._rect.width() < MIN_SIZE or self._rect.height() < MIN_SIZE:
            self._rect = QRect()
            self.update()
            return
        self.selected.emit(self._rect.translated(self.geometry().topLeft()))
        self.close()

    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key.Key_Escape:
            self._cancel()

    def _cancel(self) -> None:
        self.cancelled.emit()
        self.close()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        shade = QPainterPath()
        shade.addRect(QRectF(self.rect()))
        if not self._rect.isNull():
            hole = QPainterPath()
            hole.addRect(QRectF(self._rect))
            shade = shade.subtracted(hole)
        p.fillPath(shade, QColor(5, 8, 12, 150))

        if not self._rect.isNull():
            p.setPen(QPen(QColor(theme.ACCENT), 2))
            p.drawRect(self._rect)
            size = f"{self._rect.width()} × {self._rect.height()}"
            p.setFont(QFont(theme.FONT, 9, QFont.Weight.Bold))
            p.setPen(QColor(theme.ACCENT))
            p.drawText(self._rect.left(), self._rect.bottom() + 18, size)

        hint = QRect(0, 40, self.width(), 60)
        p.setFont(QFont(theme.FONT, 15, QFont.Weight.DemiBold))
        p.setPen(QColor(theme.TEXT))
        p.drawText(hint, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                   "Taranacak alanı fareyle çizin")
        p.setFont(QFont(theme.FONT, 10))
        p.setPen(QColor(theme.MUTED))
        p.drawText(hint.adjusted(0, 30, 0, 0), Qt.AlignmentFlag.AlignHCenter,
                   "Yalnız X-ray görüntüsünü seçin  ·  Esc ya da sağ tık: iptal")
