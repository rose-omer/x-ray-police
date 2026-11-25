"""Uygulama ayarları ve sınıf bilgileri.

Yollar betiğin klasörüne göre çözülür; uygulama hangi klasörden
başlatılırsa başlatılsın model ve kayıt klasörü bulunur.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Model ---
MODEL_PATH = BASE_DIR / "best.pt"
CONF_THRESHOLD = 0.35          # 0..1; düşük değer daha çok tespit, daha çok yanlış alarm
IMG_SIZE = 1280                # Model 640 px ile eğitildi; 1280 küçük nesnede daha çok buluyor
IMG_SIZE_CHOICES = (640, 960, 1280)

# --- Döngü ---
FRAME_INTERVAL_MS = 60         # Hedef kare aralığı (~16 FPS)
MAX_ERROR_BACKOFF_MS = 2000    # Art arda hatada en uzun bekleme

# --- Alarm tekrarını bastırma ---
DEDUP_IOU = 0.3                # Aynı sınıf + bu örtüşme = aynı nesne
DEDUP_TTL_S = 10.0             # Nesne bu süre görünmezse unutulur

# --- Arayüz ---
PANEL_WIDTH = 380              # Mantıksal piksel (Windows ölçeğinden bağımsız)
MAX_FEED_ITEMS = 150           # Panelde tutulan en çok kart
BEEP_COOLDOWN_S = 1.5

# --- Kayıt ---
LOG_DIR = BASE_DIR / "XRay_Ultra_Log"
EVENTS_FILE = "olaylar.csv"


@dataclass(frozen=True)
class ClassInfo:
    tr: str          # Türkçe ad
    severity: str    # "high" | "medium" | "low"


CLASSES: dict[str, ClassInfo] = {
    "Gun": ClassInfo("Silah", "high"),
    "Bullet": ClassInfo("Mermi", "high"),
    "Knife": ClassInfo("Bıçak", "high"),
    "Baton": ClassInfo("Cop", "medium"),
    "HandCuffs": ClassInfo("Kelepçe", "medium"),
    "Scissors": ClassInfo("Makas", "medium"),
    "Hammer": ClassInfo("Çekiç", "medium"),
    "Sprayer": ClassInfo("Sprey", "medium"),
    "Lighter": ClassInfo("Çakmak", "medium"),
    "Wrench": ClassInfo("İngiliz anahtarı", "low"),
    "Plier": ClassInfo("Pense", "low"),
    "Powerbank": ClassInfo("Powerbank", "low"),
}

SEVERITY_COLORS = {"high": "#ef4444", "medium": "#f59e0b", "low": "#38bdf8"}
SEVERITY_LABELS = {"high": "YÜKSEK", "medium": "ORTA", "low": "DÜŞÜK"}


def class_info(name: str) -> ClassInfo:
    """Bilinmeyen sınıfta adın kendisini ve orta önemi döndürür."""
    return CLASSES.get(name, ClassInfo(name, "medium"))


def tr_upper(text: str) -> str:
    """Türkçe büyük harf: 'Silah' -> 'SİLAH', 'Çakmak' -> 'ÇAKMAK'."""
    return text.replace("i", "İ").replace("ı", "I").upper()
