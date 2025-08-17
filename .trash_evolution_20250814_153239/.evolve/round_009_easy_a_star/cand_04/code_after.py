from __future__ import annotations
from typing import Dict, List

__all__ = ["accepts"]

"""
Minimal starting point for incremental evolution.

Contract under test (see tests/*):
    accepts(grammar: dict, s: str) -> bool

Grammar representation:
    grammar = {
        "start": "S",                     # start nonterminal (single uppercase letter)
        "rules": {                         # mapping from nonterminal -> list of productions
            # A production is a string where:
            #   - Uppercase letters (A-Z) are nonterminals
            #   - Any other characters are terminals (e.g., 'a', 'b', '(', ')', '[', ']')
            #   - The empty string "" denotes epsilon (ε)
            # Concatenation is by juxtaposition, e.g., "abS" means 'a' 'b' then nonterminal S.
            # Example:
            #   "S": ["aS", ""]   # a*
        }
    }

Design note:
    This stub intentionally implements only the simplest possible behavior so the
    evolutionary loop can grow capabilities via tiny mutations:
      - Accept only the empty string when start directly derives epsilon.
      - Reject everything else.

    Early EASY tests with epsilon in the start productions may partially pass, while
    other cases will fail and guide incremental patches.
"""


def _validate_grammar(grammar: Dict) -> tuple[str, Dict[str, List[str]]]:
    if not isinstance(grammar, dict):
        raise TypeError("grammar must be a dict with keys 'start' and 'rules'")
    if "start" not in grammar or "rules" not in grammar:
        raise ValueError("grammar must contain 'start' and 'rules'")
    start = grammar["start"]
    rules = grammar["rules"]
    if not isinstance(start, str) or not start:
        raise ValueError("grammar['start'] must be a non-empty string")
    if not isinstance(rules, dict):
        raise ValueError("grammar['rules'] must be a dict")
    # Normalize rule lists
    norm_rules: Dict[str, List[str]] = {}
    for nt, prods in rules.items():
        if not isinstance(nt, str) or not nt:
            raise ValueError("Nonterminal keys must be non-empty strings")
        if not isinstance(prods, list):
            raise ValueError(f"Productions for {nt!r} must be a list of strings")
        norm_list: List[str] = []
        for p in prods:
            if not isinstance(p, str):
                raise ValueError(f"Production for {nt!r} must be a string, got {type(p)}")
            norm_list.append(p)
        norm_rules[nt] = norm_list
    return start, norm_rules


def accepts(grammar: Dict, s: str) -> bool:
    """Return True iff string s is in the language of the given CFG.

    Minimal baseline:
      - Accept only epsilon when the start symbol directly derives epsilon.
      - Reject all other strings.
    # Accept epsilon only if explicitly allowed by start productions
    if s == "" and "" in rules.get(start, []):
        return True

    # Simple case: if string is 'a' and there's a direct production 'aS' or 'a'
    if s == "a" and start in rules:
        for production in rules[start]:
            if production == "a" or production == "aS":
                return True

    # Everything else is rejected by the initial stub
    return False

    # Accept epsilon only if explicitly allowed by start productions
    if s == "" and "" in rules.get(start, []):
        return True

    # Everything else is rejected by the initial stub
    return False