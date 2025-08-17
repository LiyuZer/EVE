from __future__ import annotations
from PySide6.QtGui import QPalette, QColor, QFontDatabase, QFont
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Modern visual palettes and utilities for Eve IDE
# Three variants: eve_modern, dragon_modern, light_modern

THEMES: dict[str, dict[str, str]] = {
    "eve_modern": {
        "bg": "#0b0f14", "bg_alt": "#111821", "elev": "#151d28", "sunken": "#0a0f14",
        "text": "#e8edf2", "muted": "#9aa7b3", "accent": "#59f3ff", "accent2": "#ff59f3",
        "warn": "#ffc857", "error": "#ff6b6b", "sel_bg": "#133a44", "sel_fg": "#dafaff",
        "focus": "#59f3ff", "border": "#1f2a36", "hover": "#1a2430",
    },
    "dragon_modern": {
        "bg": "#0c0a10", "bg_alt": "#14121b", "elev": "#181525", "sunken": "#0a0810",
        "text": "#f4efff", "muted": "#b6a9cf", "accent": "#ff6d00", "accent2": "#ff2e63",
        "warn": "#ffd166", "error": "#ff3b30", "sel_bg": "#2b1430", "sel_fg": "#ffe9fb",
        "focus": "#ff6d00", "border": "#251d32", "hover": "#1c1726",
    },
    "light_modern": {
        "bg": "#f8fafc", "bg_alt": "#ffffff", "elev": "#ffffff", "sunken": "#f2f5f8",
        "text": "#0b1220", "muted": "#57606a", "accent": "#2563eb", "accent2": "#7c3aed",
        "warn": "#b45309", "error": "#b91c1c", "sel_bg": "#e6f0ff", "sel_fg": "#0b1220",
        "focus": "#2563eb", "border": "#e5e7eb", "hover": "#f3f6fb",
    },
}


def _apply_fonts(app: QApplication) -> None:
    # Prefer a good monospace for editors (larger)
    for name in ["JetBrains Mono", "Fira Code", "SF Mono", "Consolas", "Menlo", "DejaVu Sans Mono"]:
        try:
            if QFontDatabase.hasFamily(name):
                app.setFont(QFont(name, 16), "QPlainTextEdit")
                app.setFont(QFont(name, 16), "QTextEdit")
                break
        except Exception:
            pass
    # Prefer a clean UI font for widgets (larger)
    for name in ["Inter", "SF Pro Text", "Segoe UI", "Roboto", "Helvetica Neue", "Noto Sans"]:
        try:
            if QFontDatabase.hasFamily(name):
                app.setFont(QFont(name, 13))
                break
        except Exception:
            pass


def apply_palette(app: QApplication, theme: str) -> None:
    t = theme if theme in THEMES else "eve_modern"
    p = THEMES[t]
    pal = app.palette()
    pal.setColor(QPalette.Window, QColor(p["bg"]))
    pal.setColor(QPalette.Base, QColor(p["bg_alt"]))
    pal.setColor(QPalette.AlternateBase, QColor(p["sunken"]))
    pal.setColor(QPalette.Text, QColor(p["text"]))
    pal.setColor(QPalette.WindowText, QColor(p["text"]))
    pal.setColor(QPalette.Button, QColor(p["elev"]))
    pal.setColor(QPalette.ButtonText, QColor(p["text"]))
    pal.setColor(QPalette.ToolTipBase, QColor(p["elev"]))
    pal.setColor(QPalette.ToolTipText, QColor(p["text"]))
    pal.setColor(QPalette.Highlight, QColor(p["sel_bg"]))
    pal.setColor(QPalette.HighlightedText, QColor(p["sel_fg"]))
    app.setPalette(pal)
    _apply_fonts(app)


