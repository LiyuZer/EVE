from eve_ide_app.highlighting_registry import get_language_for_path, list_supported_languages


def test_registry_basic_mappings():
    cases = {
        "main.py": "python",
        "app.pyw": "python",
        "typing.pyi": "python",
        "index.js": "javascript",
        "module.mjs": "javascript",
        "legacy.cjs": "javascript",
        "app.ts": "typescript",
        "component.tsx": "typescript",
        "config.json": "json",
        "comments.jsonc": "json",
        "index.html": "html",
        "index.htm": "html",
        "page.xhtml": "html",
        "layout.xml": "xml",
        "style.css": "css",
        "style.scss": "css",
        "theme.less": "css",
        "README.md": "markdown",
        "docs.markdown": "markdown",
        "notes.mdx": "markdown",
        "data.yaml": "yaml",
        "data.yml": "yaml",
        "script.sh": "shell",
        "bootstrap.bash": "shell",
        "zprofile.zsh": "shell",
        "settings.ini": "ini",
        "defaults.cfg": "ini",
        "server.conf": "ini",
        "pyproject.toml": "toml",
    }
    for path, expected in cases.items():
        assert get_language_for_path(path) == expected, f"{path} -> expected {expected}"


def test_registry_basenames_and_fallback():
    assert get_language_for_path("Makefile") == "make"
    assert get_language_for_path("Dockerfile") == "docker"
    assert get_language_for_path("unknown.ext") == "plain"
    assert get_language_for_path("no_extension") == "plain"


def test_list_supported_languages_contains_known_set():
    langs = list_supported_languages()
    required = {
        "python", "javascript", "typescript", "json", "html", "xml", "css",
        "markdown", "yaml", "shell", "ini", "toml", "make", "docker", "plain"
    }
    missing = required - langs
    assert not missing, f"Missing languages from registry: {missing}"
