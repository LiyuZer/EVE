import sys
import subprocess


def test_help_runs_and_mentions_usage_and_name():
    proc = subprocess.run(
        [sys.executable, "-m", "asciivideo", "--help"],
        capture_output=True,
        text=True,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode == 0, f"rc={proc.returncode}, out={combined}"
    low = combined.lower()
    assert "usage" in low
    assert "asciivideo" in low


def test_version_importable():
    import importlib

    m = importlib.import_module("asciivideo")
    assert hasattr(m, "__version__")
