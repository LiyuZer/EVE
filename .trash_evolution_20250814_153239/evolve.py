#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Use the existing LLM interface (Fireworks path), do not modify src/llm.py
from src.llm import llmInterface

# --------------------------- Logging Setup ---------------------------
logger = logging.getLogger("evolve")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(ch)


# --------------------------- Patch Model ----------------------------
@dataclass
class Edit:
    op: str  # insert | replace | delete
    line: int  # 1-based
    count: int = 0  # for replace/delete
    text: str = ""  # for insert/replace


@dataclass
class Patch:
    edits: List[Edit]

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Patch":
        if not isinstance(d, dict) or "edits" not in d or not isinstance(d["edits"], list):
            raise ValueError("Patch must be a dict with key 'edits' as a list")
        edits: List[Edit] = []
        for e in d["edits"]:
            if not isinstance(e, dict):
                raise ValueError("Each edit must be a dict")
            op = e.get("op")
            line = e.get("line")
            count = e.get("count", 0)
            text = e.get("text", "")
            if op not in {"insert", "replace", "delete"}:
                raise ValueError(f"Invalid op: {op}")
            if not isinstance(line, int) or line < 1:
                raise ValueError("line must be positive int (1-based)")
            if op in {"replace", "delete"}:
                if not isinstance(count, int) or count < 1:
                    raise ValueError("count must be >=1 for replace/delete")
            if op in {"insert", "replace"}:
                if not isinstance(text, str):
                    raise ValueError("text must be string for insert/replace")
            edits.append(Edit(op=op, line=line, count=count, text=text))
        return Patch(edits=edits)


def apply_patch_lines(src: str, patch: Patch) -> Tuple[str, int]:
    """
    Apply a small patch to the given source (line-based), return (new_source, changed_lines_count).
    Lines are 1-based in the patch schema. Edits are applied in the order provided.
    """
    lines = src.splitlines()
    changed = 0

    for e in patch.edits:
        if e.op == "insert":
            insert_lines = e.text.splitlines()
            idx = e.line - 1
            if idx < 0:
                idx = 0
            if idx > len(lines):
                idx = len(lines)
            lines[idx:idx] = insert_lines
            changed += len(insert_lines)
        elif e.op == "replace":
            idx = e.line - 1
            if idx < 0 or idx + e.count > len(lines):
                raise ValueError("replace range out of bounds")
            repl_lines = e.text.splitlines()
            changed += max(e.count, len(repl_lines))
            lines[idx : idx + e.count] = repl_lines
        elif e.op == "delete":
            idx = e.line - 1
            if idx < 0 or idx + e.count > len(lines):
                raise ValueError("delete range out of bounds")
            changed += e.count
            del lines[idx : idx + e.count]
        else:
            raise ValueError(f"Unknown op: {e.op}")

    return ("\n".join(lines) + ("" if src.endswith("\n") else "")), changed


# --------------------------- Test Runner ----------------------------
@dataclass
class TestResult:
    returncode: int
    stdout: str
    stderr: str
    passed: int
    failed: int
    errors: int

    @property
    def pass_rate(self) -> float:
        denom = self.passed + self.failed + self.errors
        return (self.passed / denom) if denom else 0.0


SUMMARY_RE = re.compile(
    r"(?:(?P<passed>\d+)\s+passed)?(?:,\s*)?"
    r"(?:(?P<failed>\d+)\s+failed)?(?:,\s*)?"
    r"(?:(?P<errors>\d+)\s+errors?)?",
)


