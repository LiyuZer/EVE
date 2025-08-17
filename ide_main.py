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

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    win.show()
    app.exec()