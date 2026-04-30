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


def null_distribution_chart(p_value: float, absolute_lift: float, alpha: float) -> go.Figure:
    """Standard normal null distribution with rejection regions and observed z-statistic."""
    z_stat = float(scipy_stats.norm.ppf(1 - p_value / 2)) * (1 if absolute_lift >= 0 else -1)
    z_alpha = float(scipy_stats.norm.ppf(1 - alpha / 2))
    is_sig = abs(z_stat) > z_alpha

    x = np.linspace(-4.5, 4.5, 600)
    y = scipy_stats.norm.pdf(x)

    x_left = x[x <= -z_alpha]
    x_right = x[x >= z_alpha]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color="#bdc3c7", width=2), showlegend=False))

    for x_tail in [x_left, x_right]:
        y_tail = scipy_stats.norm.pdf(x_tail)
        fig.add_trace(go.Scatter(
            x=np.concatenate([x_tail, x_tail[::-1]]),
            y=np.concatenate([y_tail, np.zeros_like(y_tail)]),
            fill="toself", fillcolor="rgba(231, 76, 60, 0.20)",
            line=dict(width=0), showlegend=False,
        ))

    stat_color = "#e74c3c" if is_sig else "#7f8c8d"
    fig.add_vline(x=z_stat, line_color=stat_color, line_width=2.5,
                  annotation_text=f"z = {z_stat:.2f}", annotation_position="top right")
    fig.add_vline(x=z_alpha, line_dash="dot", line_color="#e74c3c", line_width=1,
                  annotation_text=f"±{z_alpha:.2f}", annotation_position="top left")
    fig.add_vline(x=-z_alpha, line_dash="dot", line_color="#e74c3c", line_width=1)

    verdict = "significant" if is_sig else "not significant"
    fig.update_layout(
        title=f"Null Distribution — p = {p_value:.4f} ({verdict} at α = {alpha})",
        xaxis_title="Test statistic (z)",
        yaxis=dict(visible=False),
        xaxis=dict(gridcolor="#f0f0f0", zeroline=False),
        height=260, plot_bgcolor="white", showlegend=False,
        margin=dict(t=50, b=40, r=80),
    )
    return fig


def lift_vs_mde_chart(
    absolute_lift: float, ci_lower: float, ci_upper: float, mde: float
) -> go.Figure:
    """Number line showing observed lift + CI versus the ±MDE threshold."""
    adequately_powered = abs(absolute_lift) >= mde
    lift_color = "#27ae60" if absolute_lift > 0 else "#e74c3c"
    mde_color = "#27ae60" if adequately_powered else "#e74c3c"

    fig = go.Figure()

    # CI band
    fig.add_trace(go.Scatter(
        x=[ci_lower, ci_upper], y=[0, 0],
        mode="lines", line=dict(color=lift_color, width=10),
        name="95% CI", showlegend=True,
    ))
    fig.add_trace(go.Scatter(
        x=[ci_lower, ci_upper], y=[0, 0], mode="markers",
        marker=dict(color=lift_color, size=12, symbol="line-ns-open",
                    line=dict(color=lift_color, width=3)),
        showlegend=False,
    ))
    # Observed lift diamond
    fig.add_trace(go.Scatter(
        x=[absolute_lift], y=[0], mode="markers",
        marker=dict(color="white", size=14, symbol="diamond",
                    line=dict(color=lift_color, width=3)),
        name="Observed lift", showlegend=True,
    ))

    # Reference lines
    fig.add_vline(x=0, line_dash="dash", line_color="#95a5a6", line_width=1,
                  annotation_text="0", annotation_position="bottom")
    fig.add_vline(x=mde, line_dash="dot", line_color=mde_color, line_width=1.5,
                  annotation_text=f"+MDE\n{mde:.4f}", annotation_position="top right")
    fig.add_vline(x=-mde, line_dash="dot", line_color=mde_color, line_width=1.5,
                  annotation_text=f"−MDE", annotation_position="top left")

    adequacy_label = "Adequately powered" if adequately_powered else "Underpowered"
    fig.update_layout(
        title=f"Observed Lift vs MDE — {adequacy_label}",
        xaxis_title="Absolute lift",
        yaxis=dict(visible=False, range=[-1, 1]),
        xaxis=dict(gridcolor="#f0f0f0", zeroline=False),
        height=220, plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0),
        margin=dict(t=60, b=40, r=100),
    )
    return fig


def beta_posterior_chart(
    control_conv: int, control_n: int,
    treatment_conv: int, treatment_n: int,
    prob_treatment_wins: float,
) -> go.Figure:
    """Overlapping Beta posterior distributions for control and treatment."""
    a_c, b_c = control_conv + 1, control_n - control_conv + 1
    a_t, b_t = treatment_conv + 1, treatment_n - treatment_conv + 1

    mean_c = a_c / (a_c + b_c)
    mean_t = a_t / (a_t + b_t)
    std_c = np.sqrt(a_c * b_c / ((a_c + b_c) ** 2 * (a_c + b_c + 1)))
    std_t = np.sqrt(a_t * b_t / ((a_t + b_t) ** 2 * (a_t + b_t + 1)))
    spread = 4 * max(std_c, std_t)
    x_min = max(0.0, min(mean_c, mean_t) - spread)
    x_max = min(1.0, max(mean_c, mean_t) + spread)
    x = np.linspace(x_min, x_max, 500)

    pdf_c = scipy_stats.beta.pdf(x, a_c, b_c)
    pdf_t = scipy_stats.beta.pdf(x, a_t, b_t)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=pdf_c, mode="lines", fill="tozeroy",
        line=dict(color="#3498db", width=2),
        fillcolor="rgba(52, 152, 219, 0.20)",
        name="Control",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=pdf_t, mode="lines", fill="tozeroy",
        line=dict(color="#27ae60", width=2),
        fillcolor="rgba(39, 174, 96, 0.20)",
        name="Treatment",
    ))
    fig.add_vline(x=mean_c, line_dash="dot", line_color="#3498db", line_width=1,
                  annotation_text=f"{mean_c:.3%}", annotation_position="top left")
    fig.add_vline(x=mean_t, line_dash="dot", line_color="#27ae60", line_width=1,
                  annotation_text=f"{mean_t:.3%}", annotation_position="top right")

    fig.update_layout(
        title=f"Posterior Distributions — P(Treatment wins) = {prob_treatment_wins:.1%}",
        xaxis_title="Conversion rate",
        xaxis=dict(tickformat=".2%", gridcolor="#f0f0f0"),
        yaxis=dict(visible=False),
        height=320, plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60),
    )
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
