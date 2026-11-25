"""Sağ kontrol paneli: durum, göstergeler, ayarlar ve tespit akışı."""
from __future__ import annotations

import cv2
import numpy as np
from PyQt6.QtCore import QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QImage, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFrame, QGridLayout,
                             QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea,
                             QSlider, QVBoxLayout, QWidget)

from .. import config
from ..worker import Alert
from . import icons, theme

THUMB = 84


def _restyle(widget: QWidget) -> None:
    """Dinamik özellik (property) değişince QSS'i yeniden uygular."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _rgba(hex_color: str, alpha: float) -> str:
    """'#rrggbb' -> 'rgba(r,g,b,a)'. Qt 8 haneli hex'i #AARRGGBB okur; bu yüzden rgba."""
    c = hex_color.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _to_pixmap(bgr: np.ndarray, size: int) -> QPixmap:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w, _ = rgb.shape
    img = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(img).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)


class AlertCard(QFrame):
    """Akıştaki tek tespit kartı. Tıklanınca kanıt görüntüsü açılır."""

    def __init__(self, alert: Alert) -> None:
        super().__init__()
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._path = alert.path
        info = config.class_info(alert.cls)
        color = config.SEVERITY_COLORS[info.severity]
        self.setToolTip(f"Kanıtı aç: {alert.path}")
        self.setAccessibleName(f"{info.tr}, güven yüzde {alert.conf * 100:.0f}, "
                               f"alarm {alert.alert_id}")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 10, 0)
        row.setSpacing(10)

        stripe = QFrame()
        stripe.setFixedWidth(4)
        stripe.setStyleSheet(f"background:{color}; border-top-left-radius:10px;"
                             "border-bottom-left-radius:10px;")
        row.addWidget(stripe)

        thumb = QLabel()
        thumb.setObjectName("thumb")
        thumb.setFixedSize(THUMB, THUMB)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setPixmap(_to_pixmap(alert.crop, THUMB - 6))
        wrap = QVBoxLayout()
        wrap.setContentsMargins(0, 8, 0, 8)
        wrap.addWidget(thumb)
        row.addLayout(wrap)

        col = QVBoxLayout()
        col.setContentsMargins(0, 10, 0, 10)
        col.setSpacing(4)
        top = QHBoxLayout()
        title = QLabel(info.tr)
        title.setObjectName("cardTitle")
        chip = QLabel(config.SEVERITY_LABELS[info.severity])
        chip.setObjectName("chip")
        chip.setStyleSheet(f"color:{color}; background: {_rgba(color, 0.16)};")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(chip)
        col.addLayout(top)

        meta = QLabel(f"{alert.cls}  ·  #{alert.alert_id:04d}  ·  "
                      f"{alert.when.strftime('%H:%M:%S')}")
        meta.setObjectName("cardMeta")
        col.addWidget(meta)

        conf_row = QHBoxLayout()
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(round(alert.conf * 100))
        bar.setTextVisible(False)
        bar.setStyleSheet(f"QProgressBar::chunk {{ background:{color}; border-radius:2px; }}")
        pct = QLabel(f"%{alert.conf * 100:.0f}")
        pct.setObjectName("cardMeta")
        pct.setFixedWidth(34)
        pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        conf_row.addWidget(bar, 1)
        conf_row.addWidget(pct)
        col.addLayout(conf_row)
        row.addLayout(col, 1)

        # Yeni kart birkaç saniye vurgulu kalır
        self.setProperty("fresh", True)
        QTimer.singleShot(3000, self._unfresh)

    def _unfresh(self) -> None:
        self.setProperty("fresh", False)
        _restyle(self)

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._path))


class Tile(QFrame):
    def __init__(self, label: str, value: str = "—") -> None:
        super().__init__()
        self.setObjectName("tile")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(1)
        self.value = QLabel(value)
        self.value.setObjectName("tileValue")
        cap = QLabel(label)
        cap.setObjectName("tileLabel")
        lay.addWidget(self.value)
        lay.addWidget(cap)

    def set(self, text: str) -> None:
        self.value.setText(text)


