"""Claude-powered interpretation of A/B test results."""
import json
from typing import Union
from ab_test_interpreter.stats import ABTestResult, ContinuousTestResult
from shared.claude_client import ask_claude
from shared.prompts import AB_TEST_SYSTEM_PROMPT


def interpret_results(
    result: ABTestResult,
    metric_name: str,
    experiment_context: str,
    min_practical_effect: float = 0.0,
    n_metrics: int = 1,
    corrected_alpha: float = 0.05,
) -> str:
    rel_lift_ci = (
        f"[{result.relative_lift_ci_lower:+.2%}, {result.relative_lift_ci_upper:+.2%}]"
        if result.relative_lift_ci_lower is not None
        else "undefined (0% control rate)"
    )
    prac_sig_note = (
        f"Minimum practical significance threshold: {min_practical_effect:.4f} absolute. "
        f"Observed lift {'meets' if result.absolute_lift >= min_practical_effect else 'does NOT meet'} this threshold."
        if min_practical_effect > 0 else "No practical significance threshold set."
    )
    multi_test_note = (
        f"Bonferroni-corrected significance threshold (across {n_metrics} metrics): α={corrected_alpha:.4f}. "
        f"p-value {'passes' if result.p_value < corrected_alpha else 'does NOT pass'} the corrected threshold."
        if n_metrics > 1 else "Single metric test — no multiple testing correction applied."
    )
    test_method = "Fisher's exact test (normal approximation invalid — low count cells)" if result.fisher_used else "Two-proportion z-test"

    user_message = f"""
Experiment context: {experiment_context}
Metric: {metric_name}

Results:
- Control: {result.control_rate:.4f} ({result.control_n:,} users, {result.control_conversions:,} conversions)
- Treatment: {result.treatment_rate:.4f} ({result.treatment_n:,} users, {result.treatment_conversions:,} conversions)
- Relative lift: {f"{result.relative_lift:+.2%}" if result.relative_lift is not None else "undefined (0% control rate)"}
- 95% CI on relative lift (delta method): {rel_lift_ci}
- Absolute lift: {result.absolute_lift:+.4f}
- 95% CI on absolute lift: [{result.ci_lower:+.4f}, {result.ci_upper:+.4f}]
- Test method: {test_method}
- p-value: {result.p_value:.4f}
- Statistically significant (α=0.05): {result.is_significant}
- {multi_test_note}
- {prac_sig_note}
- Sample Ratio Mismatch detected: {result.srm_flagged} (SRM p-value: {result.srm_p_value:.4f})

Interpret these results. If SRM is flagged, lead with that warning.
If the lift is statistically significant but does not meet the practical significance threshold, say so explicitly in the recommendation.
End with a clear RECOMMENDATION section: Ship / Don't Ship / Extend Test — and why.
Also include a FOLLOW-UP section: what to investigate next (segments, guardrail metrics, duration concerns).
"""
    return ask_claude(AB_TEST_SYSTEM_PROMPT, user_message, max_tokens=1500)


def interpret_continuous_results(result: ContinuousTestResult, metric_name: str, experiment_context: str) -> str:
    user_message = f"""
Experiment context: {experiment_context}
Metric: {metric_name} (continuous — mean comparison, Welch's t-test)

Results:
- Control: mean={result.control_mean:.4f}, std={result.control_std:.4f}, n={result.control_n:,}
- Treatment: mean={result.treatment_mean:.4f}, std={result.treatment_std:.4f}, n={result.treatment_n:,}
- Relative lift: {f"{result.relative_lift:+.2%}" if result.relative_lift is not None else "undefined (0 control mean)"}
- Absolute lift: {result.absolute_lift:+.4f}
- 95% CI on absolute lift: [{result.ci_lower:+.4f}, {result.ci_upper:+.4f}]
- t-statistic: {result.t_stat:.4f} (df={result.df:.1f})
- p-value: {result.p_value:.4f}
- Statistically significant (α=0.05): {result.is_significant}
- Post-hoc power: {result.power:.2%}
- Sample Ratio Mismatch detected: {result.srm_flagged} (SRM p-value: {result.srm_p_value:.4f})

Interpret these results. If SRM is flagged, lead with that warning.
End with a clear RECOMMENDATION section: Ship / Don't Ship / Extend Test — and why.
Also include a FOLLOW-UP section: what to investigate next (segments, guardrail metrics, duration concerns).
"""
    return ask_claude(AB_TEST_SYSTEM_PROMPT, user_message, max_tokens=1500)


def build_handoff_context(result: Union[ABTestResult, ContinuousTestResult], metric_name: str, experiment_context: str) -> dict:
    if isinstance(result, ABTestResult):
        primary_key, secondary_key = "control_rate", "treatment_rate"
        primary_val, secondary_val = result.control_rate, result.treatment_rate
    else:
        primary_key, secondary_key = "control_mean", "treatment_mean"
        primary_val, secondary_val = result.control_mean, result.treatment_mean

    return {
        "source": "ab_test_interpreter",
        "experiment_context": experiment_context,
        "metric": metric_name,
        "lift": result.relative_lift,
        "significant": result.is_significant,
        "p_value": result.p_value,
        primary_key: primary_val,
        secondary_key: secondary_val,
    }
