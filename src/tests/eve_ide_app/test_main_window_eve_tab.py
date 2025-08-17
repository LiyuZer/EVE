import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
from src.eve_ide_app.main_window import MainWindow

def test_main_window_has_eve_tab():
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    # Ensure the bottom tabs exist and contain an Eve tab
    assert hasattr(win, 'bottom_tabs')
    tabs = win.bottom_tabs
    labels = [tabs.tabText(i) for i in range(tabs.count())]
    assert 'Eve' in labels
    win.close()