class Panel(QWidget):
    pause_toggled = pyqtSignal(bool)
    region_requested = pyqtSignal()
    full_region_requested = pyqtSignal()
    screen_changed = pyqtSignal(int)
    conf_changed = pyqtSignal(float)
    imgsz_changed = pyqtSignal(int)
    quit_requested = pyqtSignal()

    def __init__(self, screen_names: list[str], screen_index: int, conf: float,
                 imgsz: int, sound: bool) -> None:
        super().__init__()
        self.setObjectName("panel")
        self.setWindowTitle("X-Ray Polisi — Tehlikeli Madde Algılama")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setStyleSheet(theme.QSS)
        self.setFixedWidth(config.PANEL_WIDTH)

        self._paused = False
        self._alert_count = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body = QVBoxLayout()
        body.setContentsMargins(16, 14, 16, 10)
        body.setSpacing(12)
        body.addWidget(self._build_banner())
        body.addLayout(self._build_tiles())
        body.addWidget(self._build_controls(screen_names, screen_index, conf, imgsz, sound))
        body.addLayout(self._build_feed_header())
        body.addWidget(self._build_feed(), 1)
        root.addLayout(body, 1)
        root.addWidget(self._build_footer())

        self._banner_timer = QTimer(self, singleShot=True, timeout=self.banner.hide)
        self._shortcuts()
        self.set_state("loading", "MODEL YÜKLENİYOR")

    # ------------------------------------------------------- yapı
    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        logo = QLabel()
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(icons.shield(theme.ACCENT, 34))
        names = QVBoxLayout()
        names.setSpacing(0)
        brand = QLabel("X-Ray Polisi")
        brand.setObjectName("brand")
        tag = QLabel("Tehlikeli madde algılama")
        tag.setObjectName("tagline")
        names.addWidget(brand)
        names.addWidget(tag)
        self.pill = QLabel()
        self.pill.setObjectName("pill")
        lay.addWidget(logo)
        lay.addLayout(names)
        lay.addStretch()
        lay.addWidget(self.pill)
        return header

    def _build_banner(self) -> QFrame:
        self.banner = QFrame()
        self.banner.setObjectName("banner")
        outer = QHBoxLayout(self.banner)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(12)
        mark = QLabel()
        mark.setPixmap(icons.alert("#ffffff", 26))
        outer.addWidget(mark)
        lay = QVBoxLayout()
        lay.setSpacing(2)
        outer.addLayout(lay, 1)
        self.banner_title = QLabel()
        self.banner_title.setObjectName("bannerTitle")
        self.banner_sub = QLabel()
        self.banner_sub.setObjectName("bannerSub")
        lay.addWidget(self.banner_title)
        lay.addWidget(self.banner_sub)
        self.banner.hide()
        return self.banner

    def _build_tiles(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(8)
        self.tile_fps = Tile("FPS")
        self.tile_latency = Tile("GECİKME")
        self.tile_device = Tile("CİHAZ")
        self.tile_alerts = Tile("ALARM", "0")
        grid.addWidget(self.tile_fps, 0, 0)
        grid.addWidget(self.tile_latency, 0, 1)
        grid.addWidget(self.tile_device, 1, 0)
        grid.addWidget(self.tile_alerts, 1, 1)
        return grid

    def _build_controls(self, screen_names, screen_index, conf, imgsz, sound) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 2, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(self._section("KONTROLLER"))

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.btn_pause = QPushButton(icons.pause("#111111"), "  Duraklat")
        self.btn_pause.setObjectName("primary")
        self.btn_pause.setToolTip("Taramayı duraklat / sürdür (Ctrl+P)")
        self.btn_pause.clicked.connect(self.toggle_pause)
        btn_region = QPushButton(icons.target(theme.TEXT), "  Alan seç")
        btn_region.setToolTip("Yalnız X-ray görüntüsünü tara (Ctrl+R)")
        btn_region.clicked.connect(self.region_requested)
        btn_full = QPushButton(icons.expand(theme.TEXT), "")
        btn_full.setToolTip("Tüm ekranı tara (panel hariç)")
        btn_full.setAccessibleName("Tüm ekranı tara")
        btn_full.setFixedWidth(42)
        btn_full.clicked.connect(self.full_region_requested)
        buttons.addWidget(self.btn_pause, 1)
        buttons.addWidget(btn_region, 1)
        buttons.addWidget(btn_full)
        lay.addLayout(buttons)

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)
        form.setColumnStretch(1, 1)

        self.screen_combo = QComboBox()
        self.screen_combo.addItems(screen_names)
        self.screen_combo.setCurrentIndex(screen_index)
        self.screen_combo.setAccessibleName("Taranacak ekran")
        self.screen_combo.currentIndexChanged.connect(self.screen_changed)
        form.addWidget(self._field("Ekran"), 0, 0)
        form.addWidget(self.screen_combo, 0, 1, 1, 2)

        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(10, 90)
        self.conf_slider.setSingleStep(5)
        self.conf_slider.setValue(round(conf * 100))
        self.conf_slider.setAccessibleName("Güven eşiği")
        self.conf_value = QLabel()
        self.conf_value.setObjectName("fieldValue")
        self.conf_value.setFixedWidth(36)
        self.conf_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.conf_slider.valueChanged.connect(self._on_conf)
        self._on_conf(self.conf_slider.value(), emit=False)
        form.addWidget(self._field("Güven eşiği"), 1, 0)
        form.addWidget(self.conf_slider, 1, 1)
        form.addWidget(self.conf_value, 1, 2)

        seg = QHBoxLayout()
        seg.setSpacing(0)
        self.size_group = QButtonGroup(self)
        choices = config.IMG_SIZE_CHOICES
        for i, size in enumerate(choices):
            b = QPushButton(str(size))
            b.setCheckable(True)
            b.setChecked(size == imgsz)
            b.setObjectName("segFirst" if i == 0 else "segLast" if i == len(choices) - 1 else "seg")
            b.setToolTip("Büyük değer küçük nesnede daha iyi, ama daha yavaş. Model 640 ile eğitildi.")
            self.size_group.addButton(b, size)
            seg.addWidget(b, 1)
        self.size_group.idClicked.connect(self.imgsz_changed)
        form.addWidget(self._field("Girdi boyutu"), 2, 0)
        form.addLayout(seg, 2, 1, 1, 2)

        self.sound_check = QCheckBox("Sesli alarm")
        self.sound_check.setChecked(sound)
        self.sound_check.setToolTip("Yüksek ve orta önemli tespitte sistem sesi çalar")
        form.addWidget(self._field("Ses"), 3, 0)
        form.addWidget(self.sound_check, 3, 1, 1, 2)
        lay.addLayout(form)

        line = QFrame()
        line.setObjectName("divider")
        lay.addWidget(line)
        return box

    def _build_feed_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(self._section("TESPİT AKIŞI"))
        row.addStretch()
        clear = QPushButton("Temizle")
        clear.setObjectName("ghost")
        clear.setToolTip("Listeyi temizler; kayıt dosyaları silinmez")
        clear.clicked.connect(self.clear_feed)
        row.addWidget(clear)
        return row

    def _build_feed(self) -> QScrollArea:
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        self.feed = QVBoxLayout(content)
        self.feed.setContentsMargins(0, 0, 4, 0)
        self.feed.setSpacing(8)
        self.feed.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.empty = QLabel("Henüz tespit yok.\nTarama alanında görülen tehditler burada listelenir.")
        self.empty.setObjectName("empty")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setWordWrap(True)
        self.feed.addWidget(self.empty)
        self.scroll.setWidget(content)
        return self.scroll

    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("footer")
        lay = QVBoxLayout(footer)
        lay.setContentsMargins(16, 10, 16, 12)
        lay.setSpacing(8)
        row = QHBoxLayout()
        folder = QPushButton(icons.folder(theme.TEXT), "  Kayıt klasörü")
        folder.setToolTip(str(config.LOG_DIR))
        folder.clicked.connect(self._open_logs)
        quit_btn = QPushButton(icons.power(theme.DANGER), "  Çıkış")
        quit_btn.setObjectName("danger")
        quit_btn.setToolTip("Uygulamayı kapat (Ctrl+Q)")
        quit_btn.clicked.connect(self.quit_requested)
        row.addWidget(folder, 1)
        row.addWidget(quit_btn)
        lay.addLayout(row)
        hint = QLabel("Ctrl+P duraklat  ·  Ctrl+R alan seç  ·  Ctrl+Q çıkış")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)
        return footer

    @staticmethod
    def _section(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("section")
        return label

    @staticmethod
    def _field(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _shortcuts(self) -> None:
        for keys, slot in (("Ctrl+P", self.toggle_pause), ("Ctrl+R", self.region_requested.emit),
                           ("Ctrl+Q", self.quit_requested.emit)):
            QShortcut(QKeySequence(keys), self, activated=slot)

    # --------------------------------------------------- davranış
    def _on_conf(self, value: int, emit: bool = True) -> None:
        self.conf_value.setText(f"%{value}")
        if emit:
            self.conf_changed.emit(value / 100)

    def _open_logs(self) -> None:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(config.LOG_DIR)))

    def toggle_pause(self) -> None:
        self._paused = not self._paused
        self.btn_pause.setText("  Sürdür" if self._paused else "  Duraklat")
        self.btn_pause.setIcon(icons.play("#111111") if self._paused else icons.pause("#111111"))
        self.btn_pause.setProperty("paused", self._paused)
        _restyle(self.btn_pause)
        self.set_state("paused" if self._paused else "active",
                       "DURAKLATILDI" if self._paused else "AKTİF")
        self.pause_toggled.emit(self._paused)

    @property
    def sound_enabled(self) -> bool:
        return self.sound_check.isChecked()

    def set_state(self, state: str, text: str) -> None:
        self.pill.setText(f"●  {text}")
        self.pill.setProperty("state", state)
        _restyle(self.pill)

    def set_device(self, name: str) -> None:
        short = name.replace("NVIDIA GeForce ", "").replace("NVIDIA ", "")
        self.tile_device.set(short)
        self.tile_device.setToolTip(name)
        if not self._paused:
            self.set_state("active", "AKTİF")

    def set_worker_status(self, kind: str, message: str) -> None:
        if self._paused:
            return
        if kind == "error":
            self.set_state("error", "HATA")
            self.pill.setToolTip(message)
        else:
            self.set_state("active", "AKTİF")
            self.pill.setToolTip("")

    def set_metrics(self, fps: float, latency_ms: float) -> None:
        self.tile_fps.set(f"{fps:.1f}")
        self.tile_latency.set(f"{latency_ms:.0f} ms")

    def add_alert(self, alert: Alert) -> None:
        self.empty.hide()
        self._alert_count += 1
        self.tile_alerts.set(str(self._alert_count))
        self.feed.insertWidget(0, AlertCard(alert))
        # Sınırlı liste: en eski kartlar silinir (kanıt dosyaları kalır)
        while self.feed.count() > config.MAX_FEED_ITEMS + 1:  # +1: boş durum etiketi
            item = self.feed.takeAt(self.feed.count() - 2)
            if item and item.widget():
                item.widget().deleteLater()
        self.scroll.verticalScrollBar().setValue(0)
        self._show_banner(alert)

    def _show_banner(self, alert: Alert) -> None:
        info = config.class_info(alert.cls)
        if info.severity == "low":
            return
        color = config.SEVERITY_COLORS[info.severity]
        self.banner.setStyleSheet(f"QFrame#banner {{ background: {color}; }}")
        self.banner_title.setText(f"{config.tr_upper(info.tr)} TESPİT EDİLDİ")
        self.banner_sub.setText(f"Alarm #{alert.alert_id:04d}  ·  güven %{alert.conf * 100:.0f}"
                                f"  ·  {alert.when.strftime('%H:%M:%S')}")
        self.banner.show()
        self._banner_timer.start(4000)

    def clear_feed(self) -> None:
        while self.feed.count() > 1:
            item = self.feed.takeAt(0)
            if item.widget() is self.empty:
                self.feed.addWidget(self.empty)
                continue
            if item.widget():
                item.widget().deleteLater()
        self.empty.show()

    def closeEvent(self, e) -> None:
        self.quit_requested.emit()
        e.accept()

    def sizeHint(self) -> QSize:
        return QSize(config.PANEL_WIDTH, 900)
