import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QSignalSpy

from src.eve_ide_app.terminal_widget import TerminalWidget

def test_run_engine_health():
    app = QApplication.instance() or QApplication([])
    term = TerminalWidget()
    root = Path(__file__).resolve().parents[2]  # repo root

    spy = QSignalSpy(term.proc.finished)
    term.run_health(root)

    assert spy.wait(30000), "Process did not finish within timeout"

    out = term.output.toPlainText()
    assert "HEALTHCHECK" in out
    assert "RESULT: OK" in out
    # New UX: no exit status line should be printed
    assert "[Process exited" not in out
    term.deleteLater()