def parse_summary(text: str) -> Tuple[int, int, int]:
    """
    Parse pytest output to extract (passed, failed, errors).
    Works with normal verbosity numeric summary and with -q by falling back to
    counting the progress line characters (., F, E) and short summary lines.
    """
    passed = failed = errors = 0

    # 1) Try to find a numeric summary anywhere in the output
    last_match = None
    for m in SUMMARY_RE.finditer(text):
        if m and m.group(0).strip():
            last_match = m
    if last_match is not None:
        if last_match.group("passed"):
            passed = int(last_match.group("passed"))
        if last_match.group("failed"):
            failed = int(last_match.group("failed"))
        if last_match.group("errors"):
            errors = int(last_match.group("errors"))
        if passed or failed or errors:
            return passed, failed, errors

    # 2) Fallback for -q: count characters from the progress line (e.g., "FFF." or "..F.E")
    # We look for a line composed solely of [., F, E, s, x, X] optionally followed by [NN%]
    for line in text.splitlines():
        stripped = line.strip()
        # detect lines like "FFF.", "..F.E", or "..F.   [100%]"
        if stripped and all(ch in ".FEsxX[]%0123456789 " for ch in stripped):
            # Extract contiguous result symbols prefix
            seq = []
            for ch in stripped:
                if ch in ".FEsxX":
                    seq.append(ch)
                else:
                    # stop when we hit space or '[' etc.
                    break
            if seq:
                sym = "".join(seq)
                passed = sym.count('.')
                failed = sym.count('F')
                errors = sym.count('E')
                if passed or failed or errors:
                    return passed, failed, errors

    # 3) Fallback to parsing short test summary info lines if present
    lines = [l.lstrip() for l in text.splitlines()]
    failed_lines = sum(1 for l in lines if l.startswith("FAILED "))
    error_lines = sum(1 for l in lines if l.startswith("ERROR "))
    if failed_lines or error_lines:
        # We cannot reliably infer passes without total count; return zeros for passes.
        return 0, failed_lines, error_lines

    return 0, 0, 0


def run_pytest(test_files: List[str], timeout: int = 120) -> TestResult:
    cmd = [sys.executable, "-m", "pytest", "-q", "--maxfail=999", "--disable-warnings", *test_files]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") + "\n\nTIMEOUT\n"
        err = (e.stderr or "")
        return TestResult(returncode=124, stdout=out, stderr=err, passed=0, failed=0, errors=1)

    stdout = proc.stdout
    stderr = proc.stderr
    passed, failed, errors = parse_summary(stdout + "\n" + stderr)
    logger.info(f"pytest finished rc={proc.returncode} passed={passed} failed={failed} errors={errors}")
    return TestResult(returncode=proc.returncode, stdout=stdout, stderr=stderr, passed=passed, failed=failed, errors=errors)


# --------------------------- LLM Prompts ----------------------------
PATCH_SCHEMA_TEXT = (
    "{" \
    "\"edits\": [ {\"op\": \"insert\"|\"replace\"|\"delete\", \"line\": <1-based-int>, \"count\": <int-for-replace/delete>, \"text\": <string-for-insert/replace> } ]" \
    "}"
)


def build_system_message(max_edits: int, max_changed_lines: int) -> Dict[str, str]:
    content = f"""
You are a surgical code mutator. Task: produce a tiny patch to the target file to improve test outcomes.
Constraints:
- Emit ONLY a single JSON object string with key \"completion\" containing the patch JSON, nothing else.
- The patch JSON must match the schema: {PATCH_SCHEMA_TEXT}
- No more than {max_edits} edits total; keep total changed lines <= {max_changed_lines}.
- Do NOT rewrite the whole file; change only what is necessary for the current failing tests.
- Preserve function signatures and existing behavior unless needed to fix the current errors.
- Avoid adding new files or imports unless essential.
"""
    return {"role": "system", "content": textwrap.dedent(content).strip()}


def build_user_message(
    code: str,
    last_errors: str,
    tier: str,
    target_path: str,
    hints: Optional[str] = None,
    max_edits: int = 3,
    max_changed_lines: int = 12,
) -> Dict[str, str]:
    guidance = f"""
Current Tier: {tier.upper()}
Only optimize for the CURRENT tier tests.
Target File: {target_path}

Patch Rules:
- Use 1-based line numbers.
- Allowed operations: insert, replace, delete.
- At most {max_edits} edits; total changed lines <= {max_changed_lines}.
- Keep changes minimal and targeted to address the CURRENT failing tests.

Contract under test:
    accepts(grammar: dict, s: str) -> bool
Grammar format:
    grammar = {{"start": "S", "rules": {{ nonterminal: [production, ...] }}}}
    - Uppercase A-Z are nonterminals; other chars are terminals; "" is epsilon.

Last Errors (from tests of the CURRENT tier):
{last_errors}

Current Code:
"""
    content = textwrap.dedent(guidance).rstrip("\n") + "\n" + code
    return {"role": "user", "content": content}


# --------------------------- Evolution Core ----------------------------
@dataclass
class CandidateResult:
    success: bool
    new_code: Optional[str]
    changed_lines: int
    test: Optional[TestResult]
    patch_json: Optional[Dict[str, Any]]
    err: Optional[str] = None


