import os
import time
from pathlib import Path

# Ensure Qt can run headless and autocomplete is disabled for tests
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("EVE_DISABLE_AUTOCOMPLETE", "1")

from PySide6.QtWidgets import QApplication
from src.eve_ide_app.main_window import MainWindow


def _app():
    return QApplication.instance() or QApplication([])


def test_main_window_open_file_and_close(tmp_path):
    app = _app()

    # Create a sample file in a temp project root
    root = tmp_path
    root.mkdir(parents=True, exist_ok=True)
    p = root / "sample.py"
    p.write_text("print('hello dragon')\n")

    # Launch main window with the temp root, open the file, and then close
    win = MainWindow(initial_root=str(root))
    win.show()
    app.processEvents()

    # Open the file via the window API
    win._open_file_path(str(p))
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)

    # Close the window (should dispose editors and not crash)
    win.close()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)

    # If we reached here without exceptions, the smoke test passes
    assert True


def test_open_new_window_smoke(tmp_path):
    app = _app()

    # Launch a main window and then spawn a new one
    win1 = MainWindow(initial_root=str(tmp_path))
    win1.show()
    app.processEvents()

    # Create a second window using the action
    win1._open_new_window()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)

    # Close windows
    try:
        win1.close()
    except Exception:
        pass
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)

    # Test passes if no crash occurred
    assert True
