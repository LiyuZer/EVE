import os
import time
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.eve_ide_app.search_panel import SearchPanel  # noqa: E402
from src.eve_ide_app.main_window import MainWindow   # noqa: E402


def _process(app: QApplication, ms: int = 50):
    app.processEvents()
    QTest.qWait(ms)


def _wait_until(cond, app: QApplication, timeout_ms: int = 5000, step_ms: int = 50) -> bool:
    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        try:
            if cond():
                return True
        except Exception:
            pass
        _process(app, step_ms)
    return False


def test_search_panel_basic(tmp_path):
    app = QApplication.instance() or QApplication([])

    # Create a small workspace
    f1 = tmp_path / "a.py"
    f1.write_text("dragon\nDragon here\nnope", encoding="utf-8")
    f2 = tmp_path / "b.txt"
    f2.write_text("no dragon here", encoding="utf-8")

    panel = SearchPanel()
    panel.set_root(tmp_path)

    finished = {"count": None}

    def on_finished(n):
        finished["count"] = n

    panel.searchFinished.connect(on_finished)

    # Case-insensitive literal search
    panel.run_search("dragon", case=False, regex=False, whole=False)

    ok = _wait_until(lambda: finished["count"] is not None, app, timeout_ms=5000)
    assert ok, "Search did not finish in time"
    assert panel.results.count() >= 1, "Expected at least one match in results"

    # Validate payload of first result
    item = panel.results.item(0)
    # Qt.UserRole = 32 in Qt; access both to be safe
    data = item.data(32) or item.data(panel.results.userRole if hasattr(panel.results, 'userRole') else 32)
    if data is None:
        data = item.data(32)
    assert isinstance(data, tuple) and len(data) == 3
    file_path, line, col = data
    assert str(tmp_path) in file_path
    assert isinstance(line, int) and isinstance(col, int)


def test_eve_context_sync_selection(tmp_path):
    app = QApplication.instance() or QApplication([])

    # Prepare workspace and file
    work = tmp_path
    fp = work / "foo.txt"
    fp.write_text("alpha beta gamma beta", encoding="utf-8")

    # Launch MainWindow with workspace root
    win = MainWindow(initial_root=str(work))

    try:
        # Open file in editor
        win._open_file_path(str(fp))
        _process(app, 100)

        ed = win.tab_manager.currentWidget()
        assert ed is not None, "Editor did not open"

        # Use editor find to select a known term to trigger selectionChanged
        assert hasattr(ed, "set_find_text")
        ed.set_find_text("beta")
        ed.find_next()
        _process(app, 100)

        # Eve panel should have received context
        ep = win.eve_panel
        ok = _wait_until(lambda: getattr(ep, "current_file_path", None) is not None, app, timeout_ms=2000)
        assert ok, "Eve panel did not receive active context in time"
        assert ep.current_file_path.endswith("foo.txt")
        # Selection preview should be non-empty and likely 'beta'
        assert isinstance(ep.current_selection, str)
        assert len(ep.current_selection) > 0
    finally:
        try:
            win.close()
        except Exception:
            pass
