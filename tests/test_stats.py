"""
Tests for ab_test_interpreter/stats.py

Run with: pytest tests/test_stats.py -v
No API keys required — pure math, no LLM calls.
"""

import math
import pytest
import numpy as np
from ab_test_interpreter.stats import (
    ABTestResult,
    ContinuousTestResult,
    check_normal_approximation,
    cohens_h,
    run_proportion_test,
    run_ttest,
    bayesian_ab_test,
    correct_multiple_tests,
    sample_size_for_proportion,
    sample_size_for_continuous,
    minimum_detectable_effect,
    _compute_power,
)


# ── check_normal_approximation ────────────────────────────────────────────────

def test_normal_approx_valid_for_large_n():
    assert check_normal_approximation(1000, 0.05) is True


def test_normal_approx_invalid_when_np_below_10():
    # n=100, p=0.05 → n*p = 5 < 10
    assert check_normal_approximation(100, 0.05) is False


def test_normal_approx_invalid_when_n_1mp_below_10():
    # n=100, p=0.95 → n*(1-p) = 5 < 10
    assert check_normal_approximation(100, 0.95) is False


def test_normal_approx_boundary():
    # n*p exactly 10 → should be valid (>=)
    assert check_normal_approximation(200, 0.05) is True  # 200*0.05=10


# ── cohens_h ──────────────────────────────────────────────────────────────────

def test_cohens_h_zero_when_equal():
    assert cohens_h(0.1, 0.1) == pytest.approx(0.0, abs=1e-10)


def test_cohens_h_positive_when_p2_greater():
    assert cohens_h(0.1, 0.2) > 0


def test_cohens_h_negative_when_p2_less():
    assert cohens_h(0.2, 0.1) < 0


def test_cohens_h_symmetric():
    assert abs(cohens_h(0.1, 0.2)) == pytest.approx(abs(cohens_h(0.2, 0.1)), rel=1e-6)


# ── run_proportion_test — happy path ─────────────────────────────────────────

def test_proportion_significant_lift():
    """Clear significant lift — should detect it."""
    result = run_proportion_test(
        control_conversions=300,
        control_n=10000,
        treatment_conversions=370,
        treatment_n=10000,
    )
    assert result.is_significant is True
    assert result.absolute_lift == pytest.approx(0.007, abs=1e-6)
    assert result.relative_lift == pytest.approx(0.007 / 0.03, rel=1e-4)
    assert result.ci_lower < result.absolute_lift < result.ci_upper
    assert result.p_value < 0.05


def test_proportion_not_significant_tiny_lift():
    """Tiny lift that shouldn't be significant."""
    result = run_proportion_test(
        control_conversions=300,
        control_n=10000,
        treatment_conversions=301,
        treatment_n=10000,
    )
    assert result.is_significant is False
    assert result.p_value > 0.05


def test_proportion_ci_contains_true_lift():
    """95% CI on absolute lift must bracket the observed lift."""
    result = run_proportion_test(320, 10000, 374, 10200)
    assert result.ci_lower < result.absolute_lift
    assert result.ci_upper > result.absolute_lift


def test_proportion_negative_lift():
    """Treatment performs worse — lift should be negative."""
    result = run_proportion_test(400, 10000, 300, 10000)
    assert result.absolute_lift < 0
    assert result.relative_lift < 0


def test_proportion_relative_lift_none_when_control_zero():
    """relative_lift must be None when control rate is 0."""
    result = run_proportion_test(0, 10000, 50, 10000)
    assert result.relative_lift is None
    assert result.relative_lift_ci_lower is None
    assert result.relative_lift_ci_upper is None


def test_proportion_rates_computed_correctly():
    result = run_proportion_test(500, 5000, 600, 5000)
    assert result.control_rate == pytest.approx(0.10, rel=1e-6)
    assert result.treatment_rate == pytest.approx(0.12, rel=1e-6)


def test_proportion_z_test_used_for_large_n():
    result = run_proportion_test(300, 10000, 370, 10000)
    assert result.normal_approx_valid is True
    assert result.fisher_used is False


