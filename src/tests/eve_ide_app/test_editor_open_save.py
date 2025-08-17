import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
from PySide6.QtWidgets import QApplication

from src.eve_ide_app.editor import TabManager

def test_editor_open_modify_save(tmp_path):
    app = QApplication.instance() or QApplication([])
    p = tmp_path / 'sample.py'
    p.write_text('print(1)\n', encoding='utf-8')

    tabs = TabManager()
    ed = tabs.open_file(p)
    assert ed.path and ed.path.exists()

    # Simulate a real user edit to ensure modified state toggles in PySide6
    ed.selectAll()
    ed.insertPlainText('print(42)\n')
    assert ed.document().isModified()

    ok = tabs.save_current()
    assert ok
    assert p.read_text(encoding='utf-8') == 'print(42)\n'
