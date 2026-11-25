"""Renk değişkenleri ve Qt stil sayfası (koyu güvenlik konsolu teması)."""

BG = "#0d1016"
SURFACE = "#151922"
SURFACE_2 = "#1c212c"
BORDER = "#262c38"
TEXT = "#e7eaf0"
MUTED = "#8a93a6"
ACCENT = "#f59e0b"
DANGER = "#ef4444"
OK = "#22c55e"

FONT = "Segoe UI"

QSS = f"""
QWidget#panel {{ background: {BG}; }}
QWidget {{ color: {TEXT}; font-family: "{FONT}"; font-size: 13px; }}
QLabel {{ background: transparent; }}

/* --- başlık --- */
QFrame#header {{ background: {SURFACE}; border-bottom: 1px solid {BORDER}; }}
QLabel#logo {{ min-width: 36px; max-width: 36px; min-height: 36px; max-height: 36px; }}
QLabel#brand {{ font-size: 17px; font-weight: 700; letter-spacing: 0.3px; }}
QLabel#tagline {{ color: {MUTED}; font-size: 11px; }}
QLabel#pill {{
    border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 700;
    letter-spacing: 0.6px;
}}
QLabel#pill[state="loading"] {{ background: #2a2f3b; color: {MUTED}; }}
QLabel#pill[state="active"]  {{ background: rgba(34,197,94,0.15); color: {OK}; }}
QLabel#pill[state="paused"]  {{ background: rgba(245,158,11,0.15); color: {ACCENT}; }}
QLabel#pill[state="error"]   {{ background: rgba(239,68,68,0.18); color: {DANGER}; }}

/* --- alarm şeridi --- */
QFrame#banner {{ border-radius: 10px; }}
QLabel#bannerTitle {{ color: white; font-size: 14px; font-weight: 700; }}
QLabel#bannerSub {{ color: rgba(255,255,255,0.85); font-size: 11px; }}

/* --- göstergeler --- */
QFrame#tile {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; }}
QLabel#tileValue {{ font-size: 17px; font-weight: 700; }}
QLabel#tileLabel {{ color: {MUTED}; font-size: 10px; font-weight: 600; letter-spacing: 0.8px; }}

/* --- bölüm --- */
QLabel#section {{ color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 1.2px; }}
QLabel#fieldLabel {{ color: {MUTED}; font-size: 12px; }}
QLabel#fieldValue {{ font-weight: 700; }}
QLabel#hint {{ color: #5d6578; font-size: 11px; }}
QLabel#empty {{ color: {MUTED}; font-size: 12px; padding: 28px 16px; }}

/* --- düğmeler --- */
QPushButton {{
    background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 7px 10px; font-weight: 600;
}}
QPushButton:hover {{ background: #232937; border-color: #343b4a; }}
QPushButton:pressed {{ background: #1a1f29; }}
QPushButton:focus {{ border-color: {ACCENT}; }}
QPushButton#primary {{ background: {ACCENT}; color: #111; border-color: {ACCENT}; }}
QPushButton#primary:hover {{ background: #fbbf24; }}
QPushButton#primary[paused="true"] {{ background: {OK}; border-color: {OK}; }}
QPushButton#ghost {{ background: transparent; border-color: transparent; color: {MUTED}; padding: 4px 8px; }}
QPushButton#ghost:hover {{ color: {TEXT}; background: {SURFACE_2}; }}
QPushButton#danger {{ background: transparent; color: {DANGER}; border-color: rgba(239,68,68,0.35); }}
QPushButton#danger:hover {{ background: rgba(239,68,68,0.12); }}
QPushButton#seg {{ border-radius: 0; padding: 6px 0; }}
QPushButton#seg:checked {{ background: rgba(245,158,11,0.16); color: {ACCENT}; border-color: {ACCENT}; }}
QPushButton#segFirst {{ border-top-right-radius: 0; border-bottom-right-radius: 0; padding: 6px 0; }}
QPushButton#segLast {{ border-top-left-radius: 0; border-bottom-left-radius: 0; padding: 6px 0; }}
QPushButton#segFirst:checked, QPushButton#segLast:checked {{
    background: rgba(245,158,11,0.16); color: {ACCENT}; border-color: {ACCENT};
}}

/* --- giriş öğeleri --- */
QComboBox {{
    background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px 10px;
}}
QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_2}; border: 1px solid {BORDER}; selection-background-color: #2b3242;
    outline: none;
}}
QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {TEXT}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
}}
QSlider::handle:horizontal:focus {{ background: {ACCENT}; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 32px; height: 18px; border-radius: 9px; background: {BORDER};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; }}

/* --- akış --- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #2b3140; border-radius: 3px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

QFrame#card {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px;
}}
QFrame#card:hover {{ border-color: #3a4254; }}
QFrame#card[fresh="true"] {{ border-color: {ACCENT}; background: #1b1d22; }}
QLabel#thumb {{ background: #07090c; border-radius: 6px; }}
QLabel#cardTitle {{ font-size: 14px; font-weight: 700; }}
QLabel#cardMeta {{ color: {MUTED}; font-size: 11px; }}
QLabel#chip {{ border-radius: 6px; padding: 1px 6px; font-size: 9px; font-weight: 800;
               letter-spacing: 0.6px; }}
QProgressBar {{ background: {BORDER}; border: none; border-radius: 2px; max-height: 4px; }}

QFrame#footer {{ background: {SURFACE}; border-top: 1px solid {BORDER}; }}
QFrame#divider {{ background: {BORDER}; max-height: 1px; min-height: 1px; border: none; }}
"""