# ── run_proportion_test — Fisher fallback ────────────────────────────────────

def test_proportion_fisher_fallback_low_count():
    """n*p < 10 should trigger Fisher's exact test."""
    result = run_proportion_test(
        control_conversions=3,
        control_n=200,
        treatment_conversions=8,
        treatment_n=200,
    )
    assert result.fisher_used is True
    assert result.normal_approx_valid is False
    # p-value still meaningful
    assert 0.0 <= result.p_value <= 1.0


def test_proportion_fisher_result_plausible():
    """Fisher fallback should still flag significance for very large effect."""
    result = run_proportion_test(
        control_conversions=2,
        control_n=100,
        treatment_conversions=15,
        treatment_n=100,
    )
    assert result.fisher_used is True
    assert result.p_value < 0.05


# ── run_proportion_test — SRM detection ──────────────────────────────────────

def test_proportion_srm_flagged_for_severe_imbalance():
    """50/50 expected split but 70/30 actual should flag SRM."""
    result = run_proportion_test(
        control_conversions=300,
        control_n=7000,
        treatment_conversions=130,
        treatment_n=3000,
        expected_split=0.5,
    )
    assert bool(result.srm_flagged) is True
    assert result.srm_p_value < 0.01


def test_proportion_no_srm_for_balanced_split():
    result = run_proportion_test(
        control_conversions=300,
        control_n=10000,
        treatment_conversions=330,
        treatment_n=10000,
        expected_split=0.5,
    )
    assert bool(result.srm_flagged) is False


def test_proportion_no_srm_for_intentional_unequal_split():
    """70/30 expected and 70/30 actual should not flag SRM."""
    result = run_proportion_test(
        control_conversions=300,
        control_n=7000,
        treatment_conversions=130,
        treatment_n=3000,
        expected_split=0.7,
    )
    assert bool(result.srm_flagged) is False


# ── run_proportion_test — CI/significance consistency ────────────────────────

def test_proportion_consistency_flag_set():
    """Result must always set significance_ci_consistent (Python or numpy bool)."""
    result = run_proportion_test(300, 10000, 370, 10000)
    assert isinstance(result.significance_ci_consistent, (bool, np.bool_))


# ── run_proportion_test — custom alpha ────────────────────────────────────────

def test_proportion_alpha_respected():
    """Raising alpha to 0.20 should make a borderline result significant."""
    result_strict = run_proportion_test(300, 10000, 320, 10000, alpha=0.01)
    result_lenient = run_proportion_test(300, 10000, 320, 10000, alpha=0.20)
    # p-value must be identical regardless of alpha
    assert result_strict.p_value == pytest.approx(result_lenient.p_value, rel=1e-6)
    # significance flag must reflect alpha
    if result_strict.p_value >= 0.01:
        assert result_strict.is_significant is False
    if result_lenient.p_value < 0.20:
        assert result_lenient.is_significant is True


# ── run_ttest ─────────────────────────────────────────────────────────────────

def test_ttest_significant_lift():
    result = run_ttest(
        control_mean=45.0, control_std=12.0, control_n=10000,
        treatment_mean=47.5, treatment_std=12.3, treatment_n=10000,
    )
    assert result.is_significant is True
    assert result.absolute_lift == pytest.approx(2.5, rel=1e-6)
    assert result.p_value < 0.05


def test_ttest_not_significant_tiny_lift():
    result = run_ttest(
        control_mean=45.0, control_std=12.0, control_n=100,
        treatment_mean=45.1, treatment_std=12.0, treatment_n=100,
    )
    assert result.is_significant is False


def test_ttest_negative_lift():
    result = run_ttest(
        control_mean=50.0, control_std=10.0, control_n=10000,
        treatment_mean=48.0, treatment_std=10.0, treatment_n=10000,
    )
    assert result.absolute_lift < 0
    assert result.relative_lift < 0


def test_ttest_relative_lift_none_when_control_zero():
    result = run_ttest(
        control_mean=0.0, control_std=5.0, control_n=10000,
        treatment_mean=2.0, treatment_std=5.0, treatment_n=10000,
    )
    assert result.relative_lift is None


