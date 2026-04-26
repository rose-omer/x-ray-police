import sys
import cv2
import numpy as np
import os
import time
from datetime import datetime
from mss import mss
from ultralytics import YOLO
import torch
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                             QScrollArea, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QImage, QPixmap, QFont

"""
xray-detect.py

Bu dosya ekran görüntüsü alıp, yüklenen YOLO modeli ile
gerçek zamanlı nesne takibi yapar ve tespit edilen kesitleri
sağ panelde kayıt/önizleme olarak gösterir. Yorumlar Türkçe olarak
eklenmiştir — ana hedef: kodu anlaşılır kılmak.
"""

# --- ULTRA HASSAS AYARLAR ---
# Kullanılacak model dosyası (Torch .pt formatında)
MODEL_PATH = 'best.pt'
# Tespit edilen nesnelerin kırpılmış görsellerinin kaydedileceği klasör
LOG_FOLDER = "XRay_Ultra_Log"
# Modelin kabul eşiği; düşükçe daha fazla detayı kabul eder fakat
# yanlış pozitif artabilir. (0..1 arası)
CONF_THRESHOLD = 0.35 
# Modelin giriş img boyutu. Yüksek değer küçük/uzaktaki nesnileri yakalamaya yardımcı olur.
IMG_SIZE = 1280        

# Sag panel genisligi (px)
PANEL_WIDTH = 360


if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

class DetectionItem(QFrame):
    """Sağ panelde görünen tek bir tespit kartı.

    - name: tespit edilen sınıf ismi
    - conf: güven skoru (yüzde olarak)
    - image_np: OpenCV formatında kırpılmış görsel (BGR)
    - obj_id: takip edilen nesnenin benzersiz ID'si
    """
    def __init__(self, name, conf, image_np, obj_id):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        # Daha dikkat çekici bir kırmızı/turuncu tema
        self.setStyleSheet("""
            background-color: #2c3e50; border: 2px solid #e67e22; 
            border-radius: 10px; margin: 4px; padding: 5px;
        """)
        layout = QHBoxLayout()

        rgb_image = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb_image.tobytes(), w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        pixmap = QPixmap.fromImage(qimg).scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio)
        img_label = QLabel()
        img_label.setPixmap(pixmap)
        
        info_label = QLabel(f"<font color='white' size='4'><b>{name.upper()}</b></font><br>"
                            f"<font color='#e67e22'>ID: {int(obj_id)}</font><br>"
                            f"<font color='#f1c40f'>Güven: %{conf:.1f}</font><br>"
                            f"<font color='#bdc3c7'>{datetime.now().strftime('%H:%M:%S')}</font>")
        
        layout.addWidget(img_label)
        layout.addWidget(info_label)
        self.setLayout(layout)

class SidePanel(QWidget):
    def __init__(self):
        """Sağ tarafta kayan log listesi ve başlık içeren GUI paneli."""
        super().__init__()
        self.setWindowTitle("Yapay Zeka Izleme")
        self.setFixedWidth(PANEL_WIDTH)
        self.setStyleSheet("background-color: #1a1a1a;")
        layout = QVBoxLayout()
        h = QLabel("ULTRA HASSASİYETLİ AKIŞ")
        h.setStyleSheet("color: #e67e22; font-weight: bold; font-size: 14px; padding: 15px; border-bottom: 2px solid #e67e22;")
        h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(h)
        self.scroll = QScrollArea()
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none;")
        layout.addWidget(self.scroll)
        self.setLayout(layout)

    def add_log(self, name, conf, crop_img, obj_id):
        # Yeni tespit kartını en üste ekle
        item = DetectionItem(name, conf, crop_img, obj_id)
        self.scroll_layout.insertWidget(0, item)

