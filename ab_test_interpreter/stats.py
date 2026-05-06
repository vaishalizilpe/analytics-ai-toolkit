"""Pure statistical logic — no Claude, no Streamlit."""
import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import Optional


@dataclass
class ContinuousTestResult:
    control_mean: float
    treatment_mean: float
    control_std: float
    treatment_std: float
    control_n: int
    treatment_n: int
    absolute_lift: float
    relative_lift: Optional[float]
    t_stat: float
    df: float
    p_value: float
    is_significant: bool
    ci_lower: float
    ci_upper: float
    power: float
    srm_p_value: float
    srm_flagged: bool


@dataclass
class ABTestResult:
    control_rate: float
    treatment_rate: float
    relative_lift: Optional[float]           # None when control_rate is 0
    absolute_lift: float
    p_value: float
    is_significant: bool
    ci_lower: float
    ci_upper: float
    relative_lift_ci_lower: Optional[float]  # None when control_rate is 0; delta method
    relative_lift_ci_upper: Optional[float]
    control_n: int
    treatment_n: int
    control_conversions: int
    treatment_conversions: int
    power: float
    srm_p_value: float
    srm_flagged: bool
    normal_approx_valid: bool  # False triggers Fisher fallback
    fisher_used: bool
    # Pooled SE (test) vs unpooled SE (CI) can disagree — flag it explicitly
    significance_ci_consistent: bool


def check_normal_approximation(n: int, p: float) -> bool:
    """Normal approx to the binomial holds when n*p >= 10 and n*(1-p) >= 10."""
    return n * p >= 10 and n * (1 - p) >= 10


def cohens_h(p1: float, p2: float) -> float:
    """Arcsine-transformed effect size for proportions. More accurate than Cohen's d at extreme rates."""
    return 2 * np.arcsin(np.sqrt(p2)) - 2 * np.arcsin(np.sqrt(p1))


