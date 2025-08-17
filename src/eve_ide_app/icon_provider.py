from __future__ import annotations
from typing import Dict
from pathlib import Path

from PySide6.QtWidgets import QFileIconProvider, QApplication, QStyle
from PySide6.QtGui import QIcon


class EveIconProvider(QFileIconProvider):
    """
    Minimal custom icon provider with theme mode awareness.
    - mode: 'dark' | 'light'
    - get_icon_for_path(Path) -> QIcon providing a non-null icon for known types
      with asset lookup and robust fallbacks to QStyle standard icons.

    Note: In this v1 implementation we prioritize reliability in tests by always
    returning a non-null icon via QStyle fallback if assets are missing. Later
    we will ship Fluent SVG assets and expand the mapping.
    """

    def __init__(self, mode: str = "dark"):
        super().__init__()
        self.mode = mode if mode in {"dark", "light"} else "dark"
        self._cache: Dict[str, QIcon] = {}

    def set_mode(self, mode: str):
        if mode in {"dark", "light"}:
            self.mode = mode
            # Future: clear/reload icon cache when assets are introduced
            self._cache.clear()

    # --- Public API used by tests ---
    def get_icon(self, name: str) -> QIcon:
        """Return a themed QIcon by logical name (e.g., 'open-folder', 'run', 'python').
        Tries assets/icons/fluent/{mode}/<name>.svg, falls back to QStyle. Always non-null.
        """
        if not isinstance(name, str) or not name.strip():
            return QIcon()
        name_key = name.strip().lower()
        cache_key = f"{self.mode}:{name_key}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        ico = self._load_asset_icon(name_key)
        if ico is None or ico.isNull():
            ico = self._fallback_qstyle_icon(name_key)
        if ico is None:
            ico = QIcon()
        self._cache[cache_key] = ico
        return ico

    def get_icon_for_path(self, path: Path) -> QIcon:
        """Return a themed QIcon for the given file path.
        Tries assets/icons/fluent/{mode}/<name>.svg, falls back to QStyle.
        Always returns a non-null icon.
        """
        try:
            p = Path(path)
        except Exception:
            p = Path(str(path))

        # Detect type/name/extension
        name = p.name
        ext = p.suffix.lower().lstrip(".")
        is_hidden = name.startswith('.')
        is_symlink = False
        try:
            is_symlink = p.is_symlink()
        except Exception:
            # On some virtual paths this may fail; ignore
            pass

        # Map to logical icon name
        icon_name = self._icon_name_for(ext=ext, name=name, hidden=is_hidden, symlink=is_symlink)

        # Try cache first
        cache_key = f"{self.mode}:{icon_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try asset lookup (non-fatal if missing)
        ico = self._load_asset_icon(icon_name)
        if ico is None or ico.isNull():
            # Fallback to QStyle standard pixmaps to ensure non-null
            ico = self._fallback_qstyle_icon(icon_name)

        # As a last resort, create an empty QIcon (shouldn't happen due to fallbacks)
        if ico is None:
            ico = QIcon()

        self._cache[cache_key] = ico
        return ico

    # --- Internal utilities ---
    def _icon_name_for(self, ext: str, name: str, hidden: bool, symlink: bool) -> str:
        if symlink:
            return "symlink"
        if hidden and name != ".gitignore":
            return "hidden"
        # Specific filenames
        if name == ".gitignore":
            return "git-ignore"
        # Extension mapping
        images = {"png", "jpg", "jpeg", "gif", "bmp", "svg", "webp"}
        texty = {"txt", "log", "rst"}
        configs = {"toml", "ini", "cfg", "conf"}
        if ext in images:
            return "image"
        if ext in texty:
            return "text"
        if ext in configs:
            return "config"
        if ext in {"md"}:
            return "md"
        if ext in {"json"}:
            return "json"
        if ext in {"yaml", "yml"}:
            return "yaml"
        if ext in {"py"}:
            return "python"
        # Default
        return "file"

    def _assets_root(self) -> Path:
        # src/eve_ide_app/icon_provider.py -> assets at src/eve_ide_app/assets/icons/fluent/{mode}
        return Path(__file__).resolve().parent / "assets" / "icons" / "fluent" / self.mode

    def _load_asset_icon(self, icon_name: str) -> QIcon | None:
        base = self._assets_root()
        svg = base / f"{icon_name}.svg"
        try:
            if svg.exists():
                return QIcon(str(svg))
        except Exception:
            pass
        return None

    def _fallback_qstyle_icon(self, icon_name: str) -> QIcon:
        style = QApplication.instance().style() if QApplication.instance() else None
        if not style:
            return QIcon()
        sp = QStyle.StandardPixmap
        mapping = {
            "folder": sp.SP_DirIcon,
            "folder-open": sp.SP_DirOpenIcon,
            "file": sp.SP_FileIcon,
            "python": sp.SP_FileIcon,
            "text": sp.SP_FileIcon,
            "image": sp.SP_FileIcon,
            "json": sp.SP_FileIcon,
            "yaml": sp.SP_FileIcon,
            "md": sp.SP_FileIcon,
            "config": sp.SP_FileIcon,
            "git": sp.SP_DirIcon,
            "git-ignore": sp.SP_DirIcon,
            "hidden": sp.SP_FileIcon,
            "symlink": sp.SP_FileIcon,
            # Toolbar-ish fallbacks
            "open-folder": sp.SP_DirOpenIcon,
            "open-file": sp.SP_FileIcon,
            "save": sp.SP_DialogSaveButton,
            "run": sp.SP_MediaPlay,
            "stop": sp.SP_MediaStop,
            "theme": sp.SP_DesktopIcon,
        }
        spx = mapping.get(icon_name, sp.SP_FileIcon)
        return style.standardIcon(spx)