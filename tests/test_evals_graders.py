"""Tests for the deterministic eval graders.

No API keys required. run_proportion_test is pure math, so we build real
ground-truth results and grade fixture output strings against them. This is the
free layer that runs in CI on every push.
"""
from ab_test_interpreter.stats import run_proportion_test
from evals.graders import structure_fails, ab_faithfulness_fails, deterministic_grade


# ── structure checks ──────────────────────────────────────────────────────────

def test_structure_pass_when_all_sections_present():
    out = "Here is the read. RECOMMENDATION: Ship. FOLLOW-UP: check mobile."
    assert structure_fails("ab_test", out) == []


def test_structure_flags_missing_section():
    out = "RECOMMENDATION: Ship. (no follow up here)"
    fails = structure_fails("ab_test", out)
    assert any("FOLLOW-UP" in f for f in fails)


def test_structure_rca_sections():
    out = "## IMMEDIATE TRIAGE ... ## HYPOTHESIS MATRIX ..."  # missing TOP 3 PRIORITIES
    fails = structure_fails("rca", out)
    assert any("TOP 3 PRIORITIES" in f for f in fails)


# ── A/B faithfulness against deterministic ground truth ───────────────────────

def test_ship_on_nonsignificant_is_caught():
    result = run_proportion_test(500, 10000, 515, 10000)  # p >> 0.05
    assert result.is_significant is False
    bad = "RECOMMENDATION: Ship it, looks great. FOLLOW-UP: none."
    assert any("non-significant" in f for f in ab_faithfulness_fails(bad, result))


def test_hedged_recommendation_on_nonsignificant_passes():
    result = run_proportion_test(500, 10000, 515, 10000)
    good = "RECOMMENDATION: Do not ship, the result is not significant. FOLLOW-UP: extend the test."
    assert ab_faithfulness_fails(good, result) == []


def test_srm_must_be_surfaced():
    result = run_proportion_test(250, 5000, 360, 7000)  # 5000 vs 7000 split
    assert bool(result.srm_flagged) is True
    silent = "RECOMMENDATION: Ship. FOLLOW-UP: watch retention."
    assert any("SRM" in f for f in ab_faithfulness_fails(silent, result))
    named = "Warning: sample ratio mismatch detected. RECOMMENDATION: Do not ship yet."
    assert ab_faithfulness_fails(named, result) == []


def test_zero_control_rate_forbids_relative_lift_number():
    result = run_proportion_test(0, 5000, 40, 5000)  # control rate 0
    assert result.control_rate == 0
    bad = "Relative lift is +800% here. RECOMMENDATION: Ship."
    assert any("relative-lift" in f for f in ab_faithfulness_fails(bad, result))
    good = "Relative lift is undefined at a 0% control rate. RECOMMENDATION: Extend the test."
    assert ab_faithfulness_fails(good, result) == []


def test_deterministic_grade_combines_layers():
    result = run_proportion_test(500, 10000, 515, 10000)
    case = {"module": "ab_test"}
    # missing FOLLOW-UP section AND a bad Ship verdict -> at least two failures
    bad = "RECOMMENDATION: Ship."
    fails = deterministic_grade(case, bad, {"result": result})
    assert len(fails) >= 2
