import pytest
from src.context_tree import ContextTree, ContextNode
from src.schema import ResponseBody, Diff
from src.agent import Agent
from src.shell import ShellInterface


class DummyTerminal:
    def print_agent_message(self, msg):
        pass

    def print_username(self):
        pass

    def print_system_message(self, msg):
        pass


class DummyAgent(Agent):
    def __init__(self, tree: ContextTree):
        # Avoid heavy init; only what process_llm_response needs
        self.context_tree = tree
        self.terminal = DummyTerminal()


def make_rb(action: int, node_hash: str | None = None, node_content: str | None = None) -> ResponseBody:
    return ResponseBody(
        action=action,
        action_description="test",
        shell_command="",
        file_action=0,
        file_name="",
        write_content="",
        finished=False,
        response=None,
        diff=Diff(line_range_1=[0, 0], line_range_2=[0, 0], Add=False, Remove=False, Replace=False, content=""),
        node_hash=node_hash or "",
        node_content=node_content or "",
        save_content="",
        retrieve_content="",
    )


def test_action6_add_under_head_and_specific_parent_and_fallback():
    root = ContextNode(user_message="", agent_response="", system_response="", metadata={})
    tree = ContextTree(root)
    agent = DummyAgent(tree)

    # Add under head (root)
    rb1 = make_rb(6, node_hash="", node_content="first")
    prev_head = tree.head
    agent.process_llm_response(rb1)
    first = tree.head
    assert first.agent_response == "first"
    assert prev_head.children and prev_head.children[-1].content_hash == first.content_hash

    # Add under specific parent (root), even though current head is 'first'
    rb2 = make_rb(6, node_hash=root.content_hash, node_content="second")
    agent.process_llm_response(rb2)
    second = tree.head
    assert len(root.children) == 2
    assert second.agent_response == "second"
    assert root.children[-1].content_hash == second.content_hash

    # Invalid parent -> fallback to current HEAD (which is 'second')
    prev_head = tree.head
    rb3 = make_rb(6, node_hash="deadbeef", node_content="third")
    agent.process_llm_response(rb3)
    third = tree.head
    assert prev_head.children and prev_head.children[-1].content_hash == third.content_hash
    assert third.agent_response == "third"


def test_shell_timeout_and_truncation():
    sh = ShellInterface(timeout_seconds=1, max_capture=1000)

    # Command that should timeout quickly
    stdout, stderr = sh.execute_command("sleep 2")
    assert stdout == ""
    assert "SYSTEM_BLOCK: Command timed out" in stderr

    # Command that produces large output to test truncation behavior
    out, err = sh.execute_command("yes x | head -c 60000")
    assert len(out) <= 1050  # small margin for truncation marker
    assert ("[...truncated" in out) or (len(out) <= 1000)
