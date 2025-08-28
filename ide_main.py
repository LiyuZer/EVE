import sys
from pathlib import Path

# Ensure project root and src are on sys.path regardless of CWD
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
from src.eve_ide_app.main_window import MainWindow
# Splash is optional and CI-safe; it returns None if suppressed
try:
    from src.eve_ide_app.splash import maybe_show_splash
except Exception:
    maybe_show_splash = None  # type: ignore

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    splash = None
    try:
        if callable(maybe_show_splash):  # type: ignore
            splash = maybe_show_splash(app)
    except Exception:
        splash = None
    win = MainWindow()
    win.show()
    try:
        if splash is not None and hasattr(splash, "finish"):
            splash.finish(win)
    except Exception:
        pass
    app.exec()