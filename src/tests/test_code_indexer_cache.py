import json
from pathlib import Path

from src.code_indexer import CodeIndexer


class FakeTime:
    """Simple controllable time provider for deterministic TTL tests."""
    def __init__(self, t: float = 0.0):
        self._t = float(t)

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += float(seconds)


def test_cache_hit_and_miss(tmp_path: Path):
    # Arrange a tiny repo: a.py imports b.py
    root = tmp_path
    (root / "a.py").write_text("import b\n", encoding="utf-8")
    (root / "b.py").write_text(
        """
class B:
    pass
        """.strip()
        + "\n",
        encoding="utf-8",
    )

    ft = FakeTime(100.0)
    indexer = CodeIndexer(ttl_seconds=2, time_provider=ft)

    a_path = str(root / "a.py")
    root_path = str(root)

    # First call: should parse b.py (cache miss)
    ctx1 = indexer.return_context(a_path, root_path=root_path)
    assert "b.py" in ctx1
    parsed1 = indexer._stats.get("contexts_parsed", -1)
    assert parsed1 == 1

    # Verify the context JSON is correct
    b_ctx = json.loads(ctx1["b.py"]["context"])  # it is a JSON string
    class_names = {c.get("name") for c in b_ctx.get("classes", [])}
    assert "B" in class_names

    # Second call before TTL expiry: should be cache hit (no new parse)
    ctx2 = indexer.return_context(a_path, root_path=root_path)
    parsed2 = indexer._stats.get("contexts_parsed", -1)
    assert parsed2 == 1  # unchanged => cache hit
    assert ctx2 == ctx1

    # Advance time beyond TTL and call again => cache miss -> re-parse
    ft.advance(3.0)
    ctx3 = indexer.return_context(a_path, root_path=root_path)
    parsed3 = indexer._stats.get("contexts_parsed", -1)
    assert parsed3 == 2  # incremented due to TTL expiry
    assert "b.py" in ctx3
