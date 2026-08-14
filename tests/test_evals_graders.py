"""Tests for the deterministic eval graders.

No API keys required. run_proportion_test is pure math, so we build real
ground-truth results and grade fixture output strings against them. This is the
free layer that runs in CI on every push.
"""
from ab_test_interpreter.stats import run_proportion_test, run_ttest
from evals.graders import (
    structure_fails,
    ab_faithfulness_fails,
    rca_faithfulness_fails,
    tradeoffs_faithfulness_fails,
    deterministic_grade,
)


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


def test_fisher_expectation_enforced():
    z_result = run_proportion_test(500, 10000, 650, 10000)   # normal approx, no Fisher
    assert z_result.fisher_used is False
    case = {"module": "ab_test", "expect": {"fisher_used": True}}
    # Hedged verdict so the significance check stays out of the way and this test
    # isolates the Fisher assertion.
    good = "RECOMMENDATION: Extend the test, evidence is inconclusive. FOLLOW-UP: collect more data."
    assert any("Fisher" in f for f in deterministic_grade(case, good, {"result": z_result}))

    f_result = run_proportion_test(2, 40, 8, 40)             # low counts force Fisher
    assert f_result.fisher_used is True
    assert deterministic_grade(case, good, {"result": f_result}) == []


# ── continuous (Welch t-test) faithfulness ────────────────────────────────────

def test_continuous_ship_on_nonsignificant_is_caught():
    result = run_ttest(12.0, 8.0, 3000, 12.2, 8.0, 3000)  # tiny diff, not significant
    assert result.is_significant is False
    bad = "RECOMMENDATION: Ship, the lift looks good. FOLLOW-UP: none."
    assert any("non-significant" in f for f in ab_faithfulness_fails(bad, result))


def test_continuous_zero_control_mean_forbids_relative_lift_number():
    result = run_ttest(0.0, 5.0, 2000, 3.0, 6.0, 2000)  # control mean 0
    assert result.control_mean == 0
    bad = "Relative lift is +300% here. RECOMMENDATION: Ship."
    assert any("relative-lift" in f for f in ab_faithfulness_fails(bad, result))
    good = "Relative lift is undefined at a 0 baseline. RECOMMENDATION: Extend the test."
    assert ab_faithfulness_fails(good, result) == []


# ── RCA depth: hypothesis matrix must cover the categories ────────────────────

def test_rca_thin_matrix_is_caught():
    thin = "## HYPOTHESIS MATRIX only mentions data quality and product changes."
    assert rca_faithfulness_fails(thin)  # 2/5 categories


def test_rca_full_matrix_passes():
    full = ("data quality issues, product changes, external seasonality, "
            "user segment shifts, and marketing changes are all considered")
    assert rca_faithfulness_fails(full) == []


# ── trade-offs depth: composite metric must carry a formula ───────────────────

def test_tradeoffs_composite_without_formula_is_caught():
    no_formula = "## COMPOSITE METRIC SUGGESTION\nWe recommend a balanced score of retention and quality."
    assert tradeoffs_faithfulness_fails(no_formula)


def test_tradeoffs_composite_with_formula_passes():
    with_formula = "## COMPOSITE METRIC SUGGESTION\nscore = 0.6 * retention + 0.4 * watch_time"
    assert tradeoffs_faithfulness_fails(with_formula) == []
