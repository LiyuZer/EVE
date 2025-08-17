from pathlib import Path
import asyncio

from src.eve_ide_app import ac_client as ac


def test_build_url_ipv4_localhost():
    assert ac.build_url(1234, "/autocomplete") == "http://127.0.0.1:1234/autocomplete"
    assert ac.build_url(1234, "health") == "http://127.0.0.1:1234/health"


def test_read_server_info_reads_port(tmp_path):
    p = tmp_path / "server_info.json"
    p.write_text('{"port": 55555}', encoding="utf-8")
    info = ac.read_server_info(paths=[p])
    assert info is not None
    assert int(info.get("port", 0)) == 55555


def test_resolve_port_prefers_cached_if_healthy(monkeypatch):
    monkeypatch.setattr(ac, "sync_health", lambda port, timeout=2.0: True)
    assert ac.resolve_port(32123) == 32123


def test_resolve_port_reads_file_when_cached_invalid(monkeypatch):
    def fake_sync_health(port: int, timeout: float = 2.0) -> bool:
        # Only port 77777 is considered healthy
        return port == 77777

    monkeypatch.setattr(ac, "sync_health", fake_sync_health)
    monkeypatch.setattr(ac, "read_server_info", lambda paths=None: {"port": 77777})
    assert ac.resolve_port(0) == 77777
    # Even if cached is bad, it should fallback to server_info port
    assert ac.resolve_port(1234) == 77777


def test_sync_post_json_retries_on_failure(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, json, timeout):
        calls["n"] += 1

        class FakeResp:
            def __init__(self, ok=True):
                self._ok = ok

            def raise_for_status(self):
                if not self._ok:
                    raise Exception("fail")

            def json(self):
                return {"completion": "ok", "status": 200}

        if "127.0.0.1:1234" in url:
            # First attempt fails to trigger retry
            raise Exception("connection refused")
        if "127.0.0.1:9999" in url:
            return FakeResp(ok=True)
        raise Exception("unexpected url: " + url)

    monkeypatch.setattr(ac.requests, "post", fake_post)
    # After failure on 1234, resolve_port should return 9999
    monkeypatch.setattr(ac, "resolve_port", lambda cached: 9999)

    data = ac.sync_post_json(1234, "/autocomplete", payload={"prefix": ""}, timeout=1)
    assert data.get("completion") == "ok"
    assert calls["n"] == 2  # one failure + one retry


def test_async_post_json_retries_on_failure(monkeypatch):
    attempts = {"n": 0}

    class FakeResp:
        def __init__(self, url):
            self.url = url
            self.status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            # status is 200 so no raise
            return None

        async def json(self):
            return {"completion": "ok_async", "status": 200}

    class BadCM:
        async def __aenter__(self):
            raise Exception("connection refused")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json, timeout):
            attempts["n"] += 1
            if "127.0.0.1:1234" in url:
                # First attempt should fail on context enter
                return BadCM()
            elif "127.0.0.1:9999" in url:
                return FakeResp(url)
            return FakeResp(url)

    # Patch ClientSession to our fake
    monkeypatch.setattr(ac.aiohttp, "ClientSession", lambda: FakeSession())
    # After first failure, re-resolve to new port
    monkeypatch.setattr(ac, "resolve_port", lambda cached: 9999)

    data = asyncio.run(ac.async_post_json(1234, "/autocomplete", payload={"prefix": ""}, timeout=1))
    assert data.get("completion") == "ok_async"
    assert attempts["n"] >= 2  # fail then retry