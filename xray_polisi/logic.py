"""Qt ve modelden bağımsız saf mantık: koordinat dönüşümü, alarm tekrarını
bastırma, kayıt yolları. Birim testleri bu modülü sınar."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

Box = tuple[float, float, float, float]  # x1, y1, x2, y2


def iou(a: Box, b: Box) -> float:
    """İki kutunun kesişim / birleşim oranı (0..1)."""
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter == 0.0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)


# ---------------------------------------------------------------- ekran eşleme

@dataclass(frozen=True)
class ScreenMap:
    """Bir monitörün Qt (mantıksal) ve mss (fiziksel) koordinatları.

    Windows ölçeği %125 ise fiziksel genişlik mantıksalın 1.25 katıdır.
    Qt pencereleri mantıksal, mss yakalaması fiziksel piksel kullanır.
    """
    log_x: int
    log_y: int
    log_w: int
    log_h: int
    phys_left: int
    phys_top: int
    phys_w: int
    phys_h: int

    @property
    def scale(self) -> float:
        return self.phys_w / self.log_w if self.log_w else 1.0

    def to_physical(self, x: float, y: float, w: float, h: float) -> dict[str, int]:
        """Global mantıksal dikdörtgeni mss yakalama alanına çevirir."""
        s = self.scale
        left = self.phys_left + round((x - self.log_x) * s)
        top = self.phys_top + round((y - self.log_y) * s)
        width = max(1, round(w * s))
        height = max(1, round(h * s))
        # Monitör dışına taşmasın
        right = min(left + width, self.phys_left + self.phys_w)
        bottom = min(top + height, self.phys_top + self.phys_h)
        left = max(left, self.phys_left)
        top = max(top, self.phys_top)
        return {"left": left, "top": top,
                "width": max(1, right - left), "height": max(1, bottom - top)}

    def box_to_local(self, box: Box, region: dict[str, int]) -> Box:
        """Yakalanan karedeki kutuyu monitöre göre mantıksal koordinata çevirir."""
        s = self.scale
        ox = region["left"] - self.phys_left
        oy = region["top"] - self.phys_top
        return ((box[0] + ox) / s, (box[1] + oy) / s,
                (box[2] + ox) / s, (box[3] + oy) / s)

    def region_to_local(self, region: dict[str, int]) -> Box:
        """mss alanını monitöre göre mantıksal dikdörtgene çevirir."""
        return self.box_to_local((0, 0, region["width"], region["height"]), region)


def match_monitor(log_geo: tuple[int, int, int, int], dpr: float,
                  monitors: Sequence[dict[str, int]]) -> dict[str, int] | None:
    """Qt ekranına karşılık gelen mss monitörünü bulur.

    monitors: mss.monitors[1:] (tek tek monitörler).
    Önce sol-üst köşe eşleşmesi, sonra ölçekli köşe, sonra boyut aranır.
    """
    x, y, w, h = log_geo
    candidates = [
        lambda m: m["left"] == x and m["top"] == y,
        lambda m: m["left"] == round(x * dpr) and m["top"] == round(y * dpr),
        lambda m: m["width"] == round(w * dpr) and m["height"] == round(h * dpr),
    ]
    for test in candidates:
        found = [m for m in monitors if test(m)]
        if len(found) == 1:
            return found[0]
    return None


# --------------------------------------------------------- alarm tekrarı

@dataclass
class _Seen:
    alert_id: int
    cls: str
    box: Box
    last_seen: float


class AlertDeduper:
    """Takipçi ID'sinden bağımsız, kalıcı alarm numarası verir.

    ByteTrack nesneyi kısa süre kaybedince yeni ID açar. Aynı sınıf ve
    örtüşen kutu, son `ttl` saniyede görüldüyse eski alarma bağlanır;
    yeniden alarm üretilmez. Görünmeyen kayıtlar `ttl` sonra silinir,
    böylece bellek sınırlı kalır.
    """

    def __init__(self, iou_threshold: float = 0.3, ttl: float = 10.0) -> None:
        self.iou_threshold = iou_threshold
        self.ttl = ttl
        self._next_id = 1
        self._seen: dict[int, _Seen] = {}        # alert_id -> kayıt
        self._track_to_alert: dict[int, int] = {}

    def __len__(self) -> int:
        return len(self._seen)

    def reset(self) -> None:
        self._seen.clear()
        self._track_to_alert.clear()

    def assign(self, track_id: int | None, cls: str, box: Box,
               now: float) -> tuple[int, bool]:
        """(alarm_no, yeni_mi) döndürür."""
        self._prune(now)

        if track_id is not None:
            alert_id = self._track_to_alert.get(track_id)
            if alert_id is not None and alert_id in self._seen:
                self._touch(alert_id, box, now)
                return alert_id, False

        match = self._best_match(cls, box)
        if match is not None:
            if track_id is not None:
                self._track_to_alert[track_id] = match
            self._touch(match, box, now)
            return match, False

        alert_id = self._next_id
        self._next_id += 1
        self._seen[alert_id] = _Seen(alert_id, cls, box, now)
        if track_id is not None:
            self._track_to_alert[track_id] = alert_id
        return alert_id, True

    def _touch(self, alert_id: int, box: Box, now: float) -> None:
        entry = self._seen[alert_id]
        entry.box = box
        entry.last_seen = now

    def _best_match(self, cls: str, box: Box) -> int | None:
        best_id, best_iou = None, self.iou_threshold
        for entry in self._seen.values():
            if entry.cls != cls:
                continue
            score = iou(entry.box, box)
            if score >= best_iou:
                best_id, best_iou = entry.alert_id, score
        return best_id

    def _prune(self, now: float) -> None:
        stale = [k for k, v in self._seen.items() if now - v.last_seen > self.ttl]
        for k in stale:
            del self._seen[k]
        if stale:
            gone = set(stale)
            self._track_to_alert = {t: a for t, a in self._track_to_alert.items()
                                    if a not in gone}


# ---------------------------------------------------------------- kayıt

def crop_box(shape: tuple[int, ...], box: Box) -> tuple[int, int, int, int] | None:
    """Kutuyu görüntü sınırına kırpar; boşsa None. (y1, y2, x1, x2) döndürür."""
    h, w = shape[0], shape[1]
    x1, y1 = max(0, int(box[0])), max(0, int(box[1]))
    x2, y2 = min(w, int(box[2])), min(h, int(box[3]))
    if x2 <= x1 or y2 <= y1:
        return None
    return y1, y2, x1, x2


def evidence_path(log_dir: Path, when: datetime, alert_id: int,
                  cls: str, conf: float) -> Path:
    """Gün klasörü içinde benzersiz kanıt dosya yolu.

    Örnek: XRay_Ultra_Log/2026-11-25/143205_A0003_Gun_87.jpg
    """
    day = log_dir / when.strftime("%Y-%m-%d")
    name = f"{when.strftime('%H%M%S')}_A{alert_id:04d}_{cls}_{round(conf * 100)}.jpg"
    return day / name


class EventLog:
    """Gün klasörüne CSV olay günlüğü yazar (Excel için UTF-8 BOM)."""

    HEADER = ("zaman", "alarm_no", "sinif", "sinif_tr", "onem", "guven", "dosya")

    def __init__(self, file_name: str) -> None:
        self.file_name = file_name

    def write(self, when: datetime, alert_id: int, cls: str, cls_tr: str,
              severity: str, conf: float, image: Path) -> Path:
        path = image.parent / self.file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        new = not path.exists()
        with path.open("a", newline="", encoding="utf-8-sig" if new else "utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            if new:
                writer.writerow(self.HEADER)
            writer.writerow((when.isoformat(timespec="seconds"), alert_id, cls, cls_tr,
                             severity, f"{conf:.2f}", image.name))
        return path
