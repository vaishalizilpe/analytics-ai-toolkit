"""Plotly charts for the A/B Test Interpreter."""
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from scipy import stats as scipy_stats
from ab_test_interpreter.stats import ABTestResult


def confidence_interval_plot(result: ABTestResult, metric_name: str) -> go.Figure:
    fig = go.Figure()

    # Zero line
    fig.add_vline(x=0, line_dash="dash", line_color="gray", annotation_text="No effect")

    color = "#2ecc71" if result.is_significant and result.absolute_lift > 0 else (
        "#e74c3c" if result.is_significant else "#95a5a6"
    )

    fig.add_trace(go.Scatter(
        x=[result.ci_lower, result.absolute_lift, result.ci_upper],
        y=["Absolute lift", "Absolute lift", "Absolute lift"],
        mode="lines+markers",
        line=dict(color=color, width=6),
        marker=dict(
            color=[color, color, color],
            size=[8, 14, 8],
            symbol=["line-ns", "diamond", "line-ns"],
        ),
        name="95% CI",
    ))

    title_suffix = "SIGNIFICANT" if result.is_significant else "NOT SIGNIFICANT"
    fig.update_layout(
        title=f"{metric_name} — 95% Confidence Interval ({title_suffix})",
        xaxis_title="Absolute lift",
        height=200,
        showlegend=False,
        plot_bgcolor="white",
        xaxis=dict(zeroline=False, gridcolor="#f0f0f0"),
    )
    return fig


def conversion_rate_bar(result: ABTestResult, metric_name: str) -> go.Figure:
    fig = go.Figure(data=[
        go.Bar(
            name=metric_name,
            x=["Control", "Treatment"],
            y=[result.control_rate, result.treatment_rate],
            marker_color=["#3498db", "#2ecc71" if result.absolute_lift >= 0 else "#e74c3c"],
            text=[f"{result.control_rate:.3%}", f"{result.treatment_rate:.3%}"],
            textposition="outside",
        )
    ])
    fig.update_layout(
        title=f"{metric_name}: Control vs Treatment",
        yaxis_title="Rate",
        yaxis_tickformat=".2%",
        height=350,
        plot_bgcolor="white",
        showlegend=False,
    )
    return fig


def power_gauge(power: float) -> go.Figure:
    color = "#2ecc71" if power >= 0.8 else ("#f39c12" if power >= 0.6 else "#e74c3c")
    # Post-hoc power is shown for reference only — it is mathematically linked to p-value
    # and should not substitute for pre-registered power analysis.
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=power * 100,
        title={"text": "Post-hoc Power (%)*"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 60], "color": "#fadbd8"},
                {"range": [60, 80], "color": "#fdebd0"},
                {"range": [80, 100], "color": "#d5f5e3"},
            ],
            "threshold": {"line": {"color": "black", "width": 2}, "value": 80},
        },
        number={"suffix": "%", "valueformat": ".1f"},
    ))
    fig.update_layout(height=250)
    return fig
