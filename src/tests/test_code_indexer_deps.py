import json
from pathlib import Path

from src.code_indexer import CodeIndexer


def test_absolute_import_resolution(tmp_path: Path):
    root = tmp_path
    (root / "b.py").write_text(
        """
def f():
    return 1

class C:
    pass
        """.strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "a.py").write_text("import b\n", encoding="utf-8")

    indexer = CodeIndexer(ttl_seconds=60, time_provider=lambda: 0.0)
    ctx = indexer.return_context(str(root / "a.py"), root_path=str(root))

    assert "b.py" in ctx
    data = json.loads(ctx["b.py"]["context"])
    func_names = {fn.get("name") for fn in data.get("functions", [])}
    class_names = {cl.get("name") for cl in data.get("classes", [])}
    assert "f" in func_names
    assert "C" in class_names


def test_from_import_resolution(tmp_path: Path):
    root = tmp_path
    (root / "b.py").write_text(
        """
def g():
    return 2
        """.strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "a.py").write_text("from b import g\n", encoding="utf-8")

    indexer = CodeIndexer(ttl_seconds=60, time_provider=lambda: 0.0)
    ctx = indexer.return_context(str(root / "a.py"), root_path=str(root))

    assert "b.py" in ctx
    data = json.loads(ctx["b.py"]["context"])
    func_names = {fn.get("name") for fn in data.get("functions", [])}
    assert "g" in func_names


def test_relative_import_resolution(tmp_path: Path):
    root = tmp_path
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "b.py").write_text(
        """
class B:
    pass
        """.strip()
        + "\n",
        encoding="utf-8",
    )
    (pkg / "a.py").write_text("from . import b\n", encoding="utf-8")

    indexer = CodeIndexer(ttl_seconds=60, time_provider=lambda: 0.0)
    ctx = indexer.return_context(str(pkg / "a.py"), root_path=str(root))

    assert "b.py" in ctx
    data = json.loads(ctx["b.py"]["context"])
    class_names = {cl.get("name") for cl in data.get("classes", [])}
    assert "B" in class_names


def test_ignores_outside_root_and_stdlib(tmp_path: Path):
    root = tmp_path
    (root / "a.py").write_text("import os\n", encoding="utf-8")

    indexer = CodeIndexer(ttl_seconds=60, time_provider=lambda: 0.0)
    ctx = indexer.return_context(str(root / "a.py"), root_path=str(root))

    # No in-repo dependencies should be found for stdlib-only imports
    assert ctx == {}
