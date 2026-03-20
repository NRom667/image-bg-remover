from __future__ import annotations

from PySide6.QtGui import QColor, QFont

FONT_FAMILY = "Segoe UI"

SPACE_4 = 4
SPACE_8 = 8
SPACE_12 = 12
SPACE_16 = 16
SPACE_20 = 20
SPACE_24 = 24
SPACE_32 = 32

RADIUS_XS = 8
RADIUS_SM = 12
RADIUS_MD = 16
RADIUS_LG = 20

CONTROL_HEIGHT = 42
SIDEBAR_WIDTH = 272

COLOR_BG_APP = "#f4efe6"
COLOR_BG_PANEL = "#fffbf5"
COLOR_BG_CARD = "#fffdfa"
COLOR_BG_BUTTON = "#fbf3e7"
COLOR_BG_BUTTON_PRESSED = "#f1e2cf"
COLOR_BG_SUBTLE = "#f7f1e7"
COLOR_BG_HOVER = "#fff4e3"
COLOR_BG_DISABLED = "#f1ebe2"

COLOR_BORDER_DEFAULT = "#d9c4a8"
COLOR_BORDER_STRONG = "#b99567"
COLOR_BORDER_FOCUS = "#b88952"
COLOR_BORDER_DISABLED = "#ded5c8"

COLOR_TEXT_PRIMARY = "#1f2e3d"
COLOR_TEXT_SECONDARY = "#526272"
COLOR_TEXT_MUTED = "#7c8894"
COLOR_TEXT_DISABLED = "#a3acb5"
COLOR_TEXT_ON_ACCENT = "#fffdf9"

COLOR_ACCENT_PRIMARY = "#b7793e"
COLOR_ACCENT_PRIMARY_HOVER = "#9f6430"
COLOR_ACCENT_SOFT = "#f3e2cc"

COLOR_SUCCESS = "#2f855a"
COLOR_WARNING = "#c97a1a"
COLOR_ERROR = "#c53030"
COLOR_INFO = "#2b6cb0"

COLOR_POINT_FOREGROUND = "#d64545"
COLOR_POINT_BACKGROUND = "#2b6cb0"
COLOR_POINT_GLYPH = "#ffffff"

COLOR_CHECKER_LIGHT = "#fbf7ef"
COLOR_CHECKER_DARK = "#efe3d0"


def create_app_font() -> QFont:
    font = QFont("Segoe UI")
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    font.setPointSize(10)
    return font


def message_box_stylesheet() -> str:
    return f"""
    QMessageBox {{
        background: {COLOR_BG_APP};
    }}
    QMessageBox QLabel {{
        color: {COLOR_TEXT_PRIMARY};
        font-family: \"{FONT_FAMILY}\";
        font-size: 14px;
    }}
    QMessageBox QPushButton {{
        min-width: 88px;
        min-height: 38px;
        border-radius: {RADIUS_SM}px;
        border: 1px solid {COLOR_BORDER_DEFAULT};
        padding: {SPACE_8}px {SPACE_16}px;
        background: {COLOR_BG_BUTTON};
        color: {COLOR_TEXT_PRIMARY};
        font-family: \"{FONT_FAMILY}\";
        font-size: 14px;
        font-weight: 600;
    }}
    QMessageBox QPushButton:hover {{
        border: 1px solid {COLOR_BORDER_STRONG};
        background: {COLOR_BG_HOVER};
    }}
    QMessageBox QPushButton:pressed {{
        background: {COLOR_BG_BUTTON_PRESSED};
        border: 1px solid {COLOR_BORDER_STRONG};
        padding-top: 9px;
        padding-bottom: 7px;
    }}
    """


