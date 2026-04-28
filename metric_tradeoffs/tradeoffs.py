"""Claude-powered metric trade-off analysis."""
from shared.claude_client import ask_claude
from shared.prompts import METRIC_TRADEOFFS_SYSTEM_PROMPT, INTERVIEW_DRILL_SYSTEM_PROMPT

CHANGE_TYPES = [
    "Feature / UI change",
    "Algorithm / ranking change",
    "Pricing / threshold change",
    "Marketing / messaging change",
    "Infrastructure / performance change",
    "Policy / trust & safety change",
]

PRACTICE_PRODUCTS = [
    "Spotify",
    "Airbnb",
    "LinkedIn",
    "Duolingo",
    "Instacart",
    "DoorDash",
    "Slack",
    "Notion",
    "Apple Maps",
    "Apple Pay",
]


def analyze_tradeoffs(
    primary_metric: str,
    change_type: str,
    change_description: str,
    product_context: str,
    business_goal: str,
    secondary_metrics: str,
) -> str:
    user_message = f"""
Primary metric being optimized: {primary_metric}
Type of change: {change_type}
What the change does: {change_description}
Product / platform context: {product_context}
Business goal: {business_goal}
Other metrics currently tracked: {secondary_metrics if secondary_metrics.strip() else "not specified"}

Analyze the metric trade-offs using these exact sections:

## METRIC HIERARCHY
Map the full hierarchy for this product/context:
- North Star Metric (one number that captures core product value)
- Primary Metrics (direct drivers of north star)
- Secondary / Input Metrics (levers teams control)
- Guardrail Metrics (must not break)
- Diagnostic Metrics (for investigation only, not optimization targets)

## TRADE-OFF SURFACE
For this specific change (optimizing {primary_metric} via {change_type}):
**Metrics that likely improve:** list with reasoning
**Metrics at risk of degrading:** list with reasoning
**Unknown / needs measurement:** what you would add to the experiment to find out

## ACCEPTABLE vs. UNACCEPTABLE TRADE-OFFS
Given the stated business goal, which trade-offs are worth accepting and which are not? Be specific about thresholds.

## GUARDRAIL RECOMMENDATIONS
Which specific metrics should be guardrails for this change? What degradation threshold would trigger a rollback?

## COMPOSITE METRIC SUGGESTION
Propose one composite metric or score that captures the right balance for this optimization. Include its formula.

## RECOMMENDATION
Ship / Don't Ship / Modify — with explicit assumptions stated. One clear paragraph.
"""
    return ask_claude(METRIC_TRADEOFFS_SYSTEM_PROMPT, user_message, max_tokens=2000)


def generate_drill_answer(product: str) -> str:
    user_message = f"""
Product: {product}

Generate a Staff Data Scientist-level model answer for this interview exercise:

1. What does success look like for {product}? (1 sentence)
2. What is the North Star Metric? (name it and justify it in 1 sentence)
3. What are 3 input metrics that drive the North Star? (name each and explain the mechanism)
4. What are 2 guardrail metrics? (name each and explain what breaking them would signal)
5. The North Star dropped 5% last week with no known product changes. What are your first 3 hypotheses? (be specific — name the segment, mechanism, or data issue you'd look at first)

Format each answer clearly under the numbered question. Be specific to {product}'s actual business model — no generic answers.
"""
    return ask_claude(INTERVIEW_DRILL_SYSTEM_PROMPT, user_message, max_tokens=1500)
