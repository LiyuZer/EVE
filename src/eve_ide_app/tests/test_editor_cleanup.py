import os
import time
import threading
import tempfile
from pathlib import Path

# Ensure Qt can run headless
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from src.eve_ide_app.editor import CodeEditor


def _app():
    return QApplication.instance() or QApplication([])


def test_dispose_stops_poll_timer(tmp_path):
    app = _app()

    # Create a real file so watcher/poller are engaged
    p = tmp_path / "sample.txt"
    p.write_text("hello\n")

    ed = CodeEditor(Path(p))
    # Let Qt spin up timers
    app.processEvents()
    time.sleep(0.05)
    app.processEvents()

    # Sanity: poll timer should exist and likely be active
    assert getattr(ed, "_poll_timer", None) is not None

    ed.dispose()
    app.processEvents()

    # After dispose, timer should be torn down and editor marked dead
    assert getattr(ed, "_poll_timer", None) is None
    assert getattr(ed, "_alive", True) is False


def test_signal_emit_after_dispose_is_safe():
    app = _app()

    ed = CodeEditor(None)
    app.processEvents()

    # Immediately dispose so the editor becomes inert
    ed.dispose()

    # Emit the completionReady signal from a background thread after a short delay.
    # The slot checks _is_valid() and should no-op without crashes.
    def worker_emit():
        time.sleep(0.05)
        try:
            ed.completionReady.emit(999, "ghost test")
        except Exception:
            # Emission itself should not raise, but guard the test
            pass

    t = threading.Thread(target=worker_emit)
    t.start()

    # Process events while thread emits the signal
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)

    t.join(timeout=2)
    assert not t.is_alive()

    # If we reached here, no crash occurred and the slot no-op'd safely.


def test_cancel_tasks_on_dispose():
    app = _app()

    ed = CodeEditor(None)
    app.processEvents()

    class DummyTask:
        def __init__(self):
            self.canceled = False
        def cancel(self):
            self.canceled = True

    t1, t2 = DummyTask(), DummyTask()
    ed._ac_task = t1
    ed._ac_file_context_task = t2

    ed.dispose()
    app.processEvents()

    assert t1.canceled is True
    assert t2.canceled is True
    assert ed._ac_task is None
    assert ed._ac_file_context_task is None


def test_close_event_triggers_dispose():
    app = _app()

    ed = CodeEditor(None)
    app.processEvents()

    # close() should invoke our closeEvent -> dispose
    ed.close()
    app.processEvents()

    assert getattr(ed, "_disposed", False) is True
    assert getattr(ed, "_alive", True) is False
