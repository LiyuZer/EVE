import random
import itertools
import pytest

# Hard tier: Seeded random CFG generator + sampled positive/negative strings.
# The generator avoids left recursion and epsilon cycles and bounds derivation depth.
# We derive positives by bounded expansion (BFS) and create near-miss negatives.
# Contract under test: accepts(grammar: dict, s: str) -> bool in src.target_parser.py


def make_random_cfg(seed: int, max_nonterm=3, terminals=("a", "b")):
    rng = random.Random(seed)
    nonterms = [chr(ord("A") + i) for i in range(max_nonterm)]
    start = nonterms[0]

    rules: dict[str, list[str]] = {nt: [] for nt in nonterms}

    # Ensure each nonterminal has at least one production.
    # Productions are strings mixing terminals and uppercase nonterminals.
    # We avoid immediate left recursion by not starting a production with its own symbol.
    for i, nt in enumerate(nonterms):
        prod_count = rng.randint(1, 3)
        for _ in range(prod_count):
            length = rng.randint(0, 3)  # allow epsilon
            prod = []
            for pos in range(length):
                if rng.random() < 0.5 and i + 1 < len(nonterms):
                    # Only allow references to later nonterminals to reduce cycles
                    ref = rng.choice(nonterms[i + 1 :])
                    prod.append(ref)
                else:
                    prod.append(rng.choice(terminals))
            production = "".join(prod)
            # Avoid left recursion A -> A ... (should not happen due to construction but double-check)
            if production.startswith(nt):
                continue
            rules[nt].append(production)
        # Always include epsilon sometimes to allow empty languages
        if rng.random() < 0.5:
            rules[nt].append("")
        # Fallback if we accidentally skipped all
        if not rules[nt]:
            rules[nt] = [""]

    grammar = {"start": start, "rules": rules}
    return grammar


def derive_strings(grammar: dict, max_depth: int = 4, max_count: int = 200):
    """
    Bounded BFS to derive terminal strings from the grammar.
    Nonterminals are A-Z. Terminals are any other characters.
    """
    start = grammar["start"]
    rules = grammar["rules"]

    def is_terminal(s: str) -> bool:
        return all(not ch.isupper() for ch in s)

    # Start from start symbol
    queue = [(start, 0)]
    seen = set(queue)
    results = set()

    while queue and len(results) < max_count:
        cur, d = queue.pop(0)
        if is_terminal(cur):
            results.add(cur)
            continue
        if d >= max_depth:
            continue
        # Find first nonterminal to expand
        expand_idx = None
        for idx, ch in enumerate(cur):
            if ch.isupper():
                expand_idx = idx
                break
        if expand_idx is None:
            results.add(cur)
            continue
        nt = cur[expand_idx]
        prods = rules.get(nt, [])
        for p in prods:
            new_s = cur[:expand_idx] + p + cur[expand_idx + 1 :]
            state = (new_s, d + 1)
            if state not in seen and len(new_s) <= 12:  # bound length to keep set manageable
                seen.add(state)
                queue.append(state)

    # Sort for determinism
    return sorted(results)


def make_negatives(positives, terminals=("a", "b")):
    rng = random.Random(12345)
    negatives = set()
    for s in positives:
        if not s:
            negatives.add("x")  # out-of-alphabet
            continue
        # Try flipping one char or inserting/removing
        i = rng.randrange(len(s))
        # flip
        flip = s[:i] + (terminals[1] if s[i] == terminals[0] else terminals[0]) + s[i + 1 :]
        negatives.add(flip)
        # remove
        negatives.add(s[:i] + s[i + 1 :])
        # insert
        negatives.add(s[:i] + rng.choice(terminals) + s[i:])
        if len(negatives) >= len(positives) * 2 + 5:
            break
    # Ensure negatives are not colliding with positives
    return [n for n in negatives if n not in positives]


@pytest.mark.difficulty("hard")
@pytest.mark.parametrize("seed", [7, 11, 19])
def test_random_cfg_samples(seed):
    grammar = make_random_cfg(seed=seed, max_nonterm=3, terminals=("a", "b"))
    from src.target_parser import accepts

    positives = derive_strings(grammar, max_depth=4, max_count=100)
    # Limit to a handful to keep test runtime sane
    positives = [s for s in positives if len(s) <= 8][:10]

    # If there are no positives due to construction, include epsilon when allowed
    if not positives:
        start = grammar["start"]
        if "" in grammar["rules"].get(start, []):
            positives = [""]

    negatives = make_negatives(positives)
    # Remove any negatives that are actually positives (safety)
    negatives = [n for n in negatives if n not in positives][:10]

    # Sanity: avoid completely empty both sets; if both empty, skip
    if not positives and not negatives:
        pytest.skip("No derivable positives/negatives under bounds for this seed")

    for s in positives:
        assert accepts(grammar, s) is True, f"Seed {seed}: expected True for {s!r} under grammar {grammar}"
    for s in negatives:
        assert accepts(grammar, s) is False, f"Seed {seed}: expected False for {s!r} under grammar {grammar}"