def ensure_stub_exists(target_path: Path) -> None:
    if target_path.exists():
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        """
from __future__ import annotations
from typing import Dict, List

__all__ = ["accepts"]

def accepts(grammar: Dict, s: str) -> bool:
    # Baseline stub: accept epsilon only if start->"" is allowed
    if not isinstance(grammar, dict) or "start" not in grammar or "rules" not in grammar:
        raise ValueError("Invalid grammar")
    start = grammar["start"]
    rules = grammar["rules"]
    if s == "" and "" in rules.get(start, []):
        return True
    return False
""".lstrip()
    )


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write_text(p: Path, content: str) -> None:
    p.write_text(content, encoding="utf-8")


def llm_generate_patch(
    llm: llmInterface,
    code: str,
    last_errors: str,
    tier: str,
    target_path: str,
    max_edits: int,
    max_changed_lines: int,
) -> Dict[str, Any]:
    system_msg = build_system_message(max_edits=max_edits, max_changed_lines=max_changed_lines)
    user_msg = build_user_message(
        code=code,
        last_errors=last_errors,
        tier=tier,
        target_path=target_path,
        max_edits=max_edits,
        max_changed_lines=max_changed_lines,
    )
    # Fireworks path expects (input_json=user, completion_prompt=system) and returns a JSON string in "completion"
    try:
        completion_str = llm.generate_response_qwen(user_msg, system_msg)
        patch_obj = json.loads(completion_str)
        return patch_obj
    except Exception as e:
        # Fallback: Some Fireworks responses omit {"completion": ...} and place the patch directly in
        # choices[0].message.content within the error payload. Try to salvage it without changing llm.py.
        try:
            import ast  # local import to avoid global changes
            msg = str(e)
            start = msg.find("{")
            end = msg.rfind("}")
            if start != -1 and end != -1 and end > start:
                blob = msg[start : end + 1]
                # Convert single-quoted Python dict to object safely
                payload = ast.literal_eval(blob)
                choices = payload.get("choices") or []
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    if isinstance(content, str) and content.strip():
                        return json.loads(content)
        except Exception as salvage_err:
            logger.warning(f"Fallback parse of Fireworks response failed: {salvage_err}")
        # If we reach here, re-raise the original exception
        raise


def evaluate_candidate(
    patch_obj: Dict[str, Any],
    base_code: str,
    target_file: Path,
    tier_files: List[str],
    timeout: int,
) -> CandidateResult:
    try:
        patch = Patch.from_dict(patch_obj)
    except Exception as e:
        return CandidateResult(False, None, 0, None, patch_obj, err=f"Invalid patch: {e}")

    try:
        new_code, changed = apply_patch_lines(base_code, patch)
    except Exception as e:
        return CandidateResult(False, None, 0, None, patch_obj, err=f"Patch apply failed: {e}")

    orig = read_text(target_file)
    try:
        write_text(target_file, new_code)
        test_res = run_pytest(tier_files, timeout=timeout)
    finally:
        # Always restore original after test
        write_text(target_file, orig)

    return CandidateResult(True, new_code, changed, test_res, patch_obj)


def fitness(tr: TestResult, changed_lines: int) -> Tuple[int, int, int, int]:
    # Higher is better for first element, lower better for others
    # passed, -failed, -errors, -changed_lines
    return (tr.passed, -tr.failed, -tr.errors, -changed_lines)


