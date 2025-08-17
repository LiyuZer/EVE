import os
from src.context_tree import ContextNode, ContextTree


def make_node(u="u", a="a", s="s", m=None):
    return ContextNode(u, a, s, m or {})


def test_structure_string_returns_hashes():
    root = make_node("root", "agent", "system", {})
    tree = ContextTree(root)

    child = make_node("child", "agent2", "system2", {})
    tree.add_node(child)

    out = tree.structure_string()
    assert "=== CONTEXT TREE STRUCTURE ===" in out
    assert f"[{root.content_hash}]" in out
    assert f"[{child.content_hash}]" in out

    # HEAD should be on the latest node (child)
    assert f"[{child.content_hash}] (HEAD)" in out
    assert f"[{root.content_hash}] (HEAD)" not in out


def test_prints_when_env_set(monkeypatch, capsys):
    monkeypatch.setenv("EVE_LOG_CONTEXT_TREE", "1")

    root = make_node("r", "a", "s", {})
    tree = ContextTree(root)

    first = capsys.readouterr().out
    assert "=== CONTEXT TREE STRUCTURE ===" in first
    assert f"[{root.content_hash}] (HEAD)" in first

    child = make_node("c", "a2", "s2", {})
    tree.add_node(child)

    second = capsys.readouterr().out
    assert "=== CONTEXT TREE STRUCTURE ===" in second
    assert f"[{child.content_hash}] (HEAD)" in second