def run_proportion_test(
    control_conversions: int,
    control_n: int,
    treatment_conversions: int,
    treatment_n: int,
    alpha: float = 0.05,
    expected_split: float = 0.5,
) -> ABTestResult:
    control_rate = control_conversions / control_n
    treatment_rate = treatment_conversions / treatment_n
    relative_lift = (treatment_rate - control_rate) / control_rate if control_rate > 0 else None
    absolute_lift = treatment_rate - control_rate

    # Validate normal approximation for both arms before using z-test
    control_ok = check_normal_approximation(control_n, control_rate)
    treatment_ok = check_normal_approximation(treatment_n, treatment_rate)
    normal_approx_valid = control_ok and treatment_ok

    if normal_approx_valid:
        pooled_rate = (control_conversions + treatment_conversions) / (control_n + treatment_n)
        se_pooled = np.sqrt(pooled_rate * (1 - pooled_rate) * (1 / control_n + 1 / treatment_n))
        z_stat = absolute_lift / se_pooled if se_pooled > 0 else 0.0
        p_value = float(2 * (1 - stats.norm.cdf(abs(z_stat))))
        fisher_used = False
    else:
        # Fisher's exact test — valid for any sample size, no distributional assumptions
        table = [
            [control_conversions, control_n - control_conversions],
            [treatment_conversions, treatment_n - treatment_conversions],
        ]
        _, p_value = stats.fisher_exact(table, alternative="two-sided")
        p_value = float(p_value)
        fisher_used = True

    z_critical = stats.norm.ppf(1 - alpha / 2)

    if not fisher_used:
        # Wald CI — valid when normal approximation holds.
        se = np.sqrt(
            (control_rate * (1 - control_rate) / control_n)
            + (treatment_rate * (1 - treatment_rate) / treatment_n)
        )
        ci_lower = absolute_lift - z_critical * se
        ci_upper = absolute_lift + z_critical * se
    else:
        # Clopper-Pearson exact CI per arm, then propagate to the difference.
        # CP lower/upper for each arm: Beta(k, n-k+1) and Beta(k+1, n-k) quantiles.
        # CI on the difference: (p2_lower - p1_upper, p2_upper - p1_lower) — conservative
        # but always valid regardless of sample size or conversion rate.
        alpha_cp = alpha  # same nominal level
        ctrl_lo = float(stats.beta.ppf(alpha_cp / 2, control_conversions, control_n - control_conversions + 1)) \
            if control_conversions > 0 else 0.0
        ctrl_hi = float(stats.beta.ppf(1 - alpha_cp / 2, control_conversions + 1, control_n - control_conversions)) \
            if control_conversions < control_n else 1.0
        trt_lo = float(stats.beta.ppf(alpha_cp / 2, treatment_conversions, treatment_n - treatment_conversions + 1)) \
            if treatment_conversions > 0 else 0.0
        trt_hi = float(stats.beta.ppf(1 - alpha_cp / 2, treatment_conversions + 1, treatment_n - treatment_conversions)) \
            if treatment_conversions < treatment_n else 1.0
        ci_lower = trt_lo - ctrl_hi
        ci_upper = trt_hi - ctrl_lo

    # Relative lift CI via delta method (requires normal approx — not valid for Fisher fallback).
    # Set to None when Fisher's was used, matching the treatment of relative_lift itself.
    if control_rate > 0 and not fisher_used:
        var_p1 = control_rate * (1 - control_rate) / control_n
        var_p2 = treatment_rate * (1 - treatment_rate) / treatment_n
        var_relative = (1 / control_rate ** 2) * var_p2 + (treatment_rate ** 2 / control_rate ** 4) * var_p1
        rel_se = np.sqrt(var_relative)
        relative_lift_ci_lower = float((relative_lift or 0) - z_critical * rel_se)
        relative_lift_ci_upper = float((relative_lift or 0) + z_critical * rel_se)
    else:
        relative_lift_ci_lower = None
        relative_lift_ci_upper = None

    # CI vs significance consistency check.
    # Pooled SE (z-test) vs unpooled SE (CI) can produce different decisions at the boundary.
    ci_excludes_zero = (ci_lower > 0) or (ci_upper < 0)
    is_significant = p_value < alpha
    significance_ci_consistent = is_significant == ci_excludes_zero

    # Power via Cohen's h (arcsine transform) — correct for proportions at extreme rates.
    # Retained for MDE adequacy check in the UI; not displayed as a gauge (see Gelman).
    # Uses harmonic-mean effective n so unequal splits are handled correctly.
    effect_size = abs(cohens_h(control_rate, treatment_rate)) if (control_rate + treatment_rate) > 0 else 0
    power = _compute_power(effect_size, control_n, treatment_n, alpha)

    # Sample Ratio Mismatch
    total = control_n + treatment_n
    expected_control = total * expected_split
    _, srm_p = stats.chisquare(
        [control_n, treatment_n],
        f_exp=[expected_control, total - expected_control],
    )
    srm_flagged = srm_p < 0.01

    return ABTestResult(
        control_rate=control_rate,
        treatment_rate=treatment_rate,
        relative_lift=relative_lift,
        absolute_lift=absolute_lift,
        p_value=p_value,
        is_significant=is_significant,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        relative_lift_ci_lower=relative_lift_ci_lower,
        relative_lift_ci_upper=relative_lift_ci_upper,
        control_n=control_n,
        treatment_n=treatment_n,
        control_conversions=control_conversions,
        treatment_conversions=treatment_conversions,
        power=power,
        srm_p_value=srm_p,
        srm_flagged=srm_flagged,
        normal_approx_valid=normal_approx_valid,
        fisher_used=fisher_used,
        significance_ci_consistent=significance_ci_consistent,
    )


def _compute_power(effect_size: float, n_control: float, n_treatment: float, alpha: float) -> float:
    """Compute power for a two-sample test.

    Uses the harmonic-mean effective sample size so the formula is correct for
    both equal and unequal splits.  For an equal 50/50 split this reduces to
    the familiar sqrt(n/2) expression.

    effective_n = 2 * n_c * n_t / (n_c + n_t)  (harmonic mean of the two arms)
    power = Φ(d * sqrt(effective_n / 2) - z_α/2)
    """
    if effect_size == 0:
        return alpha
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    effective_n = 2 * n_control * n_treatment / (n_control + n_treatment)
    z_power = effect_size * np.sqrt(effective_n / 2) - z_alpha
    return float(stats.norm.cdf(z_power))