def save_round_artifacts(
    round_dir: Path,
    base_code: str,
    baseline_test: TestResult,
    candidates: List[CandidateResult],
    accepted: Optional[CandidateResult],
) -> None:
    round_dir.mkdir(parents=True, exist_ok=True)
    write_text(round_dir / "code_before.py", base_code)
    write_text(round_dir / "baseline_output.txt", baseline_test.stdout + "\n" + baseline_test.stderr)
    meta = {
        "baseline": {
            "passed": baseline_test.passed,
            "failed": baseline_test.failed,
            "errors": baseline_test.errors,
            "returncode": baseline_test.returncode,
        },
        "candidates": [],
        "accepted": None,
    }
    for i, c in enumerate(candidates):
        cdir = round_dir / f"cand_{i+1:02d}"
        cdir.mkdir(exist_ok=True)
        if c.patch_json is not None:
            write_text(cdir / "patch.json", json.dumps(c.patch_json, indent=2))
        if c.new_code is not None:
            write_text(cdir / "code_after.py", c.new_code)
        if c.test is not None:
            write_text(cdir / "test_output.txt", c.test.stdout + "\n" + c.test.stderr)
            meta["candidates"].append(
                {
                    "changed_lines": c.changed_lines,
                    "passed": c.test.passed,
                    "failed": c.test.failed,
                    "errors": c.test.errors,
                }
            )
        else:
            meta["candidates"].append({"error": c.err or "unknown"})
    if accepted is not None and accepted.new_code is not None and accepted.test is not None:
        write_text(round_dir / "accepted_code.py", accepted.new_code)
        meta["accepted"] = {
            "changed_lines": accepted.changed_lines,
            "passed": accepted.test.passed,
            "failed": accepted.test.failed,
            "errors": accepted.test.errors,
        }
    write_text(round_dir / "meta.json", json.dumps(meta, indent=2))


# --------------------------- CLI and Main Loop ----------------------------
TIERS = ["easy_a_star", "easy_ab_star", "easy_parens", "medium", "hard"]
TIER_TESTS = {
    "easy_a_star": [
        "tests/test_parser_easy.py::test_a_star_basic",
        "tests/test_parser_easy.py::test_rejection_misc_short_strings",
    ],
    "easy_ab_star": [
        "tests/test_parser_easy.py::test_ab_star_basic",
    ],
    "easy_parens": [
        "tests/test_parser_easy.py::test_balanced_parentheses_shallow",
    ],
    "medium": ["tests/test_parser_medium.py"],
    "hard": ["tests/test_parser_hard.py", "tests/test_random_grammars.py"],
}
TIER_THRESHOLDS = {
    "easy_a_star": 1.0,
    "easy_ab_star": 1.0,
    "easy_parens": 1.0,
    "medium": 0.9,
    "hard": 1.0,
}