def test_ttest_ci_brackets_lift():
    result = run_ttest(45.0, 12.0, 10000, 47.5, 12.3, 10000)
    assert result.ci_lower < result.absolute_lift < result.ci_upper


def test_ttest_welch_df_less_than_pooled():
    """Welch-Satterthwaite df should be <= n_c + n_t - 2 (always for unequal variance)."""
    result = run_ttest(45.0, 12.0, 500, 47.5, 20.0, 500)
    pooled_df = 500 + 500 - 2
    assert result.df <= pooled_df


def test_ttest_srm_detection():
    result = run_ttest(45.0, 12.0, 7000, 47.5, 12.0, 3000, expected_split=0.5)
    assert bool(result.srm_flagged) is True


# ── bayesian_ab_test ──────────────────────────────────────────────────────────

def test_bayesian_prob_in_range():
    prob, lift = bayesian_ab_test(300, 10000, 370, 10000)
    assert 0.0 <= prob <= 1.0


def test_bayesian_higher_prob_for_clear_winner():
    prob, _ = bayesian_ab_test(300, 10000, 500, 10000)
    assert prob > 0.99


def test_bayesian_near_50_for_equal_rates():
    prob, _ = bayesian_ab_test(300, 10000, 300, 10000)
    assert 0.40 <= prob <= 0.60


def test_bayesian_expected_lift_positive_when_treatment_wins():
    _, lift = bayesian_ab_test(300, 10000, 370, 10000)
    assert lift > 0


def test_bayesian_deterministic_with_seed():
    """Seeded RNG must produce identical results on repeated calls."""
    p1, l1 = bayesian_ab_test(300, 10000, 370, 10000)
    p2, l2 = bayesian_ab_test(300, 10000, 370, 10000)
    assert p1 == p2
    assert l1 == l2


# ── correct_multiple_tests (BH) ──────────────────────────────────────────────

def test_bh_empty_returns_empty():
    reject, thresholds = correct_multiple_tests([])
    assert reject == []
    assert thresholds == []


def test_bh_single_test():
    reject, thresholds = correct_multiple_tests([0.03])
    assert reject == [True]
    assert thresholds == [0.05]


def test_bh_single_not_significant():
    reject, _ = correct_multiple_tests([0.10])
    assert reject == [False]


def test_bh_rejects_clearly_significant():
    p_values = [0.001, 0.01, 0.8, 0.9]
    reject, _ = correct_multiple_tests(p_values)
    assert reject[0] is True
    assert reject[1] is True
    assert reject[2] is False
    assert reject[3] is False


def test_bh_preserves_original_order():
    """BH must restore original index order, not sorted order."""
    p_values = [0.9, 0.001, 0.8, 0.01]
    reject, _ = correct_multiple_tests(p_values)
    assert reject[1] is True   # p=0.001 should reject
    assert reject[0] is False  # p=0.9 should not reject


def test_bh_more_conservative_than_uncorrected():
    """At α=0.05, BH threshold for rank 1 of 5 tests = 0.05*1/5 = 0.01."""
    p_values = [0.03, 0.8, 0.9, 0.85, 0.7]
    reject, thresholds = correct_multiple_tests(p_values, alpha=0.05)
    # p=0.03 at rank 1: BH threshold = 0.05*1/5 = 0.01 → should NOT reject
    assert reject[0] is False


# ── sample_size_for_proportion ────────────────────────────────────────────────

def test_sample_size_proportion_positive():
    n = sample_size_for_proportion(baseline_rate=0.05, mde_absolute=0.005)
    assert n > 0


def test_sample_size_proportion_integer():
    n = sample_size_for_proportion(0.05, 0.005)
    assert isinstance(n, int)


def test_sample_size_proportion_larger_n_for_smaller_mde():
    n_small_mde = sample_size_for_proportion(0.05, 0.001)
    n_large_mde = sample_size_for_proportion(0.05, 0.01)
    assert n_small_mde > n_large_mde


