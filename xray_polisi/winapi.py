"""Windows'a özel yardımcılar."""
from __future__ import annotations

import logging
import os
import sys

from PyQt6.QtWidgets import QWidget

log = logging.getLogger(__name__)

WDA_EXCLUDEFROMCAPTURE = 0x11  # Windows 10 2004+


def exclude_from_capture(widget: QWidget) -> bool:
    """Pencereyi ekran yakalamasından gizler.

    Overlay'in çizdiği kutular bir sonraki karede modele girmez.
    Pencere gösterildikten sonra çağrılmalı (geçerli HWND gerekir).
    """
    if sys.platform != "win32":
        return False
    if os.environ.get("XRAY_POLISI_SHOW_IN_CAPTURE") == "1":
        # Demo videosu çekerken overlay görünsün; model de kutuları görür
        log.warning("XRAY_POLISI_SHOW_IN_CAPTURE=1: pencereler yakalamadan gizlenmiyor")
        return False
    import ctypes

    hwnd = int(widget.winId())
    ok = bool(ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))
    if not ok:
        log.warning("SetWindowDisplayAffinity başarısız (hata %d): %s",
                    ctypes.GetLastError(), widget.windowTitle() or type(widget).__name__)
    return ok


def beep(severity: str) -> None:
    """Önem derecesine göre sistem sesi (engellemez)."""
    if sys.platform == "win32":
        import winsound

        winsound.MessageBeep(winsound.MB_ICONHAND if severity == "high"
                             else winsound.MB_ICONEXCLAMATION)
    else:
        from PyQt6.QtWidgets import QApplication

        QApplication.beep()