def stylesheet(theme: str) -> str:
    p = THEMES[theme] if theme in THEMES else THEMES["eve_modern"]
    r = 10
    pad = 6
    return f"""
* {{ outline: 0; }}
QMainWindow, QWidget {{ background: {p['bg']}; color: {p['text']}; }}
QToolTip {{ background: {p['elev']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: {r}px; padding: {pad}px {pad+2}px; }}

/* Toolbar: keep a consistent, larger height */
QToolBar#main_toolbar {{ background: {p['elev']}; border: 1px solid {p['border']}; padding: 4px 6px; min-height: 40px; }}
QToolBar#main_toolbar QToolButton {{ padding: 8px 12px; margin: 0px 2px; }}
QToolButton {{ background: transparent; color: {p['text']}; border-radius: {r}px; }}
QToolButton:hover {{ background: {p['hover']}; }}
QToolButton:pressed {{ background: {p['sel_bg']}; color: {p['sel_fg']}; }}
/* Hide the little dropdown arrow on toolbuttons with menus */
QToolButton::menu-indicator {{ image: none; width: 0px; }}
QToolButton::menu-indicator:pressed, QToolButton::menu-indicator:open {{ image: none; width: 0px; }}
QToolButton::menu-button {{ width: 0px; }}

/* Menus */
QMenu {{ background: {p['elev']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: {r}px; padding: 6px; }}
QMenu::item {{ padding: 6px 10px; border-radius: {r-2}px; }}
QMenu::item:selected {{ background: {p['sel_bg']}; color: {p['sel_fg']}; }}

/* Tabs */
QTabWidget::pane {{ border: 1px solid {p['border']}; top: -1px; background: {p['bg']}; }}
QTabBar::tab {{ background: {p['elev']}; color: {p['muted']}; padding: 6px 12px; margin-right: 2px; border: 1px solid {p['border']}; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }}
QTabBar::tab:selected {{ color: {p['accent']}; background: {p['bg_alt']}; border-color: {p['border']}; border-bottom: 2px solid {p['accent']}; }}
QTabBar::tab:hover {{ color: {p['text']}; background: {p['hover']}; }}

/* Splitter */
QSplitter::handle {{ background: {p['border']}; }}
QSplitter::handle:hover {{ background: {p['focus']}; }}

/* Explorer and lists */
QTreeView {{ background: {p['bg_alt']}; border: none; border-right: 1px solid {p['border']}; padding: 4px; show-decoration-selected: 1; }}
QListView {{ background: {p['bg_alt']}; border: none; padding: 4px; }}
QTreeView::item, QListView::item {{ height: 28px; padding-left: 6px; }}
QTreeView::item:hover, QListView::item:hover {{ background: {p['hover']}; }}
QTreeView::item:selected, QListView::item:selected {{ background: {p['hover']}; color: {p['sel_fg']}; border-left: 2px solid {p['accent']}; }}

/* Form controls */
QPushButton, QComboBox, QLineEdit {{ background: {p['elev']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: {r}px; padding: 6px 10px; }}
QPushButton:hover, QComboBox:hover, QLineEdit:hover {{ border-color: {p['focus']}; color: {p['text']}; }}
QPushButton:pressed {{ background: {p['sel_bg']}; color: {p['sel_fg']}; }}

/* Status Bar */
QStatusBar {{ background: {p['elev']}; border-top: 1px solid {p['border']}; color: {p['muted']}; }}
QStatusBar QLabel {{ padding: 2px 6px; border-radius: {r-4}px; }}

/* Editors */
QPlainTextEdit, QTextEdit {{ background: {p['sunken']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 4px; padding: 6px; selection-background-color: {p['sel_bg']}; selection-color: {p['sel_fg']}; }}

/* Scrollbars */
QScrollBar:vertical {{ border: none; background: {p['sunken']}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {p['border']}; min-height: 20px; border-radius: 5px; }}
QScrollBar::handle:vertical:hover {{ background: {p['accent']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ background: none; height: 0px; }}

QScrollBar:horizontal {{ border: none; background: {p['sunken']}; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {p['border']}; min-width: 20px; border-radius: 5px; }}
QScrollBar::handle:horizontal:hover {{ background: {p['accent']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ background: none; width: 0px; }}
"""


def apply_theme(app: QApplication, theme_name: str) -> None:
    t = theme_name if theme_name in THEMES else "eve_modern"
    apply_palette(app, t)


def apply_stylesheet(app: QApplication, theme_name: str) -> None:
    t = theme_name if theme_name in THEMES else "eve_modern"
    app.setStyleSheet(stylesheet(t))


__all__ = [
    "THEMES",
    "apply_palette",
    "stylesheet",
    "apply_theme",
    "apply_stylesheet",
]