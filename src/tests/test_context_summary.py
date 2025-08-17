import pytest
from src.context_tree import ContextTree, ContextNode


def build_sample_tree():
    root = ContextNode(
        user_message="",
        agent_response="",
        system_response="system prompt here",
        metadata={"root": True},
    )
    tree = ContextTree(root)
    # Add a few nodes
    n1 = ContextNode(user_message="Hello Eve", agent_response="", system_response="", metadata={"k1": "v1"})
    tree.add_node(n1)  # under HEAD (root)
    n2 = ContextNode(user_message=None, agent_response="Planning: step1; step2; step3;" * 10, system_response="", metadata={"Shell Command": "ls", "STDOUT": "a" * 1000})
    tree.add_node(n2)  # under HEAD (n1)
    # Prune n1 to test pruned marker (this removes its children, including n2)
    tree.prune(node_hash=n1.content_hash, replacement_val="<pruned>")
    return tree, root, n1, n2


def test_summary_string_contains_expected_headers_and_hashes():
    tree, root, n1, n2 = build_sample_tree()
    s = tree.summary_string()
    assert "=== CONTEXT TREE (SUMMARY) ===" in s
    assert root.content_hash in s
    assert n1.content_hash in s
    # Since n1 was pruned, its children (including n2) are removed from the tree
    assert n2.content_hash not in s


def test_summary_marks_head_and_pruned():
    tree, root, n1, n2 = build_sample_tree()
    s = tree.summary_string()
    # After pruning, HEAD should be re-anchored to the pruned node n1
    assert f"[{n1.content_hash}] (HEAD)" in s or "(HEAD)" in s
    # n1 was pruned and should be marked as such
    assert f"[{n1.content_hash}]" in s and "[PRUNED]" in s


def test_summary_truncation_applies():
    # Build an unpruned tree with long content to verify truncation occurs
    root2 = ContextNode(user_message="", agent_response="", system_response="system prompt here", metadata={"root": True})
    tree2 = ContextTree(root2)
    long_agent = "Planning: step1; step2; step3;" * 50
    n_long = ContextNode(user_message=None, agent_response=long_agent, system_response="S" * 2000, metadata={"Shell Command": "ls", "STDOUT": "a" * 5000})
    tree2.add_node(n_long)
    s = tree2.summary_string(max_len=60, max_keys=2)
    # long agent/system fields should be truncated with ellipsis
    assert "…" in s or "..." in s
    # metadata keys should be summarized (we expect to see keys not values)
    assert "Shell Command" in s or "STDOUT" in s