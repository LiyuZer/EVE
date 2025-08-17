from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
import json
import asyncio

import aiohttp
import requests


__all__ = [
    "read_server_info",
    "build_url",
    "async_health",
    "sync_health",
    "resolve_port",
    "async_post_json",
    "sync_post_json",
]


# ---- server_info helpers ----------------------------------------------------

def _candidate_info_paths() -> list[Path]:
    """Return likely locations for server_info.json, preferring project root.

    Layout: repo_root/server_info.json is written by autocomplete.py on startup.
    A secondary legacy path may be repo_root/src/server_info.json.
    """
    # This file lives at: repo_root/src/eve_ide_app/ac_client.py
    # So repo_root is parents[2] (.. -> eve_ide_app, .. -> src, .. -> repo_root)
    repo_root = Path(__file__).resolve().parents[2]
    primary = repo_root / "server_info.json"
    fallback = repo_root / "src" / "server_info.json"
    return [primary, fallback]


def _read_json_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def read_server_info(paths: Optional[Iterable[Path]] = None) -> Optional[Dict[str, Any]]:
    """Read the first available server_info.json from candidate paths.

    Returns the parsed dict or None if none were readable.
    """
    candidates = list(paths) if paths else _candidate_info_paths()
    for p in candidates:
        data = _read_json_file(p)
        if data and isinstance(data, dict):
            return data
    return None


# ---- URL and health ---------------------------------------------------------

def build_url(port: int, path: str) -> str:
    """Build an IPv4 localhost URL for the given port and path.

    Always uses 127.0.0.1 to avoid IPv6/SSL resolver issues.
    """
    if not path.startswith("/"):
        path = "/" + path
    return f"http://127.0.0.1:{port}{path}"


async def async_health(port: int, timeout: float = 2.0) -> bool:
    if port <= 0:
        return False
    url = build_url(port, "/health")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as resp:
                if resp.status != 200:
                    return False
                try:
                    data = await resp.json()
                except Exception:
                    return False
                return bool(data and data.get("status") == "ok")
    except Exception:
        return False


def sync_health(port: int, timeout: float = 2.0) -> bool:
    if port <= 0:
        return False
    url = build_url(port, "/health")
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code != 200:
            return False
        try:
            data = r.json()
        except Exception:
            return False
        return bool(data and data.get("status") == "ok")
    except Exception:
        return False


# ---- Port resolution ---------------------------------------------------------

def resolve_port(cached_port: int | None = None) -> int:
    """Return a healthy autocomplete server port.

    - If cached_port is healthy, return it.
    - Else, read server_info.json and validate.
    - Return 0 if none are healthy.
    """
    cached = int(cached_port or 0)
    if cached > 0 and sync_health(cached):
        return cached

    info = read_server_info()
    if not info:
        return 0
    try:
        p = int(info.get("port", 0))
    except Exception:
        p = 0
    if p > 0 and sync_health(p):
        return p
    return 0


# ---- POST helpers with single retry on re-resolve ---------------------------
async def async_post_json(
    port: int,
    path: str = "/autocomplete",
    payload: Dict[str, Any] | None = None,
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """POST JSON asynchronously to the autocomplete server.

    Behavior:
    - Attempt once with the given port.
    - On failure, re-resolve the port (without blocking the loop) and retry once if a new healthy port is found.
    - Raises the last error if both attempts fail.
    """
    payload = payload or {}
    url = build_url(port, path)

    async def _do(session: aiohttp.ClientSession, url_: str) -> Dict[str, Any]:
        async with session.post(url_, json=payload, timeout=timeout) as resp:
            # Accept 200 only; let other statuses raise
            resp.raise_for_status()
            try:
                return await resp.json()
            except Exception as e:
                raise RuntimeError(f"Invalid JSON from {url_}: {e}")

    try:
        async with aiohttp.ClientSession() as session:
            return await _do(session, url)
    except Exception as first_err:
        # Re-resolve the port without blocking the event loop
        try:
            new_port = await asyncio.to_thread(resolve_port, port)
        except Exception:
            new_port = 0
        if new_port <= 0 or new_port == port:
            raise first_err
        retry_url = build_url(new_port, path)
        try:
            async with aiohttp.ClientSession() as session:
                return await _do(session, retry_url)
        except Exception:
            raise first_err


def sync_post_json(
    port: int,
    path: str = "/autocomplete",
    payload: Dict[str, Any] | None = None,
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """POST JSON synchronously to the autocomplete server.

    Behavior:
    - Attempt once with the given port.
    - On failure, re-resolve the port and retry once if new healthy port is found.
    - Raises the last error if both attempts fail.
    """
    payload = payload or {}
    url = build_url(port, path)

    def _do(url_: str) -> Dict[str, Any]:
        r = requests.post(url_, json=payload, timeout=timeout)
        r.raise_for_status()
        try:
            return r.json()
        except Exception as e:
            raise RuntimeError(f"Invalid JSON from {url_}: {e}")

    try:
        return _do(url)
    except Exception as first_err:
        new_port = 0
        try:
            new_port = resolve_port(port)
        except Exception:
            new_port = 0
        if new_port <= 0 or new_port == port:
            raise first_err
        retry_url = build_url(new_port, path)
        try:
            return _do(retry_url)
        except Exception:
            raise first_err


def fallback_completion(prefix: Any, suffix: Any = "") -> str:
    """Local deterministic fallback completion used when server fails or returns empty.

    Mirrors the server's _DummyAgent formatting: 'test_completion:' + last 8 chars of prefix.
    Accepts prefix as str or list[str].
    """
    def _norm(x: Any) -> str:
        try:
            if isinstance(x, list):
                return "\n".join(str(part) for part in x)
            return x if isinstance(x, str) else str(x)
        except Exception:
            return str(x)

    p = _norm(prefix)
    tail = p[-8:] if p else ""
    return f"test_completion:{tail}"