class XRayOverlay(QWidget):
    def __init__(self, panel_ref):
        """Ana overlay penceresi: model yüklenir, ekran yakalanır ve
        tespit sonuçları çizilir.

        - panel_ref: Sağ panel GUI örneği; yeni tespitleri burada gösteririz.
        """
        super().__init__()
        print("Ultra Mod Baslatiliyor (1280px)...")

        # YOLO modelini yükle (ağırlık dosyası MODEL_PATH ile belirtilir)
        self.model = YOLO(MODEL_PATH)
        # GPU varsa otomatik kullan (yoksa CPU)
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.panel = panel_ref

        # MSS ile bir monitör alanı belirle (ilk monitör)
        with mss() as sct:
            mon = sct.monitors[1]
            self.full_w, self.full_h = mon["width"], mon["height"]
            self.sx, self.sy = mon.get("left", 0), mon.get("top", 0)

            # Sag panel ekranin tamamini kaplasin, isleme alanina dahil olmasin
            self.panel_width = min(PANEL_WIDTH, self.full_w)
            self.sw = max(1, self.full_w - self.panel_width)
            self.sh = self.full_h
            self.area = {
                "left": self.sx,
                "top": self.sy,
                "width": self.sw,
                "height": self.sh,
            }

        # Kaydedilmiş tespit ID'lerini tekrar kaydetmemek için takip
        self.logged_ids = set()
        # Ekrana çizmek için son sonuçları burada tutarız
        self.results_data = []

        # Overlay penceresinin görünüm özellikleri
        # Overlay'i isleme alanina yerleştir (sag panel haric)
        self.setGeometry(self.sx, self.sy, self.sw, self.sh)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # DPI ölçeklemesi (Windows %125/%150 gibi durumlar için)
        self.dpi_scale = self._get_dpi_scale()

        self.sct = mss()
        self.timer = QTimer()
        self.timer.timeout.connect(self.process)
        # Döngü aralığı (ms): 60ms -> ~16 FPS, CPU kullanımını dengelemek için
        self.timer.start(60) 

    def _get_dpi_scale(self):
        app = QApplication.instance()
        if app is None:
            return 1.0

        screen = app.screenAt(QPoint(self.sx + 1, self.sy + 1))
        if screen is None:
            screen = app.primaryScreen()
        return float(screen.devicePixelRatio()) if screen else 1.0

    def process(self):
        # Ekrandan bir kare al
        img = np.array(self.sct.grab(self.area))
        # MSS döndürdüğü görüntü BGRA formatında gelir; BGR'ye çevir
        frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # Model ile takip yap (track: nesne kimliklendirme + id takibi)
        # imgsz ile daha büyük boyutta inceleme yapılır (küçük nesniler için)
        results = self.model.track(
            frame,
            conf=CONF_THRESHOLD,
            imgsz=IMG_SIZE,
            persist=True,
            verbose=False,
            device=self.device,
        )

        temp = []
        # Eğer kutular varsa onları CPU'ya çek ve numpy'a çevir
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy()
            scores = results[0].boxes.conf.cpu().numpy()
            clss = results[0].boxes.cls.cpu().numpy()

            for box, obj_id, conf, cls in zip(boxes, ids, scores, clss):
                name = self.model.names[int(cls)]
                # Çizimde DPI farkını telafi etmek için ölçek uygula
                draw_box = box / self.dpi_scale if self.dpi_scale != 1.0 else box
                temp.append((draw_box, obj_id, conf, name))


                # Yeni bir ID görmüşsek, kırpımı kaydet ve sağ panele ekle
                if obj_id not in self.logged_ids:
                    x1, y1, x2, y2 = box
                    crop = frame[max(0, int(y1)):min(self.sh, int(y2)), 
                                 max(0, int(x1)):min(self.sw, int(x2))]
                    if crop.size > 0:
                        # Panelde görsel ve meta göster
                        self.panel.add_log(name, conf*100, crop, obj_id)
                        # Diskte log klasörüne kaydet
                        cv2.imwrite(f"{LOG_FOLDER}/ID_{int(obj_id)}_{name}_{datetime.now().strftime('%H%M%S')}.jpg", crop)
                        self.logged_ids.add(obj_id)

        # Çizim için sonuçları sakla ve yeniden çiz
        self.results_data = temp
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for box, obj_id, conf, name in self.results_data:
            x1, y1, x2, y2 = box
            # Turuncu renk teması
            pen = QPen(QColor(230, 126, 34), 3) 
            painter.setPen(pen)
            painter.drawRect(int(x1), int(y1), int(x2-x1), int(y2-y1))
            
            # Etiketi ekran dışına taşmayacak şekilde konumlandır
            label_text = f"{name.upper()} ID:{int(obj_id)}"
            label_w, label_h = 180, 28
            lx = max(0, min(int(x1), self.sw - label_w))
            ly = max(0, min(int(y1) - label_h, self.sh - label_h))

            painter.fillRect(lx, ly, label_w, label_h, QColor(230, 126, 34))
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            painter.drawText(lx + 5, ly + 20, label_text)

        # Eğer istenirse burada ek bilgi (gösterge, FPS vb.) çizilebilir.

if __name__ == '__main__':
    # Uygulama başlatma
    app = QApplication(sys.argv)
    p = SidePanel()
    # Overlay penceresini oluştur ve göster
    o = XRayOverlay(p)
    # Sag paneli ekranin sagina yapistir ve boydan kaplat
    p.setFixedHeight(o.full_h)
    p.move(o.sx + o.full_w - p.width(), o.sy)
    p.show()
    o.show()
    # Qt uygulama döngüsünü başlat
    sys.exit(app.exec())