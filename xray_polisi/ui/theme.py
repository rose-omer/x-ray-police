"""Polis merkezi teması: lacivert zemin, siren mavisi + alarm kırmızısı."""

BG = "#0a1430"          # derin lacivert
SURFACE = "#0f1d42"
SURFACE_2 = "#152a5a"
BORDER = "#1f3670"
TEXT = "#e8eefc"
MUTED = "#8ea2cf"
ACCENT = "#dc2626"      # alarm kırmızısı (ana vurgu)
ACCENT_HOVER = "#ef4444"
POLICE_BLUE = "#2563eb" # siren mavisi (ikinci vurgu)
OK = "#22c55e"

FONT = "Segoe UI"


def rgba(hex_color: str, alpha: float) -> str:
    """'#rrggbb' -> 'rgba(r,g,b,a)'. Qt 8 haneli hex'i #AARRGGBB okur; bu yüzden rgba."""
    c = hex_color.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


_RED_TINT = rgba(ACCENT, 0.18)
_BLUE_TINT = rgba(POLICE_BLUE, 0.18)

QSS = f"""
QWidget#panel {{ background: {BG}; }}
QWidget {{ color: {TEXT}; font-family: "{FONT}"; font-size: 13px; }}
QLabel {{ background: transparent; }}

/* --- siren şeridi --- */
QFrame#sirenBlue {{ background: {POLICE_BLUE}; border: none; }}
QFrame#sirenRed {{ background: {ACCENT}; border: none; }}

/* --- başlık --- */
QFrame#header {{ background: {SURFACE}; border-bottom: 1px solid {BORDER}; }}
QLabel#logo {{ min-width: 40px; max-width: 40px; min-height: 40px; max-height: 40px; }}
QLabel#brand {{ font-size: 18px; font-weight: 800; letter-spacing: 0.4px; }}
QLabel#tagline {{ color: {MUTED}; font-size: 11px; letter-spacing: 0.3px; }}
QLabel#pill {{
    border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: 800;
    letter-spacing: 0.8px;
}}
QLabel#pill[state="loading"] {{ background: {SURFACE_2}; color: {MUTED}; }}
QLabel#pill[state="active"]  {{ background: {rgba(OK, 0.16)}; color: {OK}; }}
QLabel#pill[state="paused"]  {{ background: {_BLUE_TINT}; color: #7fa6ff; }}
QLabel#pill[state="error"]   {{ background: {_RED_TINT}; color: #ff7070; }}

/* --- alarm şeridi --- */
QFrame#banner {{ border-radius: 6px; }}
QLabel#bannerTitle {{ color: white; font-size: 14px; font-weight: 800; letter-spacing: 0.4px; }}
QLabel#bannerSub {{ color: rgba(255,255,255,0.88); font-size: 11px; }}

/* --- göstergeler --- */
QFrame#tile {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 6px; }}
QLabel#tileValue {{ font-size: 18px; font-weight: 800; }}
QLabel#tileLabel {{ color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 1px; }}

/* --- bölüm --- */
QLabel#section {{ color: {MUTED}; font-size: 10px; font-weight: 800; letter-spacing: 1.4px; }}
QLabel#fieldLabel {{ color: {MUTED}; font-size: 12px; }}
QLabel#fieldValue {{ font-weight: 800; }}
QLabel#hint {{ color: #5f73a3; font-size: 11px; }}
QLabel#empty {{ color: {MUTED}; font-size: 12px; padding: 28px 16px; }}

/* --- düğmeler --- */
QPushButton {{
    background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 6px;
    padding: 8px 10px; font-weight: 700;
}}
QPushButton:hover {{ background: #1b3370; border-color: #2c4a91; }}
QPushButton:pressed {{ background: #11234d; }}
QPushButton:focus {{ border-color: {POLICE_BLUE}; }}
QPushButton#primary {{ background: {ACCENT}; color: white; border-color: {ACCENT}; }}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#primary[paused="true"] {{ background: {POLICE_BLUE}; border-color: {POLICE_BLUE}; }}
QPushButton#ghost {{ background: transparent; border-color: transparent; color: {MUTED}; padding: 4px 8px; }}
QPushButton#ghost:hover {{ color: {TEXT}; background: {SURFACE_2}; }}
QPushButton#danger {{ background: transparent; color: #ff6b6b; border-color: {rgba(ACCENT, 0.45)}; }}
QPushButton#danger:hover {{ background: {_RED_TINT}; }}
QPushButton#seg, QPushButton#segFirst, QPushButton#segLast {{ padding: 7px 0; }}
QPushButton#seg {{ border-radius: 0; }}
QPushButton#segFirst {{ border-top-right-radius: 0; border-bottom-right-radius: 0; }}
QPushButton#segLast {{ border-top-left-radius: 0; border-bottom-left-radius: 0; }}
QPushButton#seg:checked, QPushButton#segFirst:checked, QPushButton#segLast:checked {{
    background: {_RED_TINT}; color: #ff8a8a; border-color: {ACCENT};
}}

/* --- giriş öğeleri --- */
QComboBox {{
    background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 7px 10px;
}}
QComboBox:focus {{ border-color: {POLICE_BLUE}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_2}; border: 1px solid {BORDER}; selection-background-color: #1d3a80;
    outline: none;
}}
QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {TEXT}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
}}
QSlider::handle:horizontal:focus {{ background: {ACCENT_HOVER}; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 32px; height: 18px; border-radius: 9px; background: {BORDER}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; }}

/* --- akış --- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 3px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

QFrame#card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 6px; }}
QFrame#card:hover {{ border-color: #2f4f9a; }}
QFrame#card[fresh="true"] {{ border-color: {ACCENT}; background: #1a1f45; }}
QLabel#thumb {{ background: #050a18; border-radius: 4px; }}
QLabel#cardTitle {{ font-size: 14px; font-weight: 800; }}
QLabel#cardMeta {{ color: {MUTED}; font-size: 11px; }}
QLabel#chip {{ border-radius: 3px; padding: 1px 6px; font-size: 9px; font-weight: 800;
               letter-spacing: 0.8px; }}
QProgressBar {{ background: {BORDER}; border: none; border-radius: 2px; max-height: 4px; }}

QFrame#footer {{ background: {SURFACE}; border-top: 1px solid {BORDER}; }}
QFrame#divider {{ background: {BORDER}; max-height: 1px; min-height: 1px; border: none; }}
"""
