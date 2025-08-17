import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
from src.eve_ide_app.eve_interface import EveInterfaceWidget

def test_eve_interface_widget_basic():
    app = QApplication.instance() or QApplication([])
    w = EveInterfaceWidget()
    w.append('Eve: Hello')
    assert 'Eve: Hello' in w.output.toPlainText()
    w.deleteLater()
