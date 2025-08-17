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

    # Accept epsilon only if explicitly allowed by start productions
    if s == "" and "" in rules.get(start, []):
        return True

    # For non-empty strings, try to match productions
    def can_derive(nt: str, remaining: str) -> bool:
        for production in rules.get(nt, []):
            if _matches_production(production, remaining, rules):
                return True
        return False

    def _matches_production(prod: str, s: str, rules: dict) -> bool:
        # Try to match production against string
        if not prod and not s:
            return True
        if not prod:
            return False
        if not s:
            # Check if rest of production can derive epsilon
            return _can_derive_epsilon(prod, rules)
        
        # Match first symbol
        first_sym = prod[0]
        rest_prod = prod[1:]
        
        if first_sym.isupper():
            # Nonterminal: try all possible splits
            for i in range(len(s) + 1):
                prefix = s[:i]
                suffix = s[i:]
                if can_derive(first_sym, prefix) and _matches_production(rest_prod, suffix, rules):
                    return True
            return False
        else:
            # Terminal
            if s[0] == first_sym:
                return _matches_production(rest_prod, s[1:], rules)
            else:
                return False
    
    def _can_derive_epsilon(nt: str, rules: dict, visited=None) -> bool:
        if visited is None:
            visited = set()
        if nt in visited:
            return False  # Prevent infinite recursion
        visited.add(nt)
        
        for production in rules.get(nt, []):
            if not production:
                return True
            # Check if all symbols in production can derive epsilon
            all_epsilon = True
            for sym in production:
                if sym.isupper():
                    if not _can_derive_epsilon(sym, rules, visited.copy()):
                        all_epsilon = False
                        break
                else:
                    all_epsilon = False
                    break
            if all_epsilon:
                return True
        return False

    return can_derive(start, s)
    """
    start, rules = _validate_grammar(grammar)

    # Accept epsilon only if explicitly allowed by start productions
    if s == "" and "" in rules.get(start, []):
        return True

    # Everything else is rejected by the initial stub
    return False