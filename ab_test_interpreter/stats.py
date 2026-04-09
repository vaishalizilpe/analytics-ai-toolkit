"""Pure statistical logic — no Claude, no Streamlit."""
import numpy as np
from scipy import stats
from dataclasses import dataclass


@dataclass
class ABTestResult:
    control_rate: float
    treatment_rate: float
    relative_lift: float
    absolute_lift: float
    p_value: float
    is_significant: bool
    ci_lower: float
    ci_upper: float
    control_n: int
    treatment_n: int
    power: float
    srm_p_value: float
    srm_flagged: bool


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
    relative_lift = (treatment_rate - control_rate) / control_rate if control_rate > 0 else 0
    absolute_lift = treatment_rate - control_rate

    # Two-proportion z-test (manual implementation using scipy.stats.norm)
    pooled_rate = (control_conversions + treatment_conversions) / (control_n + treatment_n)
    se_pooled = np.sqrt(pooled_rate * (1 - pooled_rate) * (1 / control_n + 1 / treatment_n))
    z_stat = absolute_lift / se_pooled if se_pooled > 0 else 0.0
    p_value = float(2 * (1 - stats.norm.cdf(abs(z_stat))))

    # 95% confidence interval on absolute lift
    se = np.sqrt(
        (control_rate * (1 - control_rate) / control_n)
        + (treatment_rate * (1 - treatment_rate) / treatment_n)
    )
    z_critical = stats.norm.ppf(1 - alpha / 2)
    ci_lower = absolute_lift - z_critical * se
    ci_upper = absolute_lift + z_critical * se

    # Post-hoc power
    effect_size = abs(absolute_lift) / np.sqrt(
        (control_rate * (1 - control_rate) + treatment_rate * (1 - treatment_rate)) / 2
    ) if (control_rate + treatment_rate) > 0 else 0
    power = _compute_power(effect_size, control_n + treatment_n, alpha)

    # Sample Ratio Mismatch check
    total = control_n + treatment_n
    expected_control = total * expected_split
    chi2, srm_p = stats.chisquare(
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
        is_significant=p_value < alpha,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        control_n=control_n,
        treatment_n=treatment_n,
        power=power,
        srm_p_value=srm_p,
        srm_flagged=srm_flagged,
    )


def _compute_power(effect_size: float, n: float, alpha: float) -> float:
    if effect_size == 0:
        return alpha
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = effect_size * np.sqrt(n / 2) - z_alpha
    return float(stats.norm.cdf(z_power))


def minimum_detectable_effect(n_per_variant: int, baseline_rate: float, alpha: float = 0.05, power: float = 0.8) -> float:
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    se = np.sqrt(2 * baseline_rate * (1 - baseline_rate) / n_per_variant)
    return (z_alpha + z_power) * se
