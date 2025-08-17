import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import asyncio
from importlib import import_module

import pytest


ac_client = import_module("src.eve_ide_app.ac_client")


def test_build_url_formats_path_and_ipv4():
    assert ac_client.build_url(1234, "autocomplete") == "http://127.0.0.1:1234/autocomplete"
    assert ac_client.build_url(1234, "/autocomplete") == "http://127.0.0.1:1234/autocomplete"


def test_fallback_completion_str_and_list():
    assert ac_client.fallback_completion("abcdefghi") == "test_completion:bcdefghi"  # last 8
    assert ac_client.fallback_completion(["foo", "bar"]) == "test_completion:foo\nbar"
    assert ac_client.fallback_completion("") == "test_completion:"


def test_read_server_info_with_monkeypatched_paths(tmp_path, monkeypatch):
    primary = tmp_path / "server_info.json"
    secondary = tmp_path / "src" / "server_info.json"
    secondary.parent.mkdir(parents=True, exist_ok=True)

    (tmp_path / "other.json").write_text("{}", encoding="utf-8")
    primary.write_text('{"port": 5678, "status": "ok"}', encoding="utf-8")

    def fake_candidates():
        return [primary, secondary]

    monkeypatch.setattr(ac_client, "_candidate_info_paths", fake_candidates)
    info = ac_client.read_server_info()
    assert isinstance(info, dict)
    assert info.get("port") == 5678

    # If none exist -> None
    primary.unlink()
    monkeypatch.setattr(ac_client, "_candidate_info_paths", lambda: [primary, secondary])
    assert ac_client.read_server_info() is None


def test_resolve_port_prefers_cached_then_server_info(monkeypatch):
    calls = {"health": []}

    def fake_sync_health(p, timeout=2.0):
        calls["health"].append(p)
        # only 9999 and 7777 are healthy in this test
        return p in (9999, 7777)

    monkeypatch.setattr(ac_client, "sync_health", fake_sync_health)

    # Case 1: cached healthy
    assert ac_client.resolve_port(9999) == 9999

    # Case 2: cached unhealthy, read server_info and validate healthy port
    monkeypatch.setattr(ac_client, "read_server_info", lambda: {"port": 7777})
    assert ac_client.resolve_port(1111) == 7777

    # Case 3: none healthy
    monkeypatch.setattr(ac_client, "read_server_info", lambda: {"port": 2222})
    assert ac_client.resolve_port(0) == 0


def test_sync_post_json_retry_success(monkeypatch):
    # Arrange a failing first POST and succeeding retry with a re-resolved port
    events = {"count": 0}

    class FakeResp:
        def __init__(self, status_code=200, data=None):
            self.status_code = status_code
            self._data = data or {}

        def raise_for_status(self):
            if self.status_code != 200:
                raise Exception("HTTP error")

        def json(self):
            return self._data

    def fake_post(url, json=None, timeout=5.0):
        events["count"] += 1
        if events["count"] == 1:
            return FakeResp(500)  # first attempt fails
        return FakeResp(200, {"ok": True, "url": url})

    monkeypatch.setattr(ac_client.requests, "post", fake_post)
    monkeypatch.setattr(ac_client, "resolve_port", lambda p: 4242)

    out = ac_client.sync_post_json(1111, "/autocomplete", payload={"x": 1})
    assert out["ok"] is True
    assert "127.0.0.1:4242" in out["url"]
    assert events["count"] == 2


def test_async_post_json_retry_success(monkeypatch):
    # Arrange a failing first POST and succeeding retry with a re-resolved port for aiohttp path
    call_counter = {"post": 0}

    class FakeAiohttpResponse:
        def __init__(self, status=200, data=None):
            self.status = status
            self._data = data or {}

        def raise_for_status(self):
            if self.status != 200:
                raise Exception("HTTP error")

        async def json(self):
            return self._data

    class FakeCM:
        def __init__(self, response):
            self._resp = response

        async def __aenter__(self):
            return self._resp

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json=None, timeout=5.0):
            call_counter["post"] += 1
            if call_counter["post"] == 1:
                return FakeCM(FakeAiohttpResponse(500))
            return FakeCM(FakeAiohttpResponse(200, {"ok": True, "url": url}))

    # Patch aiohttp.ClientSession used inside the module
    monkeypatch.setattr(ac_client.aiohttp, "ClientSession", FakeSession)
    monkeypatch.setattr(ac_client, "resolve_port", lambda p: 9090)

    async def runner():
        return await ac_client.async_post_json(1111, "/autocomplete", payload={"x": 2})

    out = asyncio.run(runner())
    assert out["ok"] is True
    assert "127.0.0.1:9090" in out["url"]
    assert call_counter["post"] == 2