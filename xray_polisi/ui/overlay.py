"""Ekranın üstüne çizilen saydam katman: tarama alanı ve tespit kutuları."""
from __future__ import annotations

import time

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from .. import config
from ..logic import ScreenMap
from ..worker import FrameResult
from . import theme

STALE_AFTER_S = 1.0   # bu süre yeni kare gelmezse kutular silinir


class Overlay(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("X-Ray Polisi Overlay")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.WindowTransparentForInput
                            | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._map: ScreenMap | None = None
        self._region_local: QRectF | None = None
        self._boxes: list[tuple[QRectF, str, float, int]] = []
        self._paused = False
        self._last_frame = 0.0

        self._font = QFont(theme.FONT, 10, QFont.Weight.DemiBold)
        self._small = QFont(theme.FONT, 8, QFont.Weight.Bold)

        self._stale = QTimer(self, interval=300, timeout=self._drop_stale)
        self._stale.start()

    # ------------------------------------------------------------ API
    def set_screen(self, smap: ScreenMap, region: dict[str, int]) -> None:
        self._map = smap
        self.setGeometry(smap.log_x, smap.log_y, smap.log_w, smap.log_h)
        self.set_region(region)

    def set_region(self, region: dict[str, int]) -> None:
        if self._map:
            x1, y1, x2, y2 = self._map.region_to_local(region)
            self._region_local = QRectF(x1, y1, x2 - x1, y2 - y1)
        self._boxes = []
        self.update()

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        if paused:
            self._boxes = []
        self.update()

    def show_frame(self, result: FrameResult) -> None:
        if self._map is None or self._paused:
            return
        boxes = []
        for d in result.detections:
            x1, y1, x2, y2 = self._map.box_to_local(d.box, result.region)
            boxes.append((QRectF(x1, y1, x2 - x1, y2 - y1), d.cls, d.conf, d.alert_id))
        self._boxes = boxes
        self._last_frame = time.monotonic()
        self.update()

    def _drop_stale(self) -> None:
        if self._boxes and time.monotonic() - self._last_frame > STALE_AFTER_S:
            self._boxes = []
            self.update()

    # -------------------------------------------------------- çizim
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._region_local is not None:
            self._paint_region(p, self._region_local)
        for rect, cls, conf, alert_id in self._boxes:
            self._paint_box(p, rect, cls, conf, alert_id)

    def _paint_region(self, p: QPainter, r: QRectF) -> None:
        color = QColor(theme.ACCENT if self._paused else "#ffffff")
        color.setAlpha(150 if self._paused else 90)
        r = r.adjusted(2, 2, -2, -2)
        p.setPen(QPen(color, 2))
        arm = 22
        for cx, cy, dx, dy in ((r.left(), r.top(), 1, 1), (r.right(), r.top(), -1, 1),
                               (r.left(), r.bottom(), 1, -1), (r.right(), r.bottom(), -1, -1)):
            p.drawLine(int(cx), int(cy), int(cx + dx * arm), int(cy))
            p.drawLine(int(cx), int(cy), int(cx), int(cy + dy * arm))

        text = "TARAMA DURAKLATILDI" if self._paused else "X-RAY POLİSİ · TARAMA ALANI"
        p.setFont(self._small)
        fm = QFontMetrics(self._small)
        tw = fm.horizontalAdvance(text) + 14
        tag = QRectF(r.left() + 10, r.top() + 8, tw, 18)
        bg = QColor(0, 0, 0, 150)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(tag, 4, 4)
        p.setPen(color if self._paused else QColor(255, 255, 255, 200))
        p.drawText(tag, Qt.AlignmentFlag.AlignCenter, text)

    def _paint_box(self, p: QPainter, rect: QRectF, cls: str, conf: float, alert_id: int) -> None:
        info = config.class_info(cls)
        color = QColor(config.SEVERITY_COLORS[info.severity])

        # İnce çerçeve + kalın köşeler
        fill = QColor(color)
        fill.setAlpha(28)
        p.setBrush(fill)
        edge = QColor(color)
        edge.setAlpha(200)
        p.setPen(QPen(edge, 1.5))
        p.drawRoundedRect(rect, 3, 3)

        corner = QPen(color, 4)
        corner.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(corner)
        arm = max(8.0, min(18.0, rect.width() / 4, rect.height() / 4))
        path = QPainterPath()
        for cx, cy, dx, dy in ((rect.left(), rect.top(), 1, 1), (rect.right(), rect.top(), -1, 1),
                               (rect.left(), rect.bottom(), 1, -1),
                               (rect.right(), rect.bottom(), -1, -1)):
            path.moveTo(cx + dx * arm, cy)
            path.lineTo(cx, cy)
            path.lineTo(cx, cy + dy * arm)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        # Etiket: kutunun üstünde; yer yoksa içinde
        label = f"{config.tr_upper(info.tr)}   %{conf * 100:.0f}   #{alert_id:04d}"
        p.setFont(self._font)
        fm = QFontMetrics(self._font)
        lw, lh = fm.horizontalAdvance(label) + 16, fm.height() + 8
        lx = min(max(0.0, rect.left()), self.width() - lw)
        ly = rect.top() - lh - 3
        if ly < 0:
            ly = rect.top() + 3
        tag = QRectF(lx, ly, lw, lh)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(tag, 5, 5)
        p.setPen(QColor("#111111") if info.severity != "high" else QColor("#ffffff"))
        p.drawText(tag, Qt.AlignmentFlag.AlignCenter, label)
