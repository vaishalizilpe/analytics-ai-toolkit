"""Graders for the eval loop.

Two layers:
  1. Deterministic graders (no API, no cost, run in CI). Pure functions of the
     output string plus the ground-truth stats. Each returns a list of failure
     strings; empty list means pass.
  2. LLM-as-judge (optional, costs API calls). Scores correctness, faithfulness,
     and actionability 0-5 against the ground truth. Nondeterministic, so it is
     NOT the CI gate, it is a signal you read during error analysis.
"""
import json
import re

# The prompts in shared/prompts.py require these exact sections. If a section is
# missing, the output is malformed regardless of how good the prose is.
REQUIRED_SECTIONS = {
    "ab_test":   ["RECOMMENDATION", "FOLLOW-UP"],
    "rca":       ["IMMEDIATE TRIAGE", "HYPOTHESIS MATRIX", "TOP 3 PRIORITIES"],
    "tradeoffs": ["METRIC HIERARCHY", "TRADE-OFF SURFACE", "GUARDRAIL", "RECOMMENDATION"],
}


def structure_fails(module, output):
    up = output.upper()
    return [f"missing section: {s}" for s in REQUIRED_SECTIONS[module] if s not in up]


def ab_faithfulness_fails(output, result):
    """Check the interpretation against the deterministic stats it was handed."""
    fails = []
    low = output.lower()

    # A non-significant result must not be sold as a clean win. Look at the
    # recommendation region and reject a bare "ship" verdict there.
    rec_region = low.split("recommendation", 1)[-1]
    ships = re.search(r"\bship\b", rec_region)
    hedged = any(w in rec_region for w in ["don't ship", "do not ship", "extend", "not ship", "hold"])
    if not result.is_significant and ships and not hedged:
        fails.append("recommended Ship on a non-significant result")

    # Sample Ratio Mismatch is a validity threat. If flagged, it must surface.
    if result.srm_flagged and "sample ratio" not in low and "srm" not in low:
        fails.append("SRM flagged but never mentioned")

    # Zero control rate: relative lift is undefined. The output must not quote a
    # relative-lift value. Look just after each "relative lift" mention; a signed
    # number or a percentage there is a violation, unless the text says undefined.
    if result.control_rate == 0:
        for m in re.finditer(r"relative lift(.{0,25})", low):
            window = m.group(1)
            has_value = re.search(r"[-+]\d|\d+(\.\d+)?%", window)
            excused = any(w in window for w in ["undefined", "n/a", "cannot", "not defined"])
            if has_value and not excused:
                fails.append("stated a relative-lift number at 0% control rate")
                break

    return fails


def deterministic_grade(case, output, ctx):
    """All no-API checks for a case. Returns a list of failure strings."""
    fails = structure_fails(case["module"], output)
    if case["module"] == "ab_test" and "result" in ctx:
        fails += ab_faithfulness_fails(output, ctx["result"])
    return fails


# ── Optional LLM-as-judge (costs API calls, not the CI gate) ───────────────────

_JUDGE_SYSTEM = (
    "You are a strict grader of an analytics assistant's output. "
    "Trust the ground truth over the output. Return JSON only, no prose."
)


def _ground_truth(case, ctx):
    if case["module"] == "ab_test" and "result" in ctx:
        r = ctx["result"]
        return (f"significant={r.is_significant}, p={r.p_value:.4f}, "
                f"srm_flagged={r.srm_flagged}, relative_lift={r.relative_lift}")
    return "n/a (no numeric ground truth for this module)"


def llm_judge(case, output, ctx):
    from shared.claude_client import ask_claude  # lazy import so CI stays API-free

    user = f"""MODULE: {case['module']}
GROUND TRUTH: {_ground_truth(case, ctx)}
ASSISTANT OUTPUT:
{output}

Score each 0-5:
- correctness: analytics reasoning is sound and matches the ground truth
- faithfulness: no invented numbers, nothing that contradicts the ground truth
- actionability: ends in a concrete decision or next step
Return JSON: {{"correctness":n,"faithfulness":n,"actionability":n,"failure_tags":["short"],"note":"one line"}}"""

    raw = ask_claude(_JUDGE_SYSTEM, user, max_tokens=400)
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {"correctness": 0, "faithfulness": 0, "actionability": 0,
                "failure_tags": ["judge_parse_error"], "note": "could not parse judge output"}
    return json.loads(match.group(0))