def main_window_stylesheet() -> str:
    return f"""
    QMainWindow {{
        background: {COLOR_BG_APP};
    }}
    QWidget#windowRoot {{
        background: {COLOR_BG_APP};
    }}
    QScrollArea#windowScrollArea {{
        border: none;
        background: {COLOR_BG_APP};
    }}
    QScrollArea#sidebarScrollArea {{
        border: none;
        background: {COLOR_BG_APP};
    }}
    QWidget#scrollContent {{
        background: {COLOR_BG_APP};
    }}
    QFrame#sidebar {{
        background: {COLOR_BG_PANEL};
        border: 1px solid {COLOR_BORDER_DEFAULT};
        border-radius: {RADIUS_LG}px;
    }}
    QLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-family: \"{FONT_FAMILY}\";
        font-size: 14px;
    }}
    QLabel#sidebarTitle {{
        color: {COLOR_TEXT_PRIMARY};
        font-family: \"{FONT_FAMILY}\";
        font-size: 24px;
        font-weight: 700;
    }}
    QLabel#instructionLabel, QLabel#metaLabel {{
        color: {COLOR_TEXT_SECONDARY};
        background: {COLOR_BG_SUBTLE};
        border: 1px solid {COLOR_BORDER_DEFAULT};
        border-radius: {RADIUS_SM}px;
        padding: {SPACE_12}px;
    }}
    QLabel#statusGroupLabel {{
        color: {COLOR_TEXT_MUTED};
        font-size: 13px;
        font-weight: 500;
    }}
    QGroupBox {{
        color: {COLOR_TEXT_PRIMARY};
        font-family: \"{FONT_FAMILY}\";
        font-size: 13px;
        font-weight: 600;
        border: 1px solid {COLOR_BORDER_DEFAULT};
        border-radius: {RADIUS_MD}px;
        margin-top: 10px;
        padding: {SPACE_16}px {SPACE_12}px {SPACE_12}px {SPACE_12}px;
        background: {COLOR_BG_CARD};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: {SPACE_12}px;
        padding: 0 {SPACE_4}px;
    }}
    QPushButton, QComboBox {{
        min-height: {CONTROL_HEIGHT}px;
        border-radius: {RADIUS_SM}px;
        border: 1px solid {COLOR_BORDER_DEFAULT};
        padding: {SPACE_8}px {SPACE_12}px;
        background: {COLOR_BG_BUTTON};
        color: {COLOR_TEXT_PRIMARY};
        font-family: \"{FONT_FAMILY}\";
        font-size: 16px;
    }}
    QPushButton {{
        font-weight: 500;
    }}
    QPushButton:hover, QComboBox:hover {{
        border: 1px solid {COLOR_BORDER_STRONG};
        background: {COLOR_BG_HOVER};
    }}
    QPushButton:pressed {{
        background: {COLOR_BG_BUTTON_PRESSED};
        border: 1px solid {COLOR_BORDER_STRONG};
        padding-top: 9px;
        padding-bottom: 7px;
    }}
    QPushButton:focus, QComboBox:focus {{
        border: 2px solid {COLOR_BORDER_FOCUS};
    }}
    QPushButton:disabled, QComboBox:disabled {{
        color: {COLOR_TEXT_DISABLED};
        background: {COLOR_BG_DISABLED};
        border: 1px solid {COLOR_BORDER_DISABLED};
    }}
    QPushButton#tertiaryButton {{
        background: {COLOR_BG_PANEL};
    }}
    QComboBox {{
        padding-right: 36px;
    }}
    QComboBox QAbstractItemView {{
        background: {COLOR_BG_CARD};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_DEFAULT};
        border-radius: {RADIUS_SM}px;
        padding: 6px;
        selection-background-color: {COLOR_ACCENT_SOFT};
        selection-color: {COLOR_TEXT_PRIMARY};
        outline: 0;
    }}
    QComboBox::drop-down {{
        width: 28px;
        border: none;
    }}
    QScrollBar:vertical {{
        background: {COLOR_BG_SUBTLE};
        width: 14px;
        margin: 8px 4px 8px 0;
        border-radius: 7px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLOR_BORDER_STRONG};
        min-height: 32px;
        border-radius: 7px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QStatusBar {{
        background: {COLOR_BG_PANEL};
        color: {COLOR_TEXT_SECONDARY};
        font-family: \"{FONT_FAMILY}\";
    }}
    """


def dialog_stylesheet() -> str:
    return f"""
    QDialog {{
        background: {COLOR_BG_APP};
    }}
    QFrame {{
        background: {COLOR_BG_CARD};
        border: 1px solid {COLOR_BORDER_DEFAULT};
        border-radius: {RADIUS_MD}px;
    }}
    QLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-family: \"{FONT_FAMILY}\";
        font-size: 13px;
    }}
    QPushButton {{
        min-height: 40px;
        border-radius: {RADIUS_SM}px;
        border: 1px solid {COLOR_BORDER_DEFAULT};
        padding: {SPACE_8}px {SPACE_12}px;
        background: {COLOR_BG_BUTTON};
        color: {COLOR_TEXT_PRIMARY};
        font-family: \"{FONT_FAMILY}\";
        font-size: 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        border: 1px solid {COLOR_BORDER_STRONG};
        background: {COLOR_BG_HOVER};
    }}
    QPushButton:pressed {{
        background: {COLOR_BG_BUTTON_PRESSED};
        border: 1px solid {COLOR_BORDER_STRONG};
        padding-top: 9px;
        padding-bottom: 7px;
    }}
    QPushButton:disabled {{
        color: {COLOR_TEXT_DISABLED};
        background: {COLOR_BG_DISABLED};
        border: 1px solid {COLOR_BORDER_DISABLED};
    }}
    QProgressBar {{
        min-height: 24px;
        border: 1px solid {COLOR_BORDER_DEFAULT};
        border-radius: 10px;
        background: {COLOR_BG_CARD};
        text-align: center;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QProgressBar::chunk {{
        border-radius: 9px;
        background: {COLOR_ACCENT_PRIMARY};
    }}
    """


def qcolor(value: str) -> QColor:
    return QColor(value)


