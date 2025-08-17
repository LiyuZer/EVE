from __future__ import annotations
from flask import Flask, request, jsonify
from src.smart_terminal_agent import SmartTerminalAgent

app = Flask(__name__)
agent = SmartTerminalAgent(use_llm=False)


@app.route("/terminal/parse", methods=["POST"])
def parse():
    try:
        data = request.get_json(silent=True) or {}
        user_input = data.get("input", "")
        cmd = agent.parse_nl(user_input)
        return jsonify({
            "status": 200,
            "command": cmd,
        })
    except Exception as e:
        return jsonify({
            "status": 500,
            "error": str(e),
        }), 500

@app.route("/terminal/run", methods=["POST"])
def run():
    try:
        data = request.get_json(silent=True) or {}
        # Accept either explicit command or natural language under "input"
        cmd = data.get("command") or agent.parse_nl(data.get("input", ""))
        stdout, stderr = agent.execute_command(cmd)
        return jsonify({
            "status": 200,
            "command": cmd,
            "stdout": stdout,
            "stderr": stderr,
        })
    except Exception as e:
        return jsonify({
            "status": 500,
            "error": str(e),
        }), 500


if __name__ == "__main__":
    # Optional: run a local dev server
    app.run(host="127.0.0.1", port=5001, debug=False)
