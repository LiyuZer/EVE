import json
import os
import sys
import types
import pytest

from src.smart_terminal_agent import SmartTerminalAgent
import smart_terminal_server as sts


def test_parse_basic_list_dir():
    agent = SmartTerminalAgent(use_llm=False)
    cmd = agent.parse_nl("list all files in the directory")
    assert cmd.startswith("ls -l")


def test_parse_hidden_in_src():
    agent = SmartTerminalAgent(use_llm=False)
    cmd = agent.parse_nl("show hidden files in src")
    assert "ls -la" in cmd and "src" in cmd


def test_parse_read_file_capped():
    agent = SmartTerminalAgent(use_llm=False)
    cmd = agent.parse_nl("open README.md")
    # ensure we cap output via sed and target file is present
    assert cmd.startswith("sed -n") and "README.md" in cmd


def test_parse_search_recursive():
    agent = SmartTerminalAgent(use_llm=False)
    cmd = agent.parse_nl('search for "Context Tree" in this project')
    assert "grep -R" in cmd and "Context Tree" in cmd


def test_execute_nl_passthrough_echo():
    agent = SmartTerminalAgent(use_llm=False)
    cmd, (out, err) = agent.execute_nl("echo hello world")
    assert cmd.startswith("echo hello world")
    assert out.strip() == "hello world"
    assert err == ""


def test_server_parse_endpoint_pwd():
    app = sts.app
    client = app.test_client()
    resp = client.post("/terminal/parse", json={"input": "where am i"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == 200
    assert data["command"] == "pwd"


def test_server_run_endpoint_echo():
    app = sts.app
    client = app.test_client()
    resp = client.post("/terminal/run", json={"command": "echo hi"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == 200
    assert data["command"] == "echo hi"
    assert data["stdout"].strip() == "hi"
    assert data["stderr"] == ""
