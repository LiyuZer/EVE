import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
from src.eve_ide_app.main_window import MainWindow

def test_main_window_launch():
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    assert 'Eve IDE' in win.windowTitle()
    assert hasattr(win, 'file_explorer')
    assert hasattr(win, 'tab_manager')
    assert hasattr(win, 'terminal')
    win.close()
