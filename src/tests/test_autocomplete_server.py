import os
import json
import time
import subprocess
from pathlib import Path
import urllib.request
import urllib.error


def _wait_for_file(path: Path, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists():
            return True
        time.sleep(0.05)
    return False


def _http_json(url: str, method: str = "GET", data: dict | None = None, timeout: float = 2.5) -> dict:
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, method=method, headers=headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    with urllib.request.urlopen(req, data=body, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


def _wait_http_ok(url: str, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            data = _http_json(url)
            if isinstance(data, dict):
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


def test_autocomplete_server_health():
    # Project root (two levels up from this test file: src/tests -> repo)
    repo = Path(__file__).resolve().parents[2]
    info_path = repo / "server_info.json"

    # Ensure no stale server_info file
    try:
        info_path.unlink()
    except FileNotFoundError:
        pass

    env = os.environ.copy()
    # Use deterministic stub agent to avoid external API calls
    env["EVE_AUTOCOMPLETE_TEST"] = "1"

    proc = subprocess.Popen(
        ["python3", "autocomplete.py"],
        cwd=str(repo),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        # Wait for server_info.json
        assert _wait_for_file(info_path, 5.0), "server_info.json was not created by autocomplete server"
        info = json.loads(info_path.read_text(encoding="utf-8"))
        port = int(info.get("port", 0))
        assert port > 0, "Invalid port in server_info.json"

        base = f"http://127.0.0.1:{port}"

        # Wait until /health responds
        assert _wait_http_ok(base + "/health", 5.0), \
            "Health endpoint did not respond within timeout"
        health = _http_json(base + "/health")
        assert health.get("status") == "ok"

        # Verify /autocomplete returns 200 and a string completion
        payload = {"prefix": "hello world", "suffix": "", "context": {}}
        resp = _http_json(base + "/autocomplete", method="POST", data=payload)
        assert resp.get("status") == 200
        comp = resp.get("completion")
        assert isinstance(comp, str), "Completion should be a string"
        assert len(comp) > 0, "Completion should not be empty"
    finally:
        # Terminate the server process cleanly
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
