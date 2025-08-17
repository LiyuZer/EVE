from __future__ import annotations
import os
from pathlib import Path
import importlib
from typing import Tuple, List


def _check_api_key(messages: List[str]) -> bool:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        messages.append("OPENAI_API_KEY missing or empty")
        return False
    messages.append("OPENAI_API_KEY present")
    return True


essential_imports = [
    ("chromadb", "chromadb import failed"),
]


def _check_imports(messages: List[str]) -> bool:
    ok = True
    for modname, errprefix in essential_imports:
        try:
            importlib.import_module(modname)
            messages.append(f"{modname} import ok")
        except Exception as e:
            messages.append(f"{errprefix}: {e.__class__.__name__}: {e}")
            ok = False
    return ok


def _check_logfile(messages: List[str]) -> bool:
    log_file = os.getenv("LOG_FILE", "project.log")
    path = Path(log_file)
    try:
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure file exists, then verify append permission
        if not path.exists():
            path.touch()
        with path.open("a"):
            pass
        messages.append(f"log file writable: {path}")
        return True
    except Exception as e:
        messages.append(f"log file not writable: {path} -> {e}")
        return False


def healthcheck_env() -> Tuple[bool, List[str]]:
    """
    Run basic environment health checks.
    - Verifies OPENAI_API_KEY presence
    - Verifies key dependency imports (chromadb)
    - Verifies log file path is writable (LOG_FILE or project.log)

    Returns: (ok, messages)
    """
    messages: List[str] = []
    results = [
        _check_api_key(messages),
        _check_imports(messages),
        _check_logfile(messages),
    ]
    ok = all(results)
    return ok, messages