def run_ttest(
    control_mean: float,
    control_std: float,
    control_n: int,
    treatment_mean: float,
    treatment_std: float,
    treatment_n: int,
    alpha: float = 0.05,
    expected_split: float = 0.5,
) -> ContinuousTestResult:
    absolute_lift = treatment_mean - control_mean
    relative_lift = absolute_lift / control_mean if control_mean != 0 else None

    # Welch's t-test — does not assume equal variances
    var_c = control_std ** 2 / control_n
    var_t = treatment_std ** 2 / treatment_n
    se = np.sqrt(var_c + var_t)
    t_stat = absolute_lift / se if se > 0 else 0.0

    # Welch-Satterthwaite degrees of freedom
    df = (var_c + var_t) ** 2 / (
        var_c ** 2 / (control_n - 1) + var_t ** 2 / (treatment_n - 1)
    )

    p_value = float(2 * (1 - stats.t.cdf(abs(t_stat), df)))

    t_critical = stats.t.ppf(1 - alpha / 2, df)
    ci_lower = absolute_lift - t_critical * se
    ci_upper = absolute_lift + t_critical * se

    pooled_std = np.sqrt(
        ((control_n - 1) * control_std ** 2 + (treatment_n - 1) * treatment_std ** 2)
        / (control_n + treatment_n - 2)
    )
    effect_size = abs(absolute_lift) / pooled_std if pooled_std > 0 else 0
    power = _compute_power(effect_size, control_n, treatment_n, alpha)

    total = control_n + treatment_n
    expected_control = total * expected_split
    _, srm_p = stats.chisquare(
        [control_n, treatment_n],
        f_exp=[expected_control, total - expected_control],
    )

    return ContinuousTestResult(
        control_mean=control_mean,
        treatment_mean=treatment_mean,
        control_std=control_std,
        treatment_std=treatment_std,
        control_n=control_n,
        treatment_n=treatment_n,
        absolute_lift=absolute_lift,
        relative_lift=relative_lift,
        t_stat=t_stat,
        df=df,
        p_value=p_value,
        is_significant=p_value < alpha,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        power=power,
        srm_p_value=srm_p,
        srm_flagged=srm_p < 0.01,
    )


def bayesian_ab_test(
    control_conv: int,
    control_n: int,
    treatment_conv: int,
    treatment_n: int,
    simulations: int = 50000,
) -> tuple:
    """Beta-Binomial Bayesian A/B test with uniform prior.

    Returns (prob_treatment_wins, expected_relative_lift).
    Interpretation: prob_treatment_wins = P(treatment CR > control CR).
    """
    rng = np.random.default_rng(42)
    # Uniform prior Beta(1,1) + observed data = Beta(conv+1, failures+1)
    ctrl = rng.beta(control_conv + 1, control_n - control_conv + 1, simulations)
    trt = rng.beta(treatment_conv + 1, treatment_n - treatment_conv + 1, simulations)
    prob_treatment_wins = float(np.mean(trt > ctrl))
    mask = ctrl > 0
    expected_lift = float(np.mean((trt[mask] - ctrl[mask]) / ctrl[mask]))
    return prob_treatment_wins, expected_lift


def correct_multiple_tests(p_values: list, alpha: float = 0.05) -> tuple:
    """Benjamini-Hochberg FDR correction. Returns (reject, corrected_alpha_thresholds).

    reject[i] is True if hypothesis i is rejected after correction.
    """
    m = len(p_values)
    if m == 0:
        return [], []
    if m == 1:
        return [p_values[0] < alpha], [alpha]

    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    sorted_indices = [i for i, _ in indexed]
    sorted_p = [p for _, p in indexed]

    # BH threshold for rank k (1-indexed): alpha * k / m
    bh_thresholds = [alpha * (k + 1) / m for k in range(m)]

    # Find largest k where p_(k) <= threshold
    last_reject = -1
    for k in range(m - 1, -1, -1):
        if sorted_p[k] <= bh_thresholds[k]:
            last_reject = k
            break

    reject_sorted = [k <= last_reject for k in range(m)]

    # Restore original order
    reject = [False] * m
    thresholds = [0.0] * m
    for rank, orig_idx in enumerate(sorted_indices):
        reject[orig_idx] = reject_sorted[rank]
        thresholds[orig_idx] = bh_thresholds[rank]

    return reject, thresholds


def sample_size_for_proportion(
    baseline_rate: float,
    mde_absolute: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> int:
    """Returns n per variant to detect mde_absolute from baseline_rate."""
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    p2 = float(np.clip(baseline_rate + mde_absolute, 0.0, 1.0))
    n = (
        z_alpha * np.sqrt(2 * baseline_rate * (1 - baseline_rate))
        + z_power * np.sqrt(baseline_rate * (1 - baseline_rate) + p2 * (1 - p2))
    ) ** 2 / mde_absolute ** 2
    return int(np.ceil(n))


def sample_size_for_continuous(
    baseline_std: float,
    mde_absolute: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> int:
    """Returns n per variant to detect mde_absolute given baseline_std."""
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    n = 2 * ((z_alpha + z_power) * baseline_std / mde_absolute) ** 2
    return int(np.ceil(n))


def minimum_detectable_effect(
    n_control: int,
    n_treatment: int,
    baseline_rate: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> float:
    """MDE using actual arm sizes — correct for unequal splits."""
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    se = np.sqrt(baseline_rate * (1 - baseline_rate) * (1 / n_control + 1 / n_treatment))
    return (z_alpha + z_power) * se
