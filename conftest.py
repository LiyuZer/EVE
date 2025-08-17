import os
import sys
from pathlib import Path

# Run Qt in headless environments
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# This conftest works whether it lives at <project_root>/conftest.py or <project_root>/src/conftest.py
BASE_DIR = Path(__file__).resolve().parent
# Determine project root as the nearest ancestor containing a 'src' directory
if (BASE_DIR / "src").exists():
    PROJECT_ROOT = BASE_DIR
else:
    PROJECT_ROOT = BASE_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

# Ensure project root is first so `import src.*` resolves correctly
proj = str(PROJECT_ROOT)
if proj not in sys.path:
    sys.path.insert(0, proj)

# Add src directory for direct `import eve_ide_app.*` (lower priority than project root)
src_path = str(SRC_DIR)
if src_path not in sys.path:
    sys.path.append(src_path)

# Robust: create/alias a package module for 'src' so imports work regardless of CWD
if "src" not in sys.modules:
    import types
    pkg = types.ModuleType("src")
    pkg.__path__ = [str(SRC_DIR)]
    sys.modules["src"] = pkg