import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
from PySide6.QtCore import Qt

from src.eve_ide_app.terminal_widget import TerminalWidget


def test_tab_completion_single(qtbot, tmp_path: Path):
    # Setup files
    (tmp_path / 'alpha.txt').write_text('x', encoding='utf-8')
    (tmp_path / 'beta.txt').write_text('x', encoding='utf-8')

    term = TerminalWidget()
    qtbot.addWidget(term)
    term.set_cwd(tmp_path)

    term.output.setFocus()
    qtbot.keyClicks(term.output, 'cat al')
    qtbot.keyPress(term.output, Qt.Key_Tab)

    # Expect single match: alpha.txt (with trailing space or not depending on impl)
    qtbot.waitUntil(lambda: 'alpha.txt' in term.output.current_input_text(), timeout=1500)
    assert term.output.current_input_text().startswith('cat alpha.txt')


def test_tab_completion_multiple_list(qtbot, tmp_path: Path):
    # Multiple candidates with common prefix 'ap'
    for name in ['app.py', 'apple.py', 'apricot.txt']:
        (tmp_path / name).write_text('x', encoding='utf-8')

    term = TerminalWidget()
    qtbot.addWidget(term)
    term.set_cwd(tmp_path)

    term.output.setFocus()
    qtbot.keyClicks(term.output, 'cat ap')
    qtbot.keyPress(term.output, Qt.Key_Tab)

    # On multiple matches, suggestions should be printed to the output
    qtbot.waitUntil(
        lambda: all(n in term.output.toPlainText() for n in ['app.py', 'apple.py', 'apricot.txt']),
        timeout=2000,
    )
    # Input should remain at least the same prefix (or extended to the common prefix)
    assert term.output.current_input_text().startswith('cat ap')
