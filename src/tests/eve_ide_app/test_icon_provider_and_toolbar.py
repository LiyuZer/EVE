import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
from PySide6.QtWidgets import QApplication, QToolBar, QToolButton
import pytest


@pytest.fixture()
def app():
    return QApplication.instance() or QApplication([])


def test_eve_icon_provider_returns_icons_for_known_types(app, tmp_path):
    # We expect EveIconProvider to expose a get_icon_for_path API that returns non-null QIcons
    from src.eve_ide_app.icon_provider import EveIconProvider

    p_py = tmp_path / 'x.py'
    p_md = tmp_path / 'README.md'
    p_json = tmp_path / 'conf.json'
    p_yaml = tmp_path / 'conf.yaml'
    p_txt = tmp_path / 'notes.txt'
    p_png = tmp_path / 'img.png'
    p_unknown = tmp_path / 'file.unknownext'

    for p in [p_py, p_md, p_json, p_yaml, p_txt, p_png, p_unknown]:
        p.write_text('x', encoding='utf-8')

    prov = EveIconProvider(mode='dark')

    for p in [p_py, p_md, p_json, p_yaml, p_txt, p_png, p_unknown]:
        icon = prov.get_icon_for_path(Path(p))
        assert hasattr(icon, 'isNull'), "EveIconProvider.get_icon_for_path should return a QIcon"
        assert not icon.isNull(), f"Expected non-null icon for {p.name}"


def test_main_window_toolbar_minimal_text_actions(app):
    # MainWindow should have a minimal, text-only toolbar with two dropdowns: File and Theme
    from src.eve_ide_app.main_window import MainWindow
    from PySide6.QtCore import Qt

    win = MainWindow()
    toolbars = win.findChildren(QToolBar)
    assert toolbars, "MainWindow should have at least one QToolBar"
    tb = toolbars[0]

    # Text-only style
    assert tb.toolButtonStyle() == Qt.ToolButtonTextOnly

    # Toolbar should expose two QToolButton dropdowns labeled 'File' and 'Theme'
    btn_texts = [b.text() for b in tb.findChildren(QToolButton)]
    assert 'File' in btn_texts, "Toolbar should contain a File dropdown button"
    assert 'Theme' in btn_texts, "Toolbar should contain a Theme dropdown button"

    # Ensure old standalone actions are not present on the toolbar
    labels = [a.text() for a in tb.actions() if a.text()]
    for removed in ['Open Folder', 'Open File', 'Toggle Theme']:
        assert removed not in labels

    # Also ensure no extra QToolButtons with those texts exist
    for removed in ['Open Folder', 'Open File', 'Toggle Theme']:
        assert removed not in btn_texts

    win.close()


def test_neon_theme_exists():
    # Ensure neon theme is defined so we can use it for the 2020s cyberpunk vibe
    from src.eve_ide_app.themes import THEMES, get_theme_colors
    assert 'neon' in THEMES, "Neon theme should be defined in THEMES"
    c = get_theme_colors('neon')
    assert isinstance(c, dict) and 'accent' in c and 'panel' in c, "Neon theme should provide accent/panel colors"