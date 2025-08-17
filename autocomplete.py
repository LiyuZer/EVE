'''
Autocomplete functionality for the code editor
We will create server side code to handle autocomplete requests
and return the appropriate completions based on the user's input.
'''

import json
import os
import socket
import time
import concurrent.futures

# Try to import Flask, but do not fail if unavailable (tests may spawn a different python3)
try:
    from flask import Flask, request, jsonify  # type: ignore
    HAVE_FLASK = True
except Exception:  # pragma: no cover - fallback path
    Flask = None  # type: ignore
    request = None  # type: ignore

    def jsonify(obj):  # type: ignore
        return json.dumps(obj)

    HAVE_FLASK = False


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


# Provide a test-mode stub to avoid external calls during tests
class _DummyAgent:
    def __init__(self, completion: str = "test_completion"):
        self._completion = completion

    def generate_completion(self, prefix: str, suffix: str, language=None, context=None):
        # simple deterministic reply that includes a bit of the prefix for sanity
        p = prefix if isinstance(prefix, str) else str(prefix)
        return f"{self._completion}:{p[-8:]}"


def _norm_text(x):
    """Normalize incoming payload values (may be list or str) to a plain string."""
    if isinstance(x, list):
        try:
            return "\n".join(str(part) for part in x)
        except Exception:
            return str(x)
    return x if isinstance(x, str) else str(x)


def _init_agent():
    """Initialize the autocomplete agent with robust fallbacks.

    Returns:
        (agent, mode): agent instance and human-readable mode string
    """
    # Test mode via environment ensures deterministic responses
    if os.getenv("EVE_AUTOCOMPLETE_TEST"):
        return _DummyAgent(), "test"

    # Prefer real mode only when FIREWORKS_API_KEY is present
    if os.getenv("FIREWORKS_API_KEY"):
        try:
            # Import lazily so environments without deps still work in tests
            from src.auto_completion import AutoCompletionAgent  # type: ignore

            agent = AutoCompletionAgent(
                completion_length=50,
                model=os.getenv("EVE_AC_MODEL", "gpt-4.1-nano"),
            )
            return agent, "real"
        except Exception:
            # Fall back to deterministic stub if real agent cannot initialize
            return _DummyAgent(), "test_fallback"

    # No Fireworks key -> default to stub so the editor stays responsive
    return _DummyAgent(), "test_fallback"


def _run_flask_server(port: int, agent, mode: str):  # pragma: no cover - exercised in integration
    app = Flask(__name__)  # type: ignore[name-defined]

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok', 'mode': mode})

    @app.route('/autocomplete', methods=['POST'])
    def autocomplete():
        data = request.get_json(force=True, silent=True) or {}  # type: ignore[name-defined]
        prefix = _norm_text(data.get('prefix', ''))
        suffix = _norm_text(data.get('suffix', ''))
        context = data.get('context', '')

        timeout_s = float(os.getenv("EVE_AC_TIMEOUT", "2.0"))

        def _call_agent():
            return agent.generate_completion(prefix, suffix, context=context)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                completion = ex.submit(_call_agent).result(timeout=timeout_s)
        except concurrent.futures.TimeoutError:
            # Fast fallback to keep UI snappy
            completion = _DummyAgent().generate_completion(prefix, suffix, context=context)
        except Exception:
            # Any backend error -> fallback
            completion = _DummyAgent().generate_completion(prefix, suffix, context=context)

        # Normalize return type to a string
        if isinstance(completion, list):
            completion = completion[0] if completion else ""
        if not isinstance(completion, str):
            completion = str(completion)
        return jsonify({'completion': completion, 'status': 200})

    # Bind to localhost only; enable threading; disable reloader for single-process behavior
    app.run(host='127.0.0.1', port=port, threaded=True, use_reloader=False)


def _run_builtin_http_server(port: int, agent, mode: str):  # pragma: no cover - exercised in integration
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, obj, code=200):
            body = json.dumps(obj).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # quieter
            return

        def do_GET(self):  # noqa: N802
            if self.path == '/health':
                self._send_json({'status': 'ok', 'mode': mode})
            else:
                self._send_json({'error': 'not found'}, code=404)

        def do_POST(self):  # noqa: N802
            if self.path != '/autocomplete':
                self._send_json({'error': 'not found'}, code=404)
                return
            length = int(self.headers.get('Content-Length') or '0')
            raw = self.rfile.read(length).decode('utf-8') if length else '{}'
            try:
                data = json.loads(raw) if raw else {}
            except Exception:
                data = {}
            prefix = _norm_text(data.get('prefix', ''))
            suffix = _norm_text(data.get('suffix', ''))
            context = data.get('context', '')
            try:
                completion = agent.generate_completion(prefix, suffix, context=context)
            except Exception:
                completion = _DummyAgent().generate_completion(prefix, suffix, context=context)
            if isinstance(completion, list):
                completion = completion[0] if completion else ""
            if not isinstance(completion, str):
                completion = str(completion)
            self._send_json({'completion': completion, 'status': 200})

    server = HTTPServer(('127.0.0.1', port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    # Initialize agent first so we know the mode for health
    agent, agent_mode = _init_agent()

    _port = find_free_port()

    # Keep stdout event for backward compatibility
    print(json.dumps({"event": "server_start", "port": _port, "mode": agent_mode}), flush=True)

    # Write server_info.json as a robust handshake for the IDE
    try:
        info = {
            'port': _port,
            'pid': os.getpid(),
            'started_at': time.time(),
            'mode': agent_mode,
        }
        # Primary: write to CWD (project root)
        try:
            with open('server_info.json', 'w', encoding='utf-8') as f:
                json.dump(info, f)
                try:
                    f.flush()
                    os.fsync(f.fileno())
                except Exception:
                    pass
        except Exception:
            pass
        # Secondary: also write to src/server_info.json as a fallback path
        try:
            import pathlib
            alt = pathlib.Path(__file__).resolve().parent / 'src' / 'server_info.json'
            alt.parent.mkdir(parents=True, exist_ok=True)
            with alt.open('w', encoding='utf-8') as f2:
                json.dump(info, f2)
                try:
                    f2.flush()
                    os.fsync(f2.fileno())
                except Exception:
                    pass
        except Exception:
            pass
    except Exception:
        # Non-fatal; IDE will still attempt stdout-based handshake
        pass

    # Prefer Flask if available; otherwise run a minimal built-in HTTP server
    if HAVE_FLASK:
        _run_flask_server(_port, agent, agent_mode)
    else:
        _run_builtin_http_server(_port, agent, agent_mode)