#!/usr/bin/env bash
set -euo pipefail

# EVE setup script: creates a virtual env and installs all requirements
# Usage: ./setup.sh [--recreate]

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${REPO_ROOT}/venv"
PY_BIN="python3"
PIP_BIN="pip"
RECREATE=false

for arg in "$@"; do
  case "$arg" in
    --recreate)
      RECREATE=true
      shift
      ;;
    *)
      ;;
  esac
done

command -v ${PY_BIN} >/dev/null 2>&1 || { echo "python3 not found. Please install Python 3."; exit 1; }

# Create or recreate venv
if [ "$RECREATE" = true ] && [ -d "$VENV_DIR" ]; then
  echo "Recreating virtual environment at $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment at $VENV_DIR"
  ${PY_BIN} -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# Ensure pip is up-to-date
python -m pip install --upgrade pip wheel setuptools

# Install dependencies from requirements.txt
if [ -f "$REPO_ROOT/requirements.txt" ]; then
  echo "Installing requirements from requirements.txt"
  pip install -r "$REPO_ROOT/requirements.txt"
else
  echo "requirements.txt not found; installing core deps directly"
  pip install openai colorama python-dotenv pydantic argparse chromadb
fi

# Safety: ensure chromadb present if memory module in use
if [ -f "$REPO_ROOT/src/memory.py" ]; then
  python - << 'PY'
try:
    import chromadb  # noqa: F401
    print("chromadb is installed ✔")
except Exception:
    import sys, subprocess
    print("chromadb missing; installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "chromadb"]) 
PY
fi

cat << 'MSG'

------------------------------------------------------------
EVE setup complete! Next steps:
1) Create a .env file in the repo root with at least:
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   OPENAI_MODEL=gpt-4o-mini (or your preferred compatible model)
   # Optional:
   # LOG_LEVEL=DEBUG|INFO|WARNING (default INFO)
   # LOG_FILE=project.log (default project.log)

2) Run Eve:
   source venv/bin/activate
   python main.py

Happy coding with your luminous dragon! 🐉
------------------------------------------------------------
MSG
