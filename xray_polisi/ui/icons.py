"""QPainter ile çizilen küçük çizgi simgeler (emoji yazı tipine bağımlı değil)."""
from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

SIZE = 64  # çizim tuvali; Qt ikonu gereken boyuta küçültür


def _icon(draw: Callable[[QPainter], None], color: str) -> QIcon:
    pm = QPixmap(SIZE, SIZE)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    draw(p)
    p.end()
    return QIcon(pm)


def pause(color: str) -> QIcon:
    def draw(p: QPainter) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(16, 12, 11, 40), 3, 3)
        p.drawRoundedRect(QRectF(37, 12, 11, 40), 3, 3)
    return _icon(draw, color)


def play(color: str) -> QIcon:
    def draw(p: QPainter) -> None:
        path = QPainterPath(QPointF(20, 12))
        path.lineTo(52, 32)
        path.lineTo(20, 52)
        path.closeSubpath()
        p.setBrush(QColor(color))
        p.drawPath(path)
    return _icon(draw, color)


def target(color: str) -> QIcon:
    def draw(p: QPainter) -> None:
        p.drawEllipse(QPointF(32, 32), 17, 17)
        for x1, y1, x2, y2 in ((32, 4, 32, 18), (32, 46, 32, 60), (4, 32, 18, 32), (46, 32, 60, 32)):
            p.drawLine(x1, y1, x2, y2)
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(32, 32), 3, 3)
    return _icon(draw, color)


def expand(color: str) -> QIcon:
    def draw(p: QPainter) -> None:
        for pts in (((8, 24), (8, 8), (24, 8)), ((40, 8), (56, 8), (56, 24)),
                    ((8, 40), (8, 56), (24, 56)), ((56, 40), (56, 56), (40, 56))):
            path = QPainterPath(QPointF(*pts[0]))
            for pt in pts[1:]:
                path.lineTo(QPointF(*pt))
            p.drawPath(path)
    return _icon(draw, color)


def folder(color: str) -> QIcon:
    def draw(p: QPainter) -> None:
        path = QPainterPath(QPointF(6, 50))
        for pt in ((6, 14), (24, 14), (30, 20), (58, 20), (58, 50)):
            path.lineTo(QPointF(*pt))
        path.closeSubpath()
        p.drawPath(path)
    return _icon(draw, color)


def power(color: str) -> QIcon:
    def draw(p: QPainter) -> None:
        p.drawArc(QRectF(12, 14, 40, 40), 120 * 16, -240 * 16)
        p.drawLine(32, 8, 32, 30)
    return _icon(draw, color)


def shield(color: str, size: int = 22, line: str = "#ffffff") -> QPixmap:
    """Logo: polis rozeti gibi kalkan + tarama çizgileri."""
    pm = QPixmap(SIZE, SIZE)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath(QPointF(32, 6))
    path.cubicTo(42, 12, 50, 13, 56, 13)
    path.cubicTo(56, 38, 48, 52, 32, 59)
    path.cubicTo(16, 52, 8, 38, 8, 13)
    path.cubicTo(14, 13, 22, 12, 32, 6)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawPath(path)
    pen = QPen(QColor(line), 5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(19, 32, 45, 32)
    p.drawLine(25, 22, 39, 22)
    p.drawLine(25, 42, 39, 42)
    p.end()
    return pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)


def alert(color: str, size: int = 22) -> QPixmap:
    """Uyarı üçgeni (alarm şeridi için)."""
    pm = QPixmap(SIZE, SIZE)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 6)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    path = QPainterPath(QPointF(32, 8))
    path.lineTo(58, 54)
    path.lineTo(6, 54)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(32, 24, 32, 38)
    p.drawPoint(32, 46)
    p.end()
    return pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)
