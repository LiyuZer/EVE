import pytest

# Easy tier tests for a minimal CFG acceptance function.
# Contract under test:
#   from src.target_parser import accepts
#   accepts(grammar: dict, s: str) -> bool
# Grammar representation:
#   grammar = {
#       "start": "S",
#       "rules": {
#           # Each production is a string where:
#           #  - Uppercase letters (A-Z) denote nonterminals
#           #  - Any other characters are terminals (e.g., '(', ')', 'a', 'b')
#           #  - The empty string "" denotes epsilon (ε)
#           # Concatenation is by juxtaposition, e.g., "abS" means terminal 'a', terminal 'b', then nonterminal S.
#           "S": ["aS", ""]  # Example: a*
#       }
#   }
# The EASY tier focuses on very small grammars that are solvable with straightforward recursion/brute force
# and shallow search, including epsilon, simple right-linear recursion, and shallow balanced parentheses.


@pytest.mark.difficulty("easy")
def test_a_star_basic():
    # Language: a*
    grammar = {
        "start": "S",
        "rules": {
            "S": ["aS", ""],  # S -> a S | ε
        },
    }
    from src.target_parser import accepts

    # Positive cases
    assert accepts(grammar, "") is True
    assert accepts(grammar, "a") is True
    assert accepts(grammar, "aa") is True
    assert accepts(grammar, "aaaaaa") is True

    # Negative cases
    assert accepts(grammar, "b") is False
    assert accepts(grammar, "ab") is False
    assert accepts(grammar, "ba") is False


@pytest.mark.difficulty("easy")
def test_ab_star_basic():
    # Language: (ab)*
    grammar = {
        "start": "S",
        "rules": {
            "S": ["abS", ""],  # S -> ab S | ε
        },
    }
    from src.target_parser import accepts

    # Positive cases
    assert accepts(grammar, "") is True
    assert accepts(grammar, "ab") is True
    assert accepts(grammar, "abab") is True
    assert accepts(grammar, "ababab") is True

    # Negative cases
    assert accepts(grammar, "a") is False
    assert accepts(grammar, "b") is False
    assert accepts(grammar, "aba") is False
    assert accepts(grammar, "abb") is False


@pytest.mark.difficulty("easy")
def test_balanced_parentheses_shallow():
    # Language: Balanced parentheses with shallow depth
    # Grammar: S -> ( S ) S | ε
    grammar = {
        "start": "S",
        "rules": {
            "S": ["(S)S", ""],
        },
    }
    from src.target_parser import accepts

    # Positive cases (depth up to 3 pairs)
    for s in [
        "",
        "()",
        "()()",
        "(())",
        "(()())",
        "((()))",
    ]:
        assert accepts(grammar, s) is True, f"Expected True for {s!r}"

    # Negative cases
    for s in [
        "(",
        ")",
        "())(",
        "(()",
        "())",
        "(()()(()",  # unbalanced
    ]:
        assert accepts(grammar, s) is False, f"Expected False for {s!r}"


@pytest.mark.difficulty("easy")
def test_rejection_misc_short_strings():
    # Ensure obvious mismatches are rejected for simple grammars
    grammar = {
        "start": "S",
        "rules": {
            "S": ["aS", ""],  # a*
        },
    }
    from src.target_parser import accepts

    for s in ["b", "ba", "ab", "bb", "aababb"]:
        assert accepts(grammar, s) is False
