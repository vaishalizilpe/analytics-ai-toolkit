"""Claude-powered interpretation of A/B test results."""
import json
from ab_test_interpreter.stats import ABTestResult
from shared.claude_client import ask_claude
from shared.prompts import AB_TEST_SYSTEM_PROMPT


def interpret_results(result: ABTestResult, metric_name: str, experiment_context: str) -> str:
    user_message = f"""
Experiment context: {experiment_context}
Metric: {metric_name}

Results:
- Control: {result.control_rate:.4f} ({result.control_n:,} users, {int(result.control_rate * result.control_n):,} conversions)
- Treatment: {result.treatment_rate:.4f} ({result.treatment_n:,} users, {int(result.treatment_rate * result.treatment_n):,} conversions)
- Relative lift: {result.relative_lift:+.2%}
- Absolute lift: {result.absolute_lift:+.4f}
- 95% CI on absolute lift: [{result.ci_lower:+.4f}, {result.ci_upper:+.4f}]
- p-value: {result.p_value:.4f}
- Statistically significant (α=0.05): {result.is_significant}
- Post-hoc power: {result.power:.2%}
- Sample Ratio Mismatch detected: {result.srm_flagged} (SRM p-value: {result.srm_p_value:.4f})

Interpret these results. If SRM is flagged, lead with that warning.
End with a clear RECOMMENDATION section: Ship / Don't Ship / Extend Test — and why.
Also include a FOLLOW-UP section: what to investigate next (segments, guardrail metrics, duration concerns).
"""
    return ask_claude(AB_TEST_SYSTEM_PROMPT, user_message, max_tokens=1500)


def build_handoff_context(result: ABTestResult, metric_name: str, experiment_context: str) -> dict:
    """Returns structured context for handing off to RCA or Metric Trade-offs tools."""
    return {
        "source": "ab_test_interpreter",
        "experiment_context": experiment_context,
        "metric": metric_name,
        "lift": result.relative_lift,
        "significant": result.is_significant,
        "p_value": result.p_value,
        "control_rate": result.control_rate,
        "treatment_rate": result.treatment_rate,
    }
