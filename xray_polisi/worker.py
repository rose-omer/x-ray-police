"""Ekran yakalama + YOLO takip döngüsü. Arayüzü dondurmamak için ayrı
iş parçacığında çalışır; sonuçları Qt sinyalleriyle gönderir."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime

import cv2
import mss
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from . import config
from .logic import AlertDeduper, EventLog, crop_box, evidence_path

log = logging.getLogger(__name__)

# mss 10.x: mss.MSS; eski sürümler: mss.mss
_MSS = getattr(mss, "MSS", None) or mss.mss


@dataclass(frozen=True)
class Detection:
    box: tuple[float, float, float, float]   # yakalanan karede, fiziksel px
    cls: str
    conf: float
    alert_id: int


@dataclass(frozen=True)
class FrameResult:
    detections: list[Detection]
    region: dict[str, int]                    # bu karenin yakalama alanı
    fps: float
    latency_ms: float


@dataclass(frozen=True)
class Alert:
    alert_id: int
    cls: str
    conf: float
    crop: np.ndarray                          # BGR
    when: datetime
    path: str


class DetectorWorker(QThread):
    model_ready = pyqtSignal(str)             # cihaz adı
    model_failed = pyqtSignal(str)
    frame_ready = pyqtSignal(object)          # FrameResult
    new_alert = pyqtSignal(object)            # Alert
    status = pyqtSignal(str, str)             # durum ("ok" | "error"), mesaj

    def __init__(self, region: dict[str, int]) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._region = dict(region)
        self._conf = config.CONF_THRESHOLD
        self._imgsz = config.IMG_SIZE
        self._paused = False
        self._reset_tracker = False
        self._running = True
        self._deduper = AlertDeduper(config.DEDUP_IOU, config.DEDUP_TTL_S)
        self._events = EventLog(config.EVENTS_FILE)

    # --------------------------------------------------- UI'dan ayarlar
    def set_region(self, region: dict[str, int]) -> None:
        with self._lock:
            self._region = dict(region)
            self._reset_tracker = True

    def set_conf(self, conf: float) -> None:
        with self._lock:
            self._conf = conf

    def set_imgsz(self, imgsz: int) -> None:
        with self._lock:
            self._imgsz = imgsz
            self._reset_tracker = True

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self._paused = paused

    def stop(self) -> None:
        self._running = False
        self.wait(5000)

    # -------------------------------------------------------- döngü
    def run(self) -> None:
        try:
            model, device, device_name = self._load_model()
        except Exception as exc:  # model yoksa ya da bozuksa uygulama açık kalsın
            log.exception("Model yüklenemedi")
            self.model_failed.emit(f"Model yüklenemedi: {exc}")
            return
        self.model_ready.emit(device_name)

        errors = 0
        fps = 0.0
        last_tick = time.perf_counter()
        with _MSS() as sct:
            while self._running:
                with self._lock:
                    paused, region = self._paused, dict(self._region)
                    conf, imgsz = self._conf, self._imgsz
                    persist = not self._reset_tracker
                    self._reset_tracker = False
                if not persist:  # alan ya da boyut değişti: eski kutular geçersiz
                    self._deduper.reset()
                if paused:
                    self.msleep(100)
                    last_tick = time.perf_counter()
                    continue

                t0 = time.perf_counter()
                try:
                    frame = cv2.cvtColor(np.asarray(sct.grab(region)), cv2.COLOR_BGRA2BGR)
                    t_inf = time.perf_counter()
                    results = model.track(frame, conf=conf, imgsz=imgsz, persist=persist,
                                          half=device != "cpu", device=device, verbose=False)
                    latency = (time.perf_counter() - t_inf) * 1000
                    detections = self._handle(results[0], frame, model.names)
                except Exception:  # kilit ekranı, UAC, sürücü hatası...
                    errors += 1
                    wait = min(config.MAX_ERROR_BACKOFF_MS, 200 * errors)
                    if errors == 1 or errors % 25 == 0:
                        log.exception("Kare işlenemedi (%d. hata)", errors)
                    self.status.emit("error", f"Ekran okunamıyor, yeniden deneniyor ({errors})")
                    self.msleep(wait)
                    continue

                if errors:
                    errors = 0
                    self.status.emit("ok", "")
                now = time.perf_counter()
                period = now - last_tick
                last_tick = now
                if period > 0:
                    fps = 1 / period if fps == 0 else 0.9 * fps + 0.1 / period
                self.frame_ready.emit(FrameResult(detections, region, fps, latency))

                spent_ms = (time.perf_counter() - t0) * 1000
                self.msleep(max(1, int(config.FRAME_INTERVAL_MS - spent_ms)))

    def _load_model(self):
        import torch
        from ultralytics import YOLO

        if not config.MODEL_PATH.exists():
            raise FileNotFoundError(str(config.MODEL_PATH))
        model = YOLO(str(config.MODEL_PATH))
        if torch.cuda.is_available():
            device, name = "cuda:0", torch.cuda.get_device_name(0)
        else:
            device, name = "cpu", "CPU"
        model.to(device)
        # Isınma: ilk gerçek karede ~2 sn gecikmeyi önler
        model.predict(np.zeros((640, 640, 3), np.uint8), imgsz=self._imgsz,
                      half=device != "cpu", device=device, verbose=False)
        log.info("Model yüklendi: %s (%s)", config.MODEL_PATH.name, name)
        return model, device, name

    def _handle(self, result, frame: np.ndarray, names: dict) -> list[Detection]:
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []
        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        clss = boxes.cls.cpu().numpy().astype(int)
        # Takipçi bazı karelerde ID vermez; kutular yine de çizilir
        ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else [None] * len(xyxy)

        now = time.monotonic()
        out = []
        for box, conf, cls_idx, track_id in zip(xyxy, confs, clss, ids):
            cls = names[int(cls_idx)]
            b = tuple(float(v) for v in box)
            alert_id, is_new = self._deduper.assign(track_id, cls, b, now)
            out.append(Detection(b, cls, float(conf), alert_id))
            if is_new:
                self._raise_alert(alert_id, cls, float(conf), frame, b)
        return out

    def _raise_alert(self, alert_id, cls, conf, frame, box) -> None:
        rect = crop_box(frame.shape, box)
        if rect is None:
            return
        y1, y2, x1, x2 = rect
        crop = frame[y1:y2, x1:x2].copy()
        when = datetime.now()
        path = evidence_path(config.LOG_DIR, when, alert_id, cls, conf)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(path), crop):
                raise OSError("cv2.imwrite başarısız")
            info = config.class_info(cls)
            self._events.write(when, alert_id, cls, info.tr, info.severity, conf, path)
        except OSError:
            # Disk hatası alarmı engellemesin; panelde yine görünür
            log.exception("Kanıt kaydedilemedi: %s", path)
        self.new_alert.emit(Alert(alert_id, cls, conf, crop, when, str(path)))
