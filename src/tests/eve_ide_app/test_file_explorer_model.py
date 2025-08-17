import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDir

from src.eve_ide_app.file_explorer import FileExplorer

def test_file_explorer_open_signal(tmp_path):
    app = QApplication.instance() or QApplication([])
    sub = tmp_path / 'pkg'
    sub.mkdir()
    f = sub / 'x.py'
    f.write_text('print("hi")\n', encoding='utf-8')

    fe = FileExplorer()
    fe.set_root_path(tmp_path)

    captured = {}
    def on_open(path):
        captured['path'] = path
    fe.fileOpenRequested.connect(on_open)

    idx = fe.model.index(str(f))
    assert idx.isValid()

    # Simulate user double-click
    fe._on_double_clicked(idx)

    assert captured.get('path') == str(f)
