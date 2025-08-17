import pytest

# Hard tier tests for the CFG acceptance function.
# Focus areas:
# - Non-left-recursive operator precedence grammar for + and * with parentheses
# - Dyck language with two bracket types requiring proper matching and nesting
# - Deeper balanced structures
# Contract:
#   from src.target_parser import accepts
#   accepts(grammar: dict, s: str) -> bool
# Grammar format: see tests/test_parser_easy.py.


@pytest.mark.difficulty("hard")
def test_operator_precedence_without_left_recursion():
    # Language: arithmetic expressions over terminal 'a' with + (lower precedence) and * (higher precedence)
    # Non-left-recursive grammar encoding left associativity for + and *:
    #   E  -> T E'
    #   E' -> + T E' | ε
    #   T  -> F T'
    #   T' -> * F T' | ε
    #   F  -> ( E ) | a
    grammar = {
        "start": "E",
        "rules": {
            "E": ["TE"],       # We'll encode E' as nonterminal "E" (prime) using another symbol, use R for E'
            "R": ["+TR", ""],  # R is E'
            "T": ["FT"],       # T' as nonterminal "T" (prime) using P
            "P": ["*FP", ""],  # P is T'
            "F": ["(E)", "a"],
        },
    }
    # NOTE: Above we referenced E' and T' as R and P, but also used E->TE which is wrong since E' symbol is R, T' is P.
    # Let's correct the rules mapping to use distinct symbols consistently:
    grammar = {
        "start": "E",
        "rules": {
            "E": ["TR"],
            "R": ["+TR", ""],
            "T": ["FP"],
            "P": ["*FP", ""],
            "F": ["(E)", "a"],
        },
    }

    from src.target_parser import accepts

    positives = [
        "a",
        "a+a",
        "a*a",
        "a+a*a",      # * binds tighter than +
        "(a+a)*a",
        "a*(a+a)",
        "a+a+a",
        "a*a*a",
        "(a+a)*(a+a)",
        "a+(a*a)+a",
    ]
    negatives = [
        "+a",    # starts with operator
        "a+",    # ends with operator
        "a**a",  # invalid double operator
        "a+*a",  # operator sequence
        "(a+a",  # unbalanced
        "a())",  # misplaced parentheses
        "a(a)",  # implicit multiplication not allowed by grammar
    ]

    for s in positives:
        assert accepts(grammar, s) is True, f"Expected True for {s!r}"
    for s in negatives:
        assert accepts(grammar, s) is False, f"Expected False for {s!r}"


@pytest.mark.difficulty("hard")
def test_dyck_two_types_parentheses_and_brackets():
    # Language: Balanced strings of () and [] with proper nesting and matching
    # Grammar:
    #   S -> P S | B S | ε
    #   P -> ( S )
    #   B -> [ S ]
    grammar = {
        "start": "S",
        "rules": {
            "S": ["PS", "BS", ""],
            "P": ["(S)"],
            "B": ["[S]"],
        },
    }
    from src.target_parser import accepts

    positives = [
        "",
        "()",
        "[]",
        "()[]",
        "[()]",
        "([])[]",
        "[()[[]]]",
        "()[[]]()",
    ]
    negatives = [
        "(]", "[)", "([)]", ")(", "][", ")", "(", "[[])(]",
    ]

    for s in positives:
        assert accepts(grammar, s) is True, f"Expected True for {s!r}"
    for s in negatives:
        assert accepts(grammar, s) is False, f"Expected False for {s!r}"


@pytest.mark.difficulty("hard")
def test_balanced_parentheses_deep():
    # Deep nesting to stress recursion/search limits
    grammar = {
        "start": "S",
        "rules": {
            "S": ["(S)S", ""],
        },
    }
    from src.target_parser import accepts

    positives = [
        "(((())))",           # depth 4
        "((()())(()()))",     # multiple groups
        "(()(()(())))()",     # trailing pair
    ]
    negatives = [
        "(((()))",            # missing closing
        "((()())))",          # extra closing
        "(()(()(()))))("
    ]

    for s in positives:
        assert accepts(grammar, s) is True, f"Expected True for {s!r}"
    for s in negatives:
        assert accepts(grammar, s) is False, f"Expected False for {s!r}"