def test_sample_size_proportion_larger_n_for_higher_power():
    n_80 = sample_size_for_proportion(0.05, 0.005, power=0.80)
    n_90 = sample_size_for_proportion(0.05, 0.005, power=0.90)
    assert n_90 > n_80


def test_sample_size_proportion_strictest_alpha_largest_n():
    n_lenient = sample_size_for_proportion(0.05, 0.005, alpha=0.10)
    n_strict = sample_size_for_proportion(0.05, 0.005, alpha=0.01)
    assert n_strict > n_lenient


# ── sample_size_for_continuous ────────────────────────────────────────────────

def test_sample_size_continuous_positive():
    n = sample_size_for_continuous(baseline_std=10.0, mde_absolute=1.0)
    assert n > 0


def test_sample_size_continuous_larger_std_needs_more_n():
    n_small_std = sample_size_for_continuous(5.0, 1.0)
    n_large_std = sample_size_for_continuous(20.0, 1.0)
    assert n_large_std > n_small_std


def test_sample_size_continuous_larger_mde_needs_less_n():
    n_small_mde = sample_size_for_continuous(10.0, 0.5)
    n_large_mde = sample_size_for_continuous(10.0, 2.0)
    assert n_small_mde > n_large_mde


# ── minimum_detectable_effect ─────────────────────────────────────────────────

def test_mde_positive():
    mde = minimum_detectable_effect(10000, 10000, 0.05)
    assert mde > 0


def test_mde_smaller_for_larger_n():
    mde_small_n = minimum_detectable_effect(1000, 1000, 0.05)
    mde_large_n = minimum_detectable_effect(100000, 100000, 0.05)
    assert mde_large_n < mde_small_n


def test_mde_handles_unequal_splits():
    """Unequal splits should increase MDE vs equal split at same total n."""
    n_total = 20000
    mde_equal = minimum_detectable_effect(10000, 10000, 0.05)
    mde_unequal = minimum_detectable_effect(17000, 3000, 0.05)
    assert mde_unequal > mde_equal


# ── _compute_power ────────────────────────────────────────────────────────────

def test_power_returns_alpha_when_zero_effect():
    """Zero effect size means power equals alpha (by definition)."""
    power = _compute_power(effect_size=0.0, n_control=5000, n_treatment=5000, alpha=0.05)
    assert power == pytest.approx(0.05, abs=1e-6)


def test_power_increases_with_n():
    p_small = _compute_power(0.2, 50, 50, 0.05)
    p_large = _compute_power(0.2, 5000, 5000, 0.05)
    assert p_large > p_small


def test_power_increases_with_effect_size():
    p_small_eff = _compute_power(0.1, 500, 500, 0.05)
    p_large_eff = _compute_power(0.5, 500, 500, 0.05)
    assert p_large_eff > p_small_eff


def test_power_bounded():
    p = _compute_power(2.0, 50000, 50000, 0.05)
    assert 0.0 <= p <= 1.0


def test_power_equal_split_result_in_range():
    """For equal splits, power should be in (0, 1) for a small effect at moderate n."""
    p = _compute_power(0.1, 300, 300, 0.05)
    assert 0.0 < p < 1.0


def test_power_lower_for_unequal_vs_equal_split_same_total():
    """Same total n but unequal split should give less power than equal split."""
    p_equal = _compute_power(0.2, 200, 200, 0.05)    # total=400
    p_unequal = _compute_power(0.2, 320, 80, 0.05)   # total=400, 80/20 split
    assert p_equal > p_unequal


# ── Integration: proportion test → power adequacy ────────────────────────────

def test_adequately_powered_test_detects_effect():
    """If n > required sample size, the test should be significant for the MDE."""
    baseline = 0.05
    mde = 0.005
    n = sample_size_for_proportion(baseline, mde) * 3  # well overpowered

    result = run_proportion_test(
        control_conversions=int(baseline * n),
        control_n=n,
        treatment_conversions=int((baseline + mde) * n),
        treatment_n=n,
    )
    assert result.is_significant is True
