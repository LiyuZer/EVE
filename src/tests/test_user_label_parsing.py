import pytest
from src.agent import parse_user_label


@pytest.mark.parametrize(
    "text, label, msg",
    [
        ("[label: Planning] Build feature X", "Planning", "Build feature X"),
        ("{label: Bug Fix} Fix null refs", "Bug Fix", "Fix null refs"),
        ("label: Research | Read papers", "Research", "Read papers"),
        ("  [label:   Sprint 1 ]   Kick off  ", "Sprint 1", "Kick off"),
        ("No label here", None, "No label here"),
        ("label: Missing bar separator only label", None, "label: Missing bar separator only label"),
    ],
)
def test_parse_user_label(text, label, msg):
    got_label, cleaned = parse_user_label(text)
    assert got_label == label
    assert cleaned == msg
