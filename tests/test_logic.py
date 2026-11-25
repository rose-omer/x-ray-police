from datetime import datetime

import pytest

from xray_polisi.logic import (AlertDeduper, EventLog, ScreenMap, crop_box, evidence_path,
                           iou, match_monitor)


# ------------------------------------------------------------------ iou

@pytest.mark.parametrize("a,b,expected", [
    ((0, 0, 10, 10), (0, 0, 10, 10), 1.0),
    ((0, 0, 10, 10), (20, 20, 30, 30), 0.0),
    ((0, 0, 10, 10), (5, 0, 15, 10), 50 / 150),
    ((0, 0, 10, 10), (10, 0, 20, 10), 0.0),   # yalnız kenar değiyor
], ids=["ayni", "ayrik", "yarim", "kenar"])
def test_iou(a, b, expected):
    assert iou(a, b) == pytest.approx(expected)


# ------------------------------------------------------------ ScreenMap

@pytest.fixture
def map_125():
    # 1920x1080 mantıksal, %125 ölçek -> 2400x1350 fiziksel
    return ScreenMap(0, 0, 1920, 1080, 0, 0, 2400, 1350)


def test_scale(map_125):
    assert map_125.scale == pytest.approx(1.25)


def test_to_physical_scales_region(map_125):
    assert map_125.to_physical(0, 0, 1540, 1080) == {
        "left": 0, "top": 0, "width": 1925, "height": 1350}


def test_to_physical_clips_to_monitor(map_125):
    r = map_125.to_physical(1800, 1000, 500, 500)
    assert r["left"] + r["width"] == 2400
    assert r["top"] + r["height"] == 1350


def test_box_to_local_roundtrip(map_125):
    region = map_125.to_physical(100, 50, 800, 600)
    local = map_125.box_to_local((0, 0, 125, 125), region)
    # Fiziksel piksele yuvarlama en çok 1 mantıksal piksel kaydırır
    assert local == pytest.approx((100, 50, 200, 150), abs=1)


def test_second_monitor_offset():
    m = ScreenMap(1920, 0, 1920, 1080, 1920, 0, 1920, 1080)
    assert m.to_physical(1920, 0, 100, 100) == {
        "left": 1920, "top": 0, "width": 100, "height": 100}


# --------------------------------------------------------- match_monitor

MONITORS = [
    {"left": 0, "top": 0, "width": 1920, "height": 1080},
    {"left": 1920, "top": 0, "width": 1920, "height": 1080},
    {"left": -1920, "top": 0, "width": 1920, "height": 1080},
]


def test_match_monitor_by_origin():
    assert match_monitor((1920, 0, 1920, 1080), 1.0, MONITORS) is MONITORS[1]


def test_match_monitor_scaled():
    mons = [{"left": 0, "top": 0, "width": 2400, "height": 1350}]
    assert match_monitor((0, 0, 1920, 1080), 1.25, mons) is mons[0]


def test_match_monitor_none():
    assert match_monitor((5000, 0, 800, 600), 1.0, MONITORS) is None


# --------------------------------------------------------- AlertDeduper

def test_same_track_is_not_new():
    d = AlertDeduper()
    assert d.assign(7, "Gun", (0, 0, 10, 10), 0.0) == (1, True)
    assert d.assign(7, "Gun", (1, 1, 11, 11), 0.1) == (1, False)


def test_new_track_same_object_is_suppressed():
    """Takipçi ID değiştirince tekrar alarm çıkmamalı (Baton hatası)."""
    d = AlertDeduper(iou_threshold=0.3, ttl=10)
    d.assign(2, "Baton", (0, 0, 100, 20), 0.0)
    assert d.assign(3, "Baton", (2, 0, 102, 20), 2.0) == (1, False)


def test_different_class_is_new():
    d = AlertDeduper()
    d.assign(1, "Gun", (0, 0, 10, 10), 0.0)
    assert d.assign(2, "Knife", (0, 0, 10, 10), 0.0) == (2, True)


def test_untracked_detection_gets_stable_id():
    d = AlertDeduper()
    assert d.assign(None, "Gun", (0, 0, 10, 10), 0.0) == (1, True)
    assert d.assign(None, "Gun", (0, 0, 10, 10), 0.1) == (1, False)
    assert d.assign(5, "Gun", (0, 0, 10, 10), 0.2) == (1, False)


def test_expired_object_alarms_again_and_memory_is_freed():
    d = AlertDeduper(ttl=10)
    d.assign(1, "Gun", (0, 0, 10, 10), 0.0)
    assert d.assign(1, "Gun", (0, 0, 10, 10), 11.0) == (2, True)
    assert len(d) == 1


def test_reset_keeps_counter():
    d = AlertDeduper()
    d.assign(1, "Gun", (0, 0, 10, 10), 0.0)
    d.reset()
    assert d.assign(1, "Gun", (0, 0, 10, 10), 0.0) == (2, True)


# ----------------------------------------------------------------- kayıt

def test_crop_box_clips():
    assert crop_box((100, 200, 3), (-5, -5, 250, 50)) == (0, 50, 0, 200)


def test_crop_box_empty():
    assert crop_box((100, 200, 3), (300, 0, 400, 50)) is None


def test_evidence_path_has_date_and_alert():
    p = evidence_path(__import__("pathlib").Path("log"),
                      datetime(2026, 11, 25, 14, 32, 5), 3, "Gun", 0.871)
    assert p.parent.name == "2026-11-25"
    assert p.name == "143205_A0003_Gun_87.jpg"


def test_event_log_writes_header_once(tmp_path):
    log = EventLog("olaylar.csv")
    img = tmp_path / "2026-11-25" / "x.jpg"
    when = datetime(2026, 11, 25, 14, 0, 0)
    log.write(when, 1, "Gun", "Silah", "high", 0.9, img)
    path = log.write(when, 2, "Knife", "Bıçak", "high", 0.8, img)
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0].startswith("zaman;alarm_no")
    assert len(lines) == 3
    assert "Bıçak" in lines[2]


@pytest.mark.parametrize("text,expected", [("Silah", "SİLAH"), ("Bıçak", "BIÇAK"),
                                           ("İngiliz anahtarı", "İNGİLİZ ANAHTARI")])
def test_tr_upper(text, expected):
    from xray_polisi.config import tr_upper
    assert tr_upper(text) == expected
