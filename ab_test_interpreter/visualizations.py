"""Plotly charts for the A/B Test Interpreter."""
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from scipy import stats as scipy_stats
from ab_test_interpreter.stats import ABTestResult, ContinuousTestResult


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


def mean_bar_chart(result: ContinuousTestResult, metric_name: str) -> go.Figure:
    color_treatment = "#2ecc71" if result.absolute_lift >= 0 else "#e74c3c"
    fig = go.Figure(data=[
        go.Bar(
            x=["Control", "Treatment"],
            y=[result.control_mean, result.treatment_mean],
            marker_color=["#3498db", color_treatment],
            error_y=dict(
                type="data",
                array=[result.control_std, result.treatment_std],
                visible=True,
                color="gray",
                thickness=1.5,
            ),
            text=[f"{result.control_mean:.3f}", f"{result.treatment_mean:.3f}"],
            textposition="outside",
        )
    ])
    fig.update_layout(
        title=f"{metric_name}: Control vs Treatment (mean ± std)",
        yaxis_title="Mean",
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


def power_curve(effect_size: float, alpha: float, recommended_n: int, target_power: float = 0.80) -> go.Figure:
    """Power vs n per variant. effect_size is Cohen's d (mde / pooled_std)."""
    n_min = max(20, recommended_n // 8)
    n_max = recommended_n * 4
    n_range = np.linspace(n_min, n_max, 400).astype(int)
    z_alpha = scipy_stats.norm.ppf(1 - alpha / 2)
    powers = [float(scipy_stats.norm.cdf(effect_size * np.sqrt(n) - z_alpha)) for n in n_range]

    fig = go.Figure()
    fig.add_hline(y=target_power, line_dash="dash", line_color="#e74c3c", line_width=1,
                  annotation_text=f"{target_power:.0%} power", annotation_position="right")
    fig.add_vline(x=recommended_n, line_dash="dot", line_color="#27ae60", line_width=1.5,
                  annotation_text=f"n={recommended_n:,}", annotation_position="top right")
    fig.add_trace(go.Scatter(x=n_range, y=powers, mode="lines",
                             line=dict(color="#3498db", width=2.5), showlegend=False))
    fig.add_trace(go.Scatter(x=[recommended_n], y=[target_power], mode="markers",
                             marker=dict(size=10, color="#27ae60", line=dict(color="white", width=2)),
                             showlegend=False))
    fig.update_layout(
        title="Power vs Sample Size",
        xaxis_title="n per variant",
        yaxis_title="Statistical power",
        yaxis=dict(range=[0, 1.05], tickformat=".0%", gridcolor="#f0f0f0"),
        xaxis=dict(gridcolor="#f0f0f0"),
        height=300, plot_bgcolor="white", showlegend=False,
        margin=dict(t=50, r=100),
    )
    return fig


def mde_curve(baseline_rate: float, alpha: float, power: float, recommended_n: int) -> go.Figure:
    """Detectable relative lift % vs n per variant for a proportion metric (equal split assumed)."""
    n_min = max(100, recommended_n // 8)
    n_max = recommended_n * 4
    n_range = np.linspace(n_min, n_max, 400).astype(int)
    z_alpha = scipy_stats.norm.ppf(1 - alpha / 2)
    z_power = scipy_stats.norm.ppf(power)
    # Equal split: 1/n_control + 1/n_treatment = 2/n_per_variant
    mdes_rel = (z_alpha + z_power) * np.sqrt(baseline_rate * (1 - baseline_rate) * 2 / n_range) / baseline_rate * 100
    current_mde_rel = (z_alpha + z_power) * np.sqrt(baseline_rate * (1 - baseline_rate) * 2 / recommended_n) / baseline_rate * 100

    fig = go.Figure()
    fig.add_vline(x=recommended_n, line_dash="dot", line_color="#27ae60", line_width=1.5,
                  annotation_text=f"n={recommended_n:,}", annotation_position="top right")
    fig.add_trace(go.Scatter(x=n_range, y=mdes_rel, mode="lines",
                             line=dict(color="#9b59b6", width=2.5), showlegend=False))
    fig.add_trace(go.Scatter(x=[recommended_n], y=[current_mde_rel], mode="markers",
                             marker=dict(size=10, color="#27ae60", line=dict(color="white", width=2)),
                             showlegend=False))
    fig.update_layout(
        title="Detectable Lift vs Sample Size",
        xaxis_title="n per variant",
        yaxis_title="Min detectable lift (%)",
        yaxis=dict(gridcolor="#f0f0f0"),
        xaxis=dict(gridcolor="#f0f0f0"),
        height=300, plot_bgcolor="white", showlegend=False,
        margin=dict(t=50, r=100),
    )
    return fig
