import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from PySide6.QtWidgets import QApplication

from src.eve_ide_app.eve_interface import EveInterfaceWidget
from src.eve_ide_app.file_explorer import FileExplorer


def _app():
    return QApplication.instance() or QApplication([])


def test_enter_to_send_appends_user_message():
    app = _app()
    w = EveInterfaceWidget()
    try:
        w.input.setText("hello")
        # Simulate pressing Enter
        try:
            w.input.returnPressed.emit()
        except Exception:
            # Fallback, call handler directly if signal emit fails
            w._on_send()
        try:
            app.processEvents()
        except Exception:
            pass
        text = w.output.toPlainText()
        assert "Liyu: hello" in text
    finally:
        w.deleteLater()


def test_file_explorer_programmatic_ops(tmp_path):
    app = _app()
    fe = FileExplorer()
    try:
        fe.set_root_path(str(tmp_path))
        f_a = tmp_path / "a.txt"
        d_dir = tmp_path / "d"

        # Create file and folder
        assert fe.create_file(f_a)
        assert f_a.exists() and f_a.is_file()
        assert fe.create_folder(d_dir)
        assert d_dir.exists() and d_dir.is_dir()

        # Rename file
        assert fe.rename_path(f_a, "b.txt")
        f_b = tmp_path / "b.txt"
        assert f_b.exists() and not f_a.exists()

        # Delete folder and file
        assert fe.delete_path(d_dir)
        assert not d_dir.exists()
        assert fe.delete_path(f_b)
        assert not f_b.exists()
    finally:
        fe.deleteLater()
