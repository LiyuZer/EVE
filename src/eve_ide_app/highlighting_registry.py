from __future__ import annotations
from pathlib import Path
from typing import Dict, Set

__all__ = [
    "get_language_for_path",
    "list_supported_languages",
]

# Fixed extension map - removed duplicate keys
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
    "h": "cpp",  # Default .h to C++ for better highlighting
    
    # C++
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

_BASENAME_MAP: Dict[str, str] = {
    "makefile": "make",
    "dockerfile": "docker",
}

def _normalize_extension(p: str | Path) -> str | None:
    """Extract and normalize file extension."""
    base = Path(p).name
    suf = Path(base).suffix
    if not suf:
        return None
    return suf[1:].lower() if len(suf) > 1 else None

def get_language_for_path(path: str | Path) -> str:
    """Return a language tag for the given path, or 'plain' as a fallback."""
    p = Path(path)
    base = p.name.lower()
    
    # Check basename first (files without extensions)
    if base in _BASENAME_MAP:
        return _BASENAME_MAP[base]
    
    # Check extension
    ext = _normalize_extension(p)
    if ext and ext in _EXTENSION_MAP:
        return _EXTENSION_MAP[ext]
    
    return "plain"

def list_supported_languages() -> Set[str]:
    """Return the set of declared languages in the registry."""
    langs = set(_EXTENSION_MAP.values()) | set(_BASENAME_MAP.values())
    langs.add("plain")
    return langs