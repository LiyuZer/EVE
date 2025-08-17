import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
from PySide6.QtWidgets import QApplication


def test_svg_assets_exist_and_loadable():
    app = QApplication.instance() or QApplication([])
    base = Path('src/eve_ide_app/assets/icons/fluent')
    assert (base / 'dark').exists() and (base / 'light').exists(), 'fluent icon theme directories should exist'

    names = ['open-folder', 'open-file', 'save', 'run', 'stop', 'theme', 'folder', 'folder-open', 'file']
    for mode in ['dark', 'light']:
        for n in names:
            p = base / mode / f'{n}.svg'
            assert p.exists(), f'missing SVG asset: {p}'

    # Provider should return non-null icons for these names
    from src.eve_ide_app.icon_provider import EveIconProvider
    for mode in ['dark', 'light']:
        prov = EveIconProvider(mode)
        for n in names:
            ico = prov.get_icon(n)
            assert hasattr(ico, 'isNull') and not ico.isNull(), f'icon {n} in mode {mode} should be non-null'

