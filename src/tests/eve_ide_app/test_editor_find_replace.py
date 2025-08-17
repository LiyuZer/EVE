import os
import time
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.eve_ide_app.editor import CodeEditor  # noqa: E402


def _process(app: QApplication, ms: int = 50):
    app.processEvents()
    QTest.qWait(ms)


def _make_editor_with_text(app: QApplication, text: str) -> CodeEditor:
    ed = CodeEditor(path=None)
    ed.setPlainText(text)
    _process(app)
    return ed


def test_find_next_prev_basic():
    app = QApplication.instance() or QApplication([])
    ed = _make_editor_with_text(app, "foo bar\nfoo baz\nqux foo")

    # Show find bar and set query
    assert hasattr(ed, "show_find_bar")
    ed.show_find_bar()
    ed.set_find_text("foo")

    # First next selects first 'foo'
    ed.find_next()
    _process(app)
    assert ed.textCursor().selectedText() == "foo"
    first_pos = ed.textCursor().selectionStart()

    # Next selects second 'foo'
    ed.find_next()
    _process(app)
    assert ed.textCursor().selectedText() == "foo"
    second_pos = ed.textCursor().selectionStart()
    assert second_pos > first_pos

    # Prev goes back to first
    ed.find_prev()
    _process(app)
    assert ed.textCursor().selectionStart() == first_pos


def test_replace_one_all_case_sensitive():
    app = QApplication.instance() or QApplication([])
    ed = _make_editor_with_text(app, "cat cat cAt\ncat")

    ed.show_find_bar()
    ed.set_find_text("cat")
    ed.set_find_options(case_sensitive=True, whole_word=False, regex=False)

    # Select first
    ed.find_next(); _process(app)
    assert ed.textCursor().selectedText() == "cat"

    # Set replace text and replace one
    ed.set_replace_text("dog")
    ed.replace_one(); _process(app)

    # Only the first exact-case 'cat' should change
    txt = ed.toPlainText()
    assert txt.count("dog") == 1
    assert txt.count("cat") == 2  # two remaining exact 'cat'
    assert "cAt" in txt  # case-sensitive untouched

    # Replace all remaining exact-case matches
    replaced = ed.replace_all(); _process(app)
    assert isinstance(replaced, int)
    txt = ed.toPlainText()
    assert txt.count("dog") == 3  # 1 + 2 replaced
    assert "cat" not in txt
    assert "cAt" in txt


def test_regex_search_replace_all():
    app = QApplication.instance() or QApplication([])
    ed = _make_editor_with_text(app, "a1 a2 a3 a10 b1")

    ed.show_find_bar()
    ed.set_find_text(r"a\d+")
    ed.set_find_options(case_sensitive=True, whole_word=False, regex=True)

    # Replace all regex matches
    ed.set_replace_text("A")
    count = ed.replace_all(); _process(app)

    # a1, a2, a3, a10 => 4 matches
    assert count >= 4
    txt = ed.toPlainText()
    assert txt.count("A") == 4
    assert "b1" in txt
