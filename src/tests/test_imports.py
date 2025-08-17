# Sanity import tests to catch IndentationError/SyntaxError early
# Runs headless with Qt; skips if PySide6 is unavailable.

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from importlib import import_module

pytest.importorskip("PySide6")


def test_import_editor_module_and_symbols():
    m = import_module("src.eve_ide_app.editor")
    # Import success implies no IndentationError/SyntaxError
    assert hasattr(m, "CodeEditor"), "CodeEditor class missing from editor module"
    assert hasattr(m, "TabManager"), "TabManager class missing from editor module"


def test_import_main_window_module():
    # We only need the import to succeed to detect syntax issues.
    m = import_module("src.eve_ide_app.main_window")
    assert m is not None
