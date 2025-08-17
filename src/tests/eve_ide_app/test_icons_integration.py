import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
import pytest

from src.eve_ide_app.file_explorer import FileExplorer

# EveIconProvider to be implemented in src/eve_ide_app/icon_provider.py
try:
    from src.eve_ide_app.icon_provider import EveIconProvider  # type: ignore
except Exception:  # ImportError before implementation
    EveIconProvider = None  # type: ignore


@pytest.fixture()
def app():
    return QApplication.instance() or QApplication([])


def test_file_explorer_uses_eve_icon_provider(app):
    fe = FileExplorer()
    # Qt may return a base QAbstractFileIconProvider from model.iconProvider();
    # we expose the actual EveIconProvider via FileExplorer.icon_provider.
    assert EveIconProvider is not None, "EveIconProvider should be implemented in icon_provider.py"
    assert hasattr(fe, 'icon_provider'), "FileExplorer should expose icon_provider"
    assert isinstance(fe.icon_provider, EveIconProvider), (
        "FileExplorer.icon_provider should be an EveIconProvider instance"
    )
    assert fe.model.iconProvider() is not None, "Model should have a non-null icon provider"


def test_theme_toggle_switches_icon_mode(app):
    from src.eve_ide_app.main_window import MainWindow

    win = MainWindow()

    assert hasattr(win.file_explorer, 'icon_provider'), "FileExplorer should expose icon_provider"
    provider = win.file_explorer.icon_provider

    assert EveIconProvider is not None, "EveIconProvider should be implemented in icon_provider.py"
    assert isinstance(provider, EveIconProvider), "FileExplorer should start with EveIconProvider"

    # Record initial mode; must be either 'dark' or 'light'
    initial_mode = getattr(provider, 'mode', None)
    assert initial_mode in {'dark', 'light'}, "EveIconProvider should expose mode in {'dark','light'}"

    # Toggle theme; implementation should refresh provider mode (same instance)
    win._toggle_theme()

    provider2 = win.file_explorer.icon_provider
    assert provider2 is provider, "Icon provider instance should be retained and its mode updated"

    next_mode = getattr(provider2, 'mode', None)
    assert next_mode in {'dark', 'light'}, "EveIconProvider should expose mode in {'dark','light'} after toggle"
    assert next_mode != initial_mode, "Theme toggle should switch icon mode between dark and light"

    win.close()