import os
from src.agent import Agent
from src.context_tree import ContextNode
from src.schema import ResponseBody, Interface


def test_copy_node_shallow_creates_isolated_root():
    agent = Agent(root=".", mode="ide")
    base = ContextNode(user_message="u", agent_response="a", system_response="s", metadata={"k": "v"})
    agent.context_tree.add_node(base)

    copy = agent._copy_node_shallow(base)

    # Different object and different hash (metadata carries copied_from)
    assert copy is not base
    assert copy.metadata.get("copied_from") == base.content_hash
    assert copy.content_hash != base.content_hash
    # No children copied
    assert getattr(copy, "children", []) == []


def test_action11_recurse_adds_completion_marker():
    # Prevent sub-agent loop from calling LLM
    os.environ["EVE_SUBAGENT_MAX_STEPS"] = "0"

    agent = Agent(root=".", mode="ide")
    # Seed a simple node and target it
    agent.context_tree.add_node(ContextNode(user_message="hello", agent_response="", system_response="", metadata={}))
    target_hash = agent.context_tree.head.content_hash

    iface = Interface(name="File System", description="Test iface", function=["noop() -> None"], complexity=1)
    rb = ResponseBody(
        action=11,
        action_description="Test recurse",
        node_hash=target_hash,
        node_content="Sub-goal: test",
        interface=iface,
    )

    agent.process_llm_response(rb, interactive=False)

    # Traverse and assert a Recurse Complete marker exists in parent context
    labels = []
    def walk(n):
        meta = getattr(n, "metadata", {}) or {}
        if isinstance(meta, dict):
            labels.append(meta.get("label"))
        for c in getattr(n, "children", []) or []:
            walk(c)
    walk(agent.context_tree.root)

    assert "Recurse Complete" in labels
