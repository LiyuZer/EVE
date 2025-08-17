import pytest

# Medium tier tests for the CFG acceptance function.
# These require handling of mutual recursion, alternation via multiple productions,
# and deeper nesting than the easy tier.
# Contract:
#   from src.target_parser import accepts
#   accepts(grammar: dict, s: str) -> bool
# Grammar format: see tests/test_parser_easy.py.


@pytest.mark.difficulty("medium")
def test_an_bn_medium():
    # Language: a^n b^n (n >= 0)
    # Grammar: S -> a S b | ε
    grammar = {
        "start": "S",
        "rules": {
            "S": ["aSb", ""],
        },
    }
    from src.target_parser import accepts

    # Positives
    for s in ["", "ab", "aabb", "aaabbb", "aaaabbbb"]:
        assert accepts(grammar, s) is True, f"Expected True for {s!r}"

    # Negatives
    for s in ["a", "b", "aba", "aab", "abb", "ba", "aaabbbb", "bbb" ]:
        assert accepts(grammar, s) is False, f"Expected False for {s!r}"


@pytest.mark.difficulty("medium")
def test_alternation_and_concatenation():
    # Language: (a|b) c* d
    # Grammar:
    #   S -> A C D
    #   A -> a | b
    #   C -> c C | ε
    #   D -> d
    grammar = {
        "start": "S",
        "rules": {
            "S": ["ACD"],
            "A": ["a", "b"],
            "C": ["cC", ""],
            "D": ["d"],
        },
    }
    from src.target_parser import accepts

    positives = ["ad", "acd", "accd", "bccd", "bccccd"]
    negatives = ["a", "abd", "dd", "cd", "abcd", "", "d", "ac"]

    for s in positives:
        assert accepts(grammar, s) is True, f"Expected True for {s!r}"
    for s in negatives:
        assert accepts(grammar, s) is False, f"Expected False for {s!r}"


@pytest.mark.difficulty("medium")
def test_balanced_parentheses_moderate():
    # Language: Balanced parentheses
    # Grammar: S -> ( S ) S | ε
    grammar = {
        "start": "S",
        "rules": {
            "S": ["(S)S", ""],
        },
    }
    from src.target_parser import accepts

    positives = [
        "",
        "()",
        "(())",
        "()()",
        "(()())",
        "((()))",
        "()(()())",
        "((()()))",
    ]
    negatives = [
        "(", ")", "())(", "(()", "())", "(()()(()", "(()))(",
    ]

    for s in positives:
        assert accepts(grammar, s) is True, f"Expected True for {s!r}"
    for s in negatives:
        assert accepts(grammar, s) is False, f"Expected False for {s!r}"


@pytest.mark.difficulty("medium")
def test_even_length_palindromes_small():
    # Language: even-length palindromes over {a,b}
    # Grammar: S -> a S a | b S b | ε
    grammar = {
        "start": "S",
        "rules": {
            "S": ["aSa", "bSb", ""],
        },
    }
    from src.target_parser import accepts

    positives = ["", "aa", "bb", "abba", "baab", "aabbaa", "bbaabb"]
    negatives = ["a", "b", "aba", "abbaab", "ab", "aabbab"]

    for s in positives:
        assert accepts(grammar, s) is True, f"Expected True for {s!r}"
    for s in negatives:
        assert accepts(grammar, s) is False, f"Expected False for {s!r}"
