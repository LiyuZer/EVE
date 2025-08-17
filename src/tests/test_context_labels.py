import pytest
from src.context_tree import ContextTree, ContextNode


def make_node(u="", a="", s="", m=None):
    return ContextNode(u, a, s, m or {})


def test_labels_env_off_default(monkeypatch):
    # By default, labels should not appear
    monkeypatch.delenv("EVE_LOG_CONTEXT_LABELS", raising=False)
    monkeypatch.delenv("EVE_LOG_CONTEXT_TREE", raising=False)

    root = make_node("root", "agent", "system", {})
    tree = ContextTree(root)
    child = make_node("child", "agent2 words here", "system2", {})
    tree.add_node(child)

    out = tree.structure_string()
    assert "—" not in out
    assert f"[{child.content_hash}] (HEAD)" in out


def test_labels_param_override(monkeypatch):
    # Explicit include_labels=True should append labels even if env is off
    monkeypatch.delenv("EVE_LOG_CONTEXT_LABELS", raising=False)
    monkeypatch.delenv("EVE_LOG_CONTEXT_TREE", raising=False)

    root = make_node("r", "a content for label", "s", {})
    root.content_hash = "rootL1"
    tree = ContextTree(root)

    child = make_node("", "hello there general kenobi", "", {})
    child.content_hash = "childL2"
    tree.add_node(child)

    s = tree.structure_string(include_labels=True)
    assert "[childL2] (HEAD) — hello there general kenobi" in s


def test_labels_env_on_appended_after_head(monkeypatch):
    # Env var should enable labels without passing include_labels
    monkeypatch.setenv("EVE_LOG_CONTEXT_LABELS", "1")
    monkeypatch.delenv("EVE_LOG_CONTEXT_TREE", raising=False)

    root = make_node("", "root agent resp", "", {})
    root.content_hash = "rootZZZ1"
    tree = ContextTree(root)

    child = make_node("", "child agent text more", "", {})
    child.content_hash = "childZZZ2"
    tree.add_node(child)

    s = tree.structure_string()
    assert "[childZZZ2] (HEAD) — child agent text more" in s


def test_labels_precedence_metadata(monkeypatch):
    # metadata["label"] should take precedence over content-derived labels
    monkeypatch.delenv("EVE_LOG_CONTEXT_LABELS", raising=False)
    monkeypatch.delenv("EVE_LOG_CONTEXT_TREE", raising=False)

    root = make_node("", "a", "", {})
    tree = ContextTree(root)

    child = make_node("", "agent says hi", "", {"label": "PLAN"})
    tree.add_node(child)

    s = tree.structure_string(include_labels=True)
    assert "— PLAN" in s


def test_labels_truncation_limits(monkeypatch):
    # Long labels should be truncated by max_label_len and show an ellipsis
    monkeypatch.delenv("EVE_LOG_CONTEXT_LABELS", raising=False)
    monkeypatch.delenv("EVE_LOG_CONTEXT_TREE", raising=False)

    root = make_node("", "a", "", {})
    tree = ContextTree(root)

    long_text = "word " * 50
    child = make_node("", long_text, "", {})
    tree.add_node(child)

    s = tree.structure_string(include_labels=True, max_label_len=10)
    # Get the line with the HEAD marker and parse the label after the em dash
    line = next(l for l in s.splitlines() if "(HEAD)" in l)
    assert "— " in line
    label_part = line.split("—", 1)[1].strip()
    # Allow for 10 chars plus an ellipsis
    assert len(label_part) <= 11
    assert ("…" in label_part) or ("..." in label_part)
