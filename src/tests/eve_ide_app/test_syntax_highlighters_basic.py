from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QTextDocument

from eve_ide_app.highlighters import create_highlighter


def _ensure_app():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def _highlighted_char_count(doc: QTextDocument) -> int:
    total = 0
    block = doc.begin()
    while block.isValid():
        layout = block.layout()
        if layout is not None:
            # Qt6: QTextLayout.formats(); fallback to additionalFormats() if needed
            try:
                formats = layout.formats()
            except Exception:
                try:
                    formats = layout.additionalFormats()  # type: ignore[attr-defined]
                except Exception:
                    formats = []
            for fr in formats:
                try:
                    total += int(getattr(fr, "length", 0))
                except Exception:
                    pass
        block = block.next()
    return total


def _run_and_count(text: str, language: str) -> int:
    app = _ensure_app()
    doc = QTextDocument()
    doc.setPlainText(text)
    hl = create_highlighter(doc, "eve", language)
    # Force a highlight pass and flush events
    try:
        hl.rehighlight()
    except Exception:
        pass
    try:
        app.processEvents()
    except Exception:
        pass
    return _highlighted_char_count(doc)


def test_python_highlighting_basic():
    text = (
        "@dec\n"
        "def Foo(x: int) -> int:\n"
        "    # TODO: demo\n"
        "    return x + 1\n"
    )
    count = _run_and_count(text, "python")
    assert count > 0


def test_json_highlighting_basic():
    text = '{ "name": "Eve", "n": 42, "ok": true }'
    count = _run_and_count(text, "json")
    assert count > 0


def test_markdown_highlighting_basic():
    text = "# Title\n**bold** and _italic_ and `code`\n"
    count = _run_and_count(text, "markdown")
    assert count > 0
