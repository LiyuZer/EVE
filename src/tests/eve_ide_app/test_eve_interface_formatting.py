import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
from src.eve_ide_app.eve_interface import EveInterfaceWidget


def _app():
    return QApplication.instance() or QApplication([])


def test_eve_interface_append_plain_text():
    app = _app()
    w = EveInterfaceWidget()
    w.append('Eve: Hello')
    assert 'Eve: Hello' in w.output.toPlainText()
    w.deleteLater()


def test_eve_interface_formatting_basic():
    app = _app()
    w = EveInterfaceWidget()

    # Ensure the formatting method exists
    assert hasattr(w, '_format_line'), "EveInterfaceWidget should provide _format_line for styling"

    # Eve line should be HTML-formatted and include label
    html = w._format_line('Eve: Hello there')
    assert 'Eve:' in html
    assert ('<span' in html) or ('<div' in html)

    # System line should be formatted distinctly
    html2 = w._format_line('System: Something happened')
    assert 'System:' in html2

    # ANSI sequences should be stripped from output HTML
    ansi_text = '\x1b[31mError:\x1b[0m Boom'
    html3 = w._format_line(ansi_text)
    assert 'Error:' in html3
    assert '\x1b' not in html3

    w.deleteLater()
