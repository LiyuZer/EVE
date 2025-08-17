import os
from pathlib import Path

from src.file_system import FileHandler
from src.schema import Diff


def test_filehandler_reads_writes_under_base_root(tmp_path):
    fh = FileHandler(base_root=tmp_path)

    rel_file = Path("sub/dir/hello.txt")
    content = "line1\nline2\n"

    # Write relative path -> should create under tmp_path
    fh.write_file(str(rel_file), content)
    abs_file = tmp_path / rel_file
    assert abs_file.exists(), f"Expected file at {abs_file}"
    assert abs_file.read_text(encoding="utf-8") == content

    # Read as string
    s = fh.read_as_str(str(rel_file))
    assert s == content

    # Read as line dict
    d = fh.read_file(str(rel_file))
    assert isinstance(d, dict)
    assert d[1] == "line1"
    assert d[2] == "line2"


def test_insert_diff_resolves_paths(tmp_path):
    fh = FileHandler(base_root=tmp_path)

    rel_file = Path("notes.txt")
    (tmp_path / rel_file).write_text("a\nb\nc\n", encoding="utf-8")

    diff = Diff(
        line_range_1=[2, 2],
        line_range_2=[0, 0],  # unused by our applier
        file_path=str(rel_file),
        Add=False,
        Remove=False,
        Replace=True,
        content="BETA",
    )

    res = fh.insert_diff(diff)
    assert "Applied diff" in res
    txt = (tmp_path / rel_file).read_text(encoding="utf-8")
    # Expect line 2 replaced with 'BETA' and keep others
    assert txt.splitlines() == ["a", "BETA", "c"]
