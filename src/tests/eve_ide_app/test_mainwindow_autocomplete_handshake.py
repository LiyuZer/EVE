import os
import time
import json
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.eve_ide_app.main_window import MainWindow  # noqa: E402


def _wait_until(cond, app: QApplication, timeout_ms: int = 6000, step_ms: int = 50) -> bool:
    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        try:
            if cond():
                return True
        except Exception:
            pass
        app.processEvents()
        QTest.qWait(step_ms)
    return False


def test_mainwindow_autocomplete_handshake_success(tmp_path):
    # Ensure clean handshake file
    repo = Path(__file__).resolve().parents[3]  # project root
    info_path = repo / "server_info.json"
    try:
        info_path.unlink()
    except FileNotFoundError:
        pass

    # Use stubbed autocomplete agent to avoid external API calls
    os.environ["EVE_AUTOCOMPLETE_TEST"] = "1"

    # Ensure CWD is repo root so autocomplete.py resolves correctly
    prev_cwd = Path.cwd()
    try:
        os.chdir(repo)
        app = QApplication.instance() or QApplication([])
        win = MainWindow()

        ok = _wait_until(lambda: getattr(win, "auto_completion_port", 0) > 0, app, timeout_ms=6000)
        assert ok, "MainWindow did not detect autocomplete port in time"
        assert win.auto_completion_port > 0

        # Optional: verify server_info.json reflects the same port
        data = json.loads(info_path.read_text(encoding="utf-8"))
        assert int(data.get("port", 0)) == win.auto_completion_port
    finally:
        try:
            win.close()
        except Exception:
            pass
        os.chdir(prev_cwd)
        # Cleanup env var for isolation
        os.environ.pop("EVE_AUTOCOMPLETE_TEST", None)


def test_mainwindow_autocomplete_timeout(monkeypatch):
    # Ensure clean handshake file (so timeout path is taken)
    repo = Path(__file__).resolve().parents[3]  # project root
    info_path = repo / "server_info.json"
    try:
        info_path.unlink()
    except FileNotFoundError:
        pass

    import subprocess as _sub

    real_popen = _sub.Popen

    def fake_popen(cmd, *args, **kwargs):
        # Spawn a dummy sleeper process that never writes server_info.json
        sleeper = ["python3", "-c", "import time; time.sleep(10)"]
        return real_popen(
            sleeper,
            stdout=kwargs.get("stdout"),
            stderr=kwargs.get("stderr"),
            text=kwargs.get("text", True),
            bufsize=kwargs.get("bufsize", 1),
        )

    monkeypatch.setattr("subprocess.Popen", fake_popen)

    # Ensure CWD is repo root
    prev_cwd = Path.cwd()
    try:
        os.chdir(repo)
        app = QApplication.instance() or QApplication([])
        win = MainWindow()

        # Wait slightly beyond the 5s internal deadline to ensure timeout path
        _ = _wait_until(lambda: False, app, timeout_ms=5600)
        assert getattr(win, "auto_completion_port", 0) == 0, "Port should remain unset on timeout"
    finally:
        try:
            win.close()
        except Exception:
            pass
        os.chdir(prev_cwd)