import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
from PySide6.QtWidgets import QApplication

from src.eve_ide_app.splash import get_logo_path, maybe_show_splash


def test_get_logo_path_exists():
    p = get_logo_path()
    assert p is not None, 'get_logo_path should resolve a logo file'
    assert Path(p).exists(), f'logo path should exist: {p}'


def test_splash_offscreen_no_show():
    app = QApplication.instance() or QApplication([])
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    splash = maybe_show_splash(app)
    assert splash is None, 'splash should be suppressed in offscreen mode'


def test_env_disable_no_show(monkeypatch):
    app = QApplication.instance() or QApplication([])
    # Ensure offscreen does not force behavior; rely on explicit disable flag
    monkeypatch.delenv('QT_QPA_PLATFORM', raising=False)
    monkeypatch.setenv('EVE_SPLASH', '0')
    splash = maybe_show_splash(app)
    assert splash is None, 'splash should be disabled when EVE_SPLASH=0'
