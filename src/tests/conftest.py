import os
import sys
from pathlib import Path

# Ensure Qt can run in headless environments during tests
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# This file lives at <project_root>/src/tests/conftest.py
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]  # .../eve
SRC_DIR = PROJECT_ROOT / "src"

# Ensure project root is first so 'import src.*' resolves correctly
proj = str(PROJECT_ROOT)
if proj not in sys.path:
    sys.path.insert(0, proj)

# Add src directory for direct 'import eve_ide_app.*' (lower priority than project root)
src_path = str(SRC_DIR)
if src_path not in sys.path:
    sys.path.append(src_path)

# Robust: explicitly alias a package module for 'src' so imports work regardless of CWD
if "src" not in sys.modules:
    import types
    pkg = types.ModuleType("src")
    pkg.__path__ = [str(SRC_DIR)]
    sys.modules["src"] = pkg
