# src/eve_ide_app/themes_modern.py
from PySide6.QtWidgets import QApplication

def apply_stylesheet_modern(app: QApplication):
    """
    Modern cyberpunk/dragon theme:
    - Explorer clearly separated with lighter dark background & border
    - Editor framed with subtle rounded border
    - Tabs & terminal get neon cyan accents
    """

    qss = """
    /* ===== Base App ===== */
    QWidget {
        background-color: #121212;       /* deep dark base */
        color: #e0e0e0;                  /* off-white text */
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 13px;
        border: none;
    }

    /* ===== Explorer Panel ===== */
    QTreeView, QListView {
        background-color: #181818;       /* contrast: lighter than editor */
        border-right: 1px solid #2a2a2a; /* sharp divider */
        padding: 4px;
        show-decoration-selected: 1;
    }

    QTreeView::item, QListView::item {
        height: 22px;
        padding-left: 6px;
    }

    QTreeView::item:selected, QListView::item:selected {
        background-color: #212121;
        border-left: 2px solid #00e0ff;  /* neon cyan bar highlight */
        color: #ffffff;
    }

    /* ===== Editor ===== */
    QTextEdit, QPlainTextEdit {
        background-color: #1a1a1a;
        border: 1px solid #2a2a2a;       /* subtle frame */
        border-radius: 4px;
        padding: 6px;
        selection-background-color: #5a189a; /* neon purple highlight */
        selection-color: #ffffff;
    }

    /* ===== Tabs ===== */
    QTabWidget::pane {
        border: 1px solid #2a2a2a;
        top: -1px;
        background: #121212;
    }

    QTabBar::tab {
        background: #1e1e1e;
        color: #b0b0b0;
        padding: 6px 12px;
        border: 1px solid #2a2a2a;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }

    QTabBar::tab:selected {
        background: #262626;
        color: #00e0ff;                  /* neon cyan text */
        border-bottom: 2px solid #00e0ff;
    }

    QTabBar::tab:hover {
        background: #2a2a2a;
        color: #ffffff;
    }

    /* ===== Buttons ===== */
    QPushButton {
        background-color: #1e1e1e;
        border: 1px solid #2a2a2a;
        border-radius: 4px;
        padding: 4px 8px;
        color: #e0e0e0;
    }

    QPushButton:hover {
        border: 1px solid #00e0ff;
        color: #00e0ff;
    }

    QPushButton:pressed {
        background-color: #262626;
    }

    /* ===== Scrollbars ===== */
    QScrollBar:vertical {
        border: none;
        background: #1a1a1a;
        width: 10px;
    }

    QScrollBar::handle:vertical {
        background: #333;
        min-height: 20px;
        border-radius: 5px;
    }

    QScrollBar::handle:vertical:hover {
        background: #00e0ff;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        background: none;
    }

    /* ===== Status Bar ===== */
    QStatusBar {
        background: #181818;
        border-top: 1px solid #2a2a2a;
        color: #888;
    }
    """

    app.setStyleSheet(qss)
