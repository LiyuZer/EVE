from __future__ import annotations
from pathlib import Path
from typing import Dict, Set

__all__ = [
    "get_language_for_path",
    "list_supported_languages",
]

# Simple, dependency-free mapping from file extensions to language tags
# This module is intentionally Qt-free so it can be unit tested easily.

# Normalized, lowercase extensions (without leading dot) -> language tag
_EXTENSION_MAP: Dict[str, str] = {
    # Python
    "py": "python",
    "pyw": "python",
    "pyi": "python",

    # JavaScript / TypeScript
    "js": "javascript",
    "mjs": "javascript",
    "cjs": "javascript",
    "ts": "typescript",
    "tsx": "typescript",

    # JSON
    "json": "json",
    "jsonc": "json",

    # Markup / Web
    "html": "html",
    "htm": "html",
    "xhtml": "html",
    "xml": "xml",
    "css": "css",
    "scss": "css",
    "less": "css",

    # Docs / Config
    "md": "markdown",
    "markdown": "markdown",
    "mdx": "markdown",
    "yaml": "yaml",
    "yml": "yaml",

    # Shell / Config
    "sh": "shell",
    "bash": "shell",
    "zsh": "shell",
    "ini": "ini",
    "cfg": "ini",
    "conf": "ini",
    "toml": "toml",

    # C family
    "c": "c",
    "h": "c",      # treat headers as C by default
    # C++ family
    "cpp": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "hpp": "cpp",
    "hh": "cpp",
    "hxx": "cpp",
    # Rust
    "rs": "rust",
    # Go
    "go": "go",
}

# Some common filename-based matches (no extension)
_BASENAME_MAP: Dict[str, str] = {
    "makefile": "make",        # not yet highlighted, reserved
    "dockerfile": "docker",     # not yet highlighted, reserved
}

def _normalize_extension(p: str | Path) -> str | None:
    name = str(p)
    base = Path(name).name
    # Exact basename matches (no extension)
    low_base = base.lower()
    if low_base in _BASENAME_MAP:
        return None  # handled by basename map
    # Regular extension
    suf = Path(base).suffix  # includes leading dot
    if not suf:
        return None
    return suf[1:].lower() if len(suf) > 1 else None


def get_language_for_path(path: str | Path) -> str:
    """Return a language tag for the given path, or 'plain' as a fallback.

    This prefers extension-based mapping and uses a few common basename fallbacks.
    The returned tag is a logical language key (e.g., 'python', 'json').
    """
    p = Path(path)
    base = p.name.lower()
    if base in _BASENAME_MAP:
        return _BASENAME_MAP[base]

    ext = _normalize_extension(p)
    if ext and ext in _EXTENSION_MAP:
        return _EXTENSION_MAP[ext]

    return "plain"


def list_supported_languages() -> Set[str]:
    """Return the set of declared languages in the registry.
    This is a superset of languages we may have highlighters for at runtime.
    """
    langs = set(_EXTENSION_MAP.values()) | set(_BASENAME_MAP.values())
    # 'plain' is always available as a fallback
    langs.add("plain")
    return langs