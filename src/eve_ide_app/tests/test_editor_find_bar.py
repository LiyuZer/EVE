from PySide6.QtWidgets import QApplication
from src.eve_ide_app.editor import CodeEditor


def _app():
    app = QApplication.instance() or QApplication([])
    return app


def _new_editor(text: str = ""):
    app = _app()
    ed = CodeEditor()
    if text:
        ed.setPlainText(text)
    app.processEvents()
    return ed, app


def test_find_bar_visibility():
    ed, app = _new_editor("Hello world")
    ed.show_find_bar()
    app.processEvents()
    assert getattr(ed, "_find_bar", None) is not None
    assert ed._find_bar.isVisible()

    ed.hide_find_bar()
    app.processEvents()
    assert not ed._find_bar.isVisible()


def test_find_next_prev_selection():
    text = "foo bar foo baz foo"
    ed, app = _new_editor(text)

    ed.set_find_text("foo")
    app.processEvents()

    assert ed.find_next() is True
    app.processEvents()
    assert ed.textCursor().selectedText() == "foo"

    assert ed.find_next() is True
    app.processEvents()
    assert ed.textCursor().selectedText() == "foo"

    assert ed.find_next() is True  # wrap to first again eventually
    app.processEvents()
    assert ed.textCursor().selectedText() == "foo"

    # Go previous
    assert ed.find_prev() is True
    app.processEvents()
    assert ed.textCursor().selectedText() == "foo"


def test_replace_one_and_all():
    text = "alpha foo beta foo gamma foo"
    ed, app = _new_editor(text)

    ed.set_find_text("foo")
    ed.set_replace_text("bar")
    app.processEvents()

    # Replace one occurrence
    ok_one = ed.replace_one()
    app.processEvents()
    assert ok_one is True
    t1 = ed.toPlainText()
    assert t1.count("bar") == 1
    assert t1.count("foo") == 2

    # Replace remaining occurrences
    cnt = ed.replace_all()
    app.processEvents()
    assert cnt == 2
    t2 = ed.toPlainText()
    assert t2.count("bar") == 3
    assert "foo" not in t2


def test_highlight_matches():
    text = "foo X foo Y foo Z"
    ed, app = _new_editor(text)

    ed.set_find_text("foo")
    app.processEvents()

    sels = ed.extraSelections()
    # Should highlight all occurrences; allow >= for resilience if extra selections are added later
    assert len(sels) >= 3


def test_case_sensitivity_programmatic():
    text = "Foo foo FOO"
    ed, app = _new_editor(text)

    ed.set_find_text("foo")
    ed.set_find_options(case_sensitive=False)
    app.processEvents()
    sels_insensitive = len(ed.extraSelections())
    assert sels_insensitive >= 3  # Foo, foo, FOO all match when case-insensitive

    ed.set_find_options(case_sensitive=True)
    app.processEvents()
    sels_sensitive = len(ed.extraSelections())
    # Only the exact lowercase 'foo' should match
    assert sels_sensitive == 1
