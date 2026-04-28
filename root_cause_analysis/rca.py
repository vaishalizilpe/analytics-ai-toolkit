"""Claude-powered root cause analysis logic."""
from shared.claude_client import ask_claude
from shared.prompts import RCA_SYSTEM_PROMPT

DIAGNOSTIC_QUERIES = {
    "Data Quality / Pipeline": [
        {
            "name": "Event volume by day",
            "description": "Spot logging drops or spikes immediately",
            "sql": """SELECT
    DATE(event_timestamp) AS day,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_id) AS unique_users
FROM events
WHERE event_name = '<your_event>'
  AND DATE(event_timestamp) BETWEEN '<start_date>' AND '<end_date>'
GROUP BY 1
ORDER BY 1""",
        },
        {
            "name": "Null / missing value rate",
            "description": "Check for schema changes or upstream data quality regression",
            "sql": """SELECT
    DATE(created_at) AS day,
    COUNT(*) AS total_rows,
    COUNTIF(<key_field> IS NULL) AS null_count,
    ROUND(COUNTIF(<key_field> IS NULL) / COUNT(*), 4) AS null_rate
FROM <table>
WHERE DATE(created_at) BETWEEN '<start_date>' AND '<end_date>'
GROUP BY 1
ORDER BY 1""",
        },
    ],
    "User Segment Shifts": [
        {
            "name": "Metric by new vs. returning users",
            "description": "Determine if cohort mix shifted and is driving the aggregate change",
            "sql": """SELECT
    DATE(event_date) AS day,
    CASE WHEN user_age_days < 7 THEN 'new' ELSE 'returning' END AS user_type,
    COUNT(DISTINCT user_id) AS users,
    COUNT(DISTINCT CASE WHEN converted THEN user_id END) AS converters,
    ROUND(COUNT(DISTINCT CASE WHEN converted THEN user_id END)
          / NULLIF(COUNT(DISTINCT user_id), 0), 4) AS rate
FROM user_events
WHERE DATE(event_date) BETWEEN '<start_date>' AND '<end_date>'
GROUP BY 1, 2
ORDER BY 1, 2""",
        },
        {
            "name": "Metric by platform",
            "description": "Check if device mix (iOS / Android / Web) shifted",
            "sql": """SELECT
    DATE(event_date) AS day,
    platform,
    COUNT(DISTINCT user_id) AS users,
    COUNT(DISTINCT CASE WHEN converted THEN user_id END) AS converters,
    ROUND(COUNT(DISTINCT CASE WHEN converted THEN user_id END)
          / NULLIF(COUNT(DISTINCT user_id), 0), 4) AS rate
FROM user_events
WHERE DATE(event_date) BETWEEN '<start_date>' AND '<end_date>'
GROUP BY 1, 2
ORDER BY 1, 2""",
        },
    ],
    "Product / Feature Changes": [
        {
            "name": "Before / after deploy comparison",
            "description": "Compare metric on either side of a deployment timestamp",
            "sql": """SELECT
    CASE
        WHEN event_timestamp < TIMESTAMP('<deploy_time>') THEN 'pre_deploy'
        ELSE 'post_deploy'
    END AS period,
    COUNT(DISTINCT user_id) AS users,
    COUNT(DISTINCT CASE WHEN converted THEN user_id END) AS converters,
    ROUND(COUNT(DISTINCT CASE WHEN converted THEN user_id END)
          / NULLIF(COUNT(DISTINCT user_id), 0), 4) AS rate
FROM user_events
WHERE DATE(event_timestamp) BETWEEN '<start_date>' AND '<end_date>'
GROUP BY 1""",
        },
    ],
}


def analyze_metric_movement(
    metric_name: str,
    movement_direction: str,
    magnitude: str,
    time_period: str,
    product_context: str,
    known_events: str,
    affected_segments: list[str],
) -> str:
    user_message = f"""
Metric: {metric_name}
Movement: {movement_direction} — {magnitude}
Time period: {time_period}
Product / platform context: {product_context}
Known events around this time: {known_events if known_events.strip() else "None specified"}
Affected segments so far: {', '.join(affected_segments) if affected_segments else "not yet investigated"}

Perform a structured root cause analysis using these exact sections:

## IMMEDIATE TRIAGE
Is this likely a data quality issue or a real metric shift? What is the single first thing to check and why?

## HYPOTHESIS MATRIX
For each of the five categories below, list 2-3 specific hypotheses. For each hypothesis include:
- Likelihood: High / Medium / Low
- Ease to check: High / Medium / Low
- Specific data cut or query to confirm or rule out

Categories: Data Quality / Pipeline | Product / Feature Changes | External / Seasonality | User Segment Shifts | Marketing / Business Changes

## TOP 3 PRIORITIES
Rank by (likelihood x ease). For each: one concrete next step, stated as an action.

## RED FLAGS
Any signals in the description that point to an urgent or high-severity root cause. Skip this section if none.
"""
    return ask_claude(RCA_SYSTEM_PROMPT, user_message, max_tokens=2000)
