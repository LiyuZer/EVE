import pytest
from src.context_tree import ContextTree, ContextNode


def build_tree():
    root = ContextNode(
        user_message="",
        agent_response="",
        system_response="system prompt here",
        metadata={"root": True},
    )
    tree = ContextTree(root)
    n1 = ContextNode(user_message="Hello Eve", agent_response="", system_response="", metadata={"k1": "v1"})
    tree.add_node(n1)  # under HEAD (root)
    n2 = ContextNode(user_message=None, agent_response="Planning step", system_response="", metadata={"k2": "v2"})
    tree.add_node(n2)  # under HEAD (n1)
    n3 = ContextNode(user_message=None, agent_response="Deeper step", system_response="", metadata={})
    tree.add_node(n3)  # under HEAD (n2)
    return tree, root, n1, n2, n3


def snapshot_structure(tree: ContextTree) -> str:
    # structure_string provides a stable representation for equality checks
    return tree.structure_string(include_labels=True)


def test_replace_preserves_children_and_hash():
    tree, root, n1, n2, n3 = build_tree()
    old_hash = n1.content_hash
    # Assert child chain exists before
    assert n1.children and n1.children[0] is n2
    # Replace n1 summary
    ok = tree.replace(node_hash=n1.content_hash, replacement_val="<summary>")
    assert ok is True
    # Identity unchanged
    assert n1.content_hash == old_hash
    # Children preserved
    assert n1.children and n1.children[0] is n2
    # Grandchildren preserved
    assert n2.children and n2.children[0] is n3


def test_replace_updates_summary_and_label():
    tree, root, n1, n2, n3 = build_tree()
    ok = tree.replace(node_hash=n2.content_hash, replacement_val="Short summary", node_label="Replaced Node")
    assert ok is True
    # Summary fields updated
    assert n2.user_message == "Short summary"
    assert n2.agent_response == "Short summary"
    # Metadata marked and label set
    assert isinstance(n2.metadata, dict)
    assert n2.metadata.get("replaced") is True
    assert n2.metadata.get("label") == "Replaced Node"


def test_replace_does_not_move_head():
    tree, root, n1, n2, n3 = build_tree()
    # After build_tree, HEAD should be the last added node n3
    assert tree.head is n3
    # Replace an ancestor node (n1)
    ok = tree.replace(node_hash=n1.content_hash, replacement_val="<n1>")
    assert ok is True
    # HEAD remains unchanged
    assert tree.head is n3
    # Replace the HEAD itself
    ok2 = tree.replace(node_hash=n3.content_hash, replacement_val="<n3>")
    assert ok2 is True
    assert tree.head is n3


def test_replace_root_keeps_tree_and_head():
    tree, root, n1, n2, n3 = build_tree()
    # HEAD is n3 at this point
    assert tree.head is n3
    ok = tree.replace(node_hash=root.content_hash, replacement_val="<root>", node_label="Root Summarized")
    assert ok is True
    # Root still has its child (n1)
    assert root.children and root.children[0] is not None
    # HEAD remains at n3
    assert tree.head is n3
    # Label applied on root
    assert isinstance(root.metadata, dict)
    assert root.metadata.get("label") == "Root Summarized"


def test_replace_invalid_hash_no_mutation():
    tree, root, n1, n2, n3 = build_tree()
    before = snapshot_structure(tree)
    ok = tree.replace(node_hash="deadbeef", replacement_val="won't apply")
    after = snapshot_structure(tree)
    assert ok is False
    assert before == after
