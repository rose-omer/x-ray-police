"""Uygulama giriş noktası: pencereleri, iş parçacığını ve ayarları bağlar."""
from __future__ import annotations

import logging
import sys
import time
import traceback

from PyQt6.QtCore import QRect, QSettings
from PyQt6.QtGui import QScreen
from PyQt6.QtWidgets import QApplication, QMessageBox

from . import config, winapi
from .logic import ScreenMap, match_monitor
from .ui.overlay import Overlay
from .ui.panel import Panel
from .ui.region import RegionSelector
from .worker import _MSS, Alert, DetectorWorker, FrameResult

log = logging.getLogger("xray_polisi")


def _setup_logging() -> None:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(),
                  logging.FileHandler(config.LOG_DIR / "xray_polisi.log", encoding="utf-8")],
    )

    def hook(exc_type, exc, tb):
        # PyQt6 yakalanmamış hatada süreci kapatır; özel kanca uygulamayı açık tutar
        log.error("Yakalanmamış hata:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))

    sys.excepthook = hook


def _screen_map(screen: QScreen) -> ScreenMap:
    geo = screen.geometry()
    dpr = screen.devicePixelRatio()
    with _MSS() as sct:
        monitors = sct.monitors[1:]
    mon = match_monitor((geo.x(), geo.y(), geo.width(), geo.height()), dpr, monitors)
    if mon is None:
        log.warning("Ekran mss monitörüyle eşleşmedi, ölçekten tahmin ediliyor: %s", screen.name())
        mon = {"left": geo.x(), "top": geo.y(),
               "width": round(geo.width() * dpr), "height": round(geo.height() * dpr)}
    return ScreenMap(geo.x(), geo.y(), geo.width(), geo.height(),
                     mon["left"], mon["top"], mon["width"], mon["height"])


def _screen_label(i: int, screen: QScreen, primary: QScreen) -> str:
    geo = screen.geometry()
    scale = round(screen.devicePixelRatio() * 100)
    tail = " · birincil" if screen is primary else ""
    return f"{i + 1}.  {geo.width()}×{geo.height()} · %{scale}{tail}"


class Controller:
    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.settings = QSettings("XRayPolisi", "XRayPolisi")
        self.screens = app.screens()
        primary = app.primaryScreen()

        saved = self.settings.value("screen", "", str)
        names = [s.name() for s in self.screens]
        self.screen_idx = names.index(saved) if saved in names else self.screens.index(primary)
        conf = float(self.settings.value("conf", config.CONF_THRESHOLD))
        imgsz = int(self.settings.value("imgsz", config.IMG_SIZE))
        if imgsz not in config.IMG_SIZE_CHOICES:
            imgsz = config.IMG_SIZE
        sound = self.settings.value("sound", True, bool)

        self.panel = Panel([_screen_label(i, s, primary) for i, s in enumerate(self.screens)],
                           self.screen_idx, conf, imgsz, sound)
        self.overlay = Overlay()
        self._selector: RegionSelector | None = None
        self._last_beep = 0.0

        self.smap = _screen_map(self.screens[self.screen_idx])
        self.region = self._full_region()
        self.worker = DetectorWorker(self.region)
        self.worker.set_conf(conf)
        self.worker.set_imgsz(imgsz)

        self._place_windows()
        self._connect()

    # -------------------------------------------------------- yerleşim
    def _full_region(self) -> dict[str, int]:
        """Panel hariç tüm ekran (fiziksel)."""
        m = self.smap
        return m.to_physical(m.log_x, m.log_y, m.log_w - config.PANEL_WIDTH, m.log_h)

    def _place_windows(self) -> None:
        screen = self.screens[self.screen_idx]
        avail = screen.availableGeometry()
        self.panel.setGeometry(avail.right() - config.PANEL_WIDTH + 1, avail.top(),
                               config.PANEL_WIDTH, avail.height())
        self.overlay.set_screen(self.smap, self.region)

    def _connect(self) -> None:
        p, w = self.panel, self.worker
        w.model_ready.connect(p.set_device)
        w.model_failed.connect(self._model_failed)
        w.frame_ready.connect(self._on_frame)
        w.new_alert.connect(self._on_alert)
        w.status.connect(p.set_worker_status)

        p.pause_toggled.connect(self._on_pause)
        p.region_requested.connect(self._select_region)
        p.full_region_requested.connect(lambda: self._set_region(self._full_region()))
        p.screen_changed.connect(self._change_screen)
        p.conf_changed.connect(self._on_conf)
        p.imgsz_changed.connect(self._on_imgsz)
        p.sound_check.toggled.connect(lambda v: self.settings.setValue("sound", v))
        p.quit_requested.connect(self.app.quit)
        self.app.aboutToQuit.connect(self.worker.stop)

    def start(self) -> None:
        self.overlay.show()
        self.panel.show()
        # Kendi pencerelerimiz modele girmesin (geri besleme hatası)
        for widget in (self.overlay, self.panel):
            winapi.exclude_from_capture(widget)
        self.worker.start()

    # -------------------------------------------------------- olaylar
    def _on_frame(self, result: FrameResult) -> None:
        self.overlay.show_frame(result)
        self.panel.set_metrics(result.fps, result.latency_ms)

    def _on_alert(self, alert: Alert) -> None:
        self.panel.add_alert(alert)
        severity = config.class_info(alert.cls).severity
        now = time.monotonic()
        if (self.panel.sound_enabled and severity != "low"
                and now - self._last_beep > config.BEEP_COOLDOWN_S):
            self._last_beep = now
            winapi.beep(severity)

    def _on_pause(self, paused: bool) -> None:
        self.worker.set_paused(paused)
        self.overlay.set_paused(paused)

    def _on_conf(self, conf: float) -> None:
        self.worker.set_conf(conf)
        self.settings.setValue("conf", conf)

    def _on_imgsz(self, size: int) -> None:
        self.worker.set_imgsz(size)
        self.settings.setValue("imgsz", size)

    def _set_region(self, region: dict[str, int]) -> None:
        self.region = region
        self.worker.set_region(region)
        self.overlay.set_region(region)

    def _select_region(self) -> None:
        if self._selector is not None:
            return
        self._selector = RegionSelector(self.screens[self.screen_idx].geometry())
        self._selector.selected.connect(self._region_selected)
        self._selector.destroyed.connect(lambda: setattr(self, "_selector", None))
        self._selector.show()
        winapi.exclude_from_capture(self._selector)
        self._selector.activateWindow()

    def _region_selected(self, rect: QRect) -> None:
        self._set_region(self.smap.to_physical(rect.x(), rect.y(), rect.width(), rect.height()))

    def _change_screen(self, idx: int) -> None:
        self.screen_idx = idx
        self.settings.setValue("screen", self.screens[idx].name())
        self.smap = _screen_map(self.screens[idx])
        self.region = self._full_region()
        self.worker.set_region(self.region)
        self._place_windows()

    def _model_failed(self, message: str) -> None:
        self.panel.set_state("error", "MODEL YOK")
        QMessageBox.critical(self.panel, "X-Ray Polisi", f"{message}\n\nBeklenen yol:\n{config.MODEL_PATH}")


def main() -> int:
    _setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("X-Ray Polisi")
    controller = Controller(app)
    controller.start()
    return app.exec()