def evolve(
    target_path: str = "src/target_parser.py",
    rounds: int = 50,
    population: int = 3,
    start_tier: str = "easy_a_star",
    progressive: bool = True,
    timeout: int = 120,
    max_edits: int = 3,
    max_changed_lines: int = 12,
    model: str = "gpt-4.1-mini",  # model field is required by llmInterface even if unused in qwen
    fireworks_api_key: Optional[str] = None,
    artifacts_dir: str = ".evolve",
) -> None:
    # Prepare env for fireworks if provided
    if fireworks_api_key:
        os.environ.setdefault("FIREWORKS_API_KEY", fireworks_api_key)

    target_file = Path(target_path)
    ensure_stub_exists(target_file)

    # Initialize LLM interface (api_key can be None; llm.py handles resolution)
    llm = llmInterface(api_key=None, model=model)

    # Determine tier index
    if start_tier not in TIERS:
        raise ValueError(f"Unknown start_tier: {start_tier}")
    tier_idx = TIERS.index(start_tier)

    # Create artifacts base
    base_dir = Path(artifacts_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    # Track last errors per tier (feed only the previous step's errors)
    last_errors: str = "(initial run)"

    total_round = 0
    stagnation_count = 0
    while total_round < rounds and tier_idx < len(TIERS):
        tier = TIERS[tier_idx]
        test_files = TIER_TESTS[tier]
        total_round += 1
        round_dir = base_dir / f"round_{total_round:03d}_{tier}"
        logger.info(f"Round {total_round}/{rounds} | Tier: {tier}")

        # Determine local patch limits based on stagnation
        local_max_edits = max_edits
        local_max_changed_lines = max_changed_lines
        if stagnation_count >= 4:
            local_max_edits = max(local_max_edits, 8)
            local_max_changed_lines = max(local_max_changed_lines, 60)
        elif stagnation_count >= 2:
            local_max_edits = max(local_max_edits, 5)
            local_max_changed_lines = max(local_max_changed_lines, 24)
        logger.info(
            f"Patch limits: edits={local_max_edits}, lines={local_max_changed_lines} (stagnation={stagnation_count})"
        )

        # Read current code and run baseline tests for CURRENT tier
        base_code = read_text(target_file)
        baseline = run_pytest(test_files, timeout=timeout)
        last_errors = baseline.stdout + "\n" + baseline.stderr

        candidates: List[CandidateResult] = []
        for i in range(population):
            logger.info(f"Generating candidate {i+1}/{population} for tier {tier}")
            try:
                patch_obj = llm_generate_patch(
                    llm=llm,
                    code=base_code,
                    last_errors=last_errors,
                    tier=tier,
                    target_path=target_path,
                    max_edits=local_max_edits,
                    max_changed_lines=local_max_changed_lines,
                )
            except Exception as e:
                logger.error(f"Patch generation failed: {e}")
                candidates.append(CandidateResult(False, None, 0, None, None, err=str(e)))
                continue

            cand = evaluate_candidate(
                patch_obj=patch_obj,
                base_code=base_code,
                target_file=target_file,
                tier_files=test_files,
                timeout=timeout,
            )
            candidates.append(cand)

        # Select best
        best: Optional[CandidateResult] = None
        best_score: Optional[Tuple[int, int, int, int]] = None
        for c in candidates:
            if not c.success or c.test is None:
                continue
            score = fitness(c.test, c.changed_lines)
            if best_score is None or score > best_score:
                best_score = score
                best = c

        # Decide acceptance (only if improvement over baseline)
        accepted: Optional[CandidateResult] = None
        if best is not None and best.test is not None:
            base_score = fitness(baseline, 0)
            best_score = fitness(best.test, best.changed_lines)
            if best_score > base_score and best.new_code is not None:
                logger.info(
                    f"Accepting candidate: passed {best.test.passed} vs baseline {baseline.passed}, "
                    f"failed {best.test.failed} vs {baseline.failed}"
                )
                # Write accepted code to disk permanently
                write_text(target_file, best.new_code)
                accepted = best
                last_errors = best.test.stdout + "\n" + best.test.stderr
                stagnation_count = 0
            else:
                logger.info("No improvement this round; keeping current code.")
                stagnation_count += 1
        else:
            logger.info("No valid candidate produced test results.")
            stagnation_count += 1

        # Save artifacts
        save_round_artifacts(round_dir, base_code, baseline, candidates, accepted)

        # Check progression condition: if accepted exists and threshold met, advance tier
        if accepted is not None and accepted.test is not None:
            denom = accepted.test.passed + accepted.test.failed + accepted.test.errors
            rate = accepted.test.pass_rate if denom else 0.0
            threshold = TIER_THRESHOLDS[tier]
            logger.info(f"Tier {tier} pass-rate {rate:.2%} (threshold {threshold:.0%})")
            if progressive and denom > 0 and rate >= threshold:
                logger.info(f"Advancing from tier {tier} to next tier.")
                tier_idx += 1
                # Reset last_errors to fresh run on next tier
                last_errors = "(advanced tier; fresh run)"
                stagnation_count = 0
        # Otherwise continue on same tier until improvement

    logger.info("Evolution complete.")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Incremental evolution orchestrator with tiny patch edits (Fireworks)")
    p.add_argument("--target", default="src/target_parser.py", help="Target file to evolve")
    p.add_argument("--rounds", type=int, default=50, help="Total evolution rounds")
    p.add_argument("--population", type=int, default=3, help="Candidates per round")
    p.add_argument("--start-tier", choices=TIERS, default="easy_a_star", help="Tier to start with")
    p.add_argument("--no-progressive", action="store_true", help="Do not advance tiers automatically")
    p.add_argument("--timeout", type=int, default=120, help="Pytest timeout (seconds)")
    p.add_argument("--max-edits", type=int, default=3, help="Max edits per patch")
    p.add_argument("--max-changed-lines", type=int, default=12, help="Max total changed lines per patch")
    p.add_argument("--model", default="gpt-4.1-mini", help="Model name for llmInterface (unused by qwen path)")
    p.add_argument("--fireworks-key", default=None, help="Optional Fireworks API key (if llmInterface supports env)")
    p.add_argument("--artifacts", default=".evolve", help="Artifacts directory")

    args = p.parse_args(argv)

    try:
        evolve(
            target_path=args.target,
            rounds=args.rounds,
            population=args.population,
            start_tier=args.start_tier,
            progressive=not args.no_progressive,
            timeout=args.timeout,
            max_edits=args.max_edits,
            max_changed_lines=args.max_changed_lines,
            model=args.model,
            fireworks_api_key=args.fireworks_key,
            artifacts_dir=args.artifacts,
        )
    except Exception as e:
        logger.exception(f"Evolution failed: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())