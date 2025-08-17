import time
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest

from src.eve_ide_app.main_window import MainWindow


def get_app():
    return QApplication.instance() or QApplication([])


def wait_until(predicate, timeout_ms=2000, step_ms=50):
    app = QApplication.instance()
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        if predicate():
            return True
        if app:
            app.processEvents()
        QTest.qWait(step_ms)
    return predicate()


def test_save_shortcut_is_standard_save():
    app = get_app()
    win = MainWindow()
    try:
        seq = win.save_action.shortcut()
        # Compare as string to avoid platform-specific keycode nuances
        assert seq.toString() == QKeySequence(QKeySequence.StandardKey.Save).toString()
    finally:
        win.close()


def test_save_action_saves_file(tmp_path):
    app = get_app()
    p = tmp_path / "sample.txt"
    p.write_text("line1\n", encoding="utf-8")

    win = MainWindow()
    try:
        win._open_file_path(str(p))
        editor = win.tab_manager.currentWidget()
        # Edit content in the editor (simulate user typing)
        editor.appendPlainText("line2\n")
        assert editor.document().isModified()

        # Trigger Save via the exposed action
        win.save_action.trigger()
        app.processEvents()
        QTest.qWait(100)

        text_on_disk = p.read_text(encoding="utf-8")
        assert "line2" in text_on_disk
        assert not editor.document().isModified()
    finally:
        win.close()


def test_autoreload_when_unmodified(tmp_path):
    app = get_app()
    p = tmp_path / "watch.txt"
    p.write_text("v1\n", encoding="utf-8")

    win = MainWindow()
    try:
        win._open_file_path(str(p))
        editor = win.tab_manager.currentWidget()
        # Ensure loaded and unmodified
        assert editor.toPlainText() == "v1\n"
        assert not editor.document().isModified()

        # External change
        p.write_text("v2\n", encoding="utf-8")

        # Wait for QFileSystemWatcher to fire and reload
        ok = wait_until(lambda: editor.toPlainText() == "v2\n", timeout_ms=3000)
        assert ok, "Editor did not auto-reload updated file contents"
        assert not editor.document().isModified()
    finally:
        win.close()


def test_no_autoreload_when_modified(tmp_path):
    app = get_app()
    p = tmp_path / "conflict.txt"
    p.write_text("base\n", encoding="utf-8")

    win = MainWindow()
    try:
        win._open_file_path(str(p))
        editor = win.tab_manager.currentWidget()
        assert editor.toPlainText() == "base\n"

        # Make local unsaved edits
        editor.appendPlainText("local change\n")
        assert editor.document().isModified()

        # External change on disk
        p.write_text("external\n", encoding="utf-8")

        # Give watcher time; editor should NOT overwrite local edits
        QTest.qWait(500)
        app.processEvents()

        assert "local change" in editor.toPlainText()
        assert "external\n" != editor.toPlainText()
        assert editor.document().isModified()
    finally:
        win.close()
