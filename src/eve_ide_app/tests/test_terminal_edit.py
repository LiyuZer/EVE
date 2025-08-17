from PySide6.QtCore import Qt
import pytest

from src.eve_ide_app.terminal_widget import TerminalEdit


@pytest.mark.usefixtures("qtbot")
def test_submit_emits_signal(qtbot):
    edit = TerminalEdit()
    qtbot.addWidget(edit)
    edit.append_output("welcome\n")
    edit.setFocus()

    with qtbot.waitSignal(edit.commandSubmitted, timeout=2000) as blocker:
        qtbot.keyClicks(edit, "echo hi")
        qtbot.keyPress(edit, Qt.Key_Return)

    assert blocker.args[0] == "echo hi"
    # After submit, we should be at a new empty input line
    assert edit.current_input_text() == ""
    assert edit.toPlainText().endswith("\n")


@pytest.mark.usefixtures("qtbot")
def test_boundary_backspace(qtbot):
    edit = TerminalEdit()
    qtbot.addWidget(edit)
    edit.append_output("hi\n")
    edit.setFocus()

    qtbot.keyClicks(edit, "ab")
    qtbot.keyPress(edit, Qt.Key_Backspace)
    qtbot.keyPress(edit, Qt.Key_Backspace)
    # This backspace should not cross into read-only history area
    qtbot.keyPress(edit, Qt.Key_Backspace)

    assert edit.current_input_text() == ""


@pytest.mark.usefixtures("qtbot")
def test_history_navigation(qtbot):
    edit = TerminalEdit()
    qtbot.addWidget(edit)
    edit.append_output("\n")
    edit.setFocus()

    # First command
    with qtbot.waitSignal(edit.commandSubmitted, timeout=2000):
        qtbot.keyClicks(edit, "first")
        qtbot.keyPress(edit, Qt.Key_Return)

    # Second command
    with qtbot.waitSignal(edit.commandSubmitted, timeout=2000):
        qtbot.keyClicks(edit, "second")
        qtbot.keyPress(edit, Qt.Key_Return)

    # Navigate history
    qtbot.keyPress(edit, Qt.Key_Up)
    assert edit.current_input_text() == "second"
    qtbot.keyPress(edit, Qt.Key_Up)
    assert edit.current_input_text() == "first"
    qtbot.keyPress(edit, Qt.Key_Down)
    assert edit.current_input_text() == "second"
    qtbot.keyPress(edit, Qt.Key_Down)
    assert edit.current_input_text() == ""


@pytest.mark.usefixtures("qtbot")
def test_set_colors(qtbot):
    from PySide6.QtGui import QPalette, QColor

    edit = TerminalEdit()
    qtbot.addWidget(edit)
    edit.set_colors("#e6e6e6", "#101010")

    pal = edit.palette()
    # QPlainTextEdit uses Base for background and Text for foreground
    assert pal.color(QPalette.Base).name() == QColor("#101010").name()
    assert pal.color(QPalette.Text).name() == QColor("#e6e6e6").name()
