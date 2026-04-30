"""Sample Size Calculator — Streamlit page."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import numpy as np
from ab_test_interpreter.stats import sample_size_for_proportion, sample_size_for_continuous

st.set_page_config(
    page_title="Sample Size Calculator",
    page_icon="📐",
    layout="wide",
)

with st.sidebar:
    st.caption("Powered by Claude · [GitHub](https://github.com/vaishalizilpe/analytics-ai-toolkit)")

st.title("📐 Sample Size Calculator")
st.markdown(
    "Plan your A/B test before you run it. "
    "Enter your baseline and the smallest effect worth detecting — get the sample size you need."
)

metric_type = st.selectbox(
    "Metric type",
    ["Conversion rate (proportion)", "Continuous (revenue, duration, engagement)"],
    help="Proportion: binary yes/no events. Continuous: numeric values with a mean and standard deviation.",
)
is_proportion = metric_type == "Conversion rate (proportion)"

st.divider()

col_inputs, col_results = st.columns([1, 1], gap="large")

with col_inputs:
    st.subheader("Parameters")

    alpha = st.select_slider(
        "Significance level (α)",
        options=[0.01, 0.05, 0.10],
        value=0.05,
        format_func=lambda x: f"{x} ({int((1-x)*100)}% confidence)",
    )
    power = st.select_slider(
        "Power (1-β)",
        options=[0.70, 0.80, 0.90],
        value=0.80,
        format_func=lambda x: f"{x:.0%}",
    )

    st.markdown("---")

    if is_proportion:
        baseline_rate = st.number_input(
            "Baseline conversion rate (%)",
            min_value=0.01, max_value=99.99, value=3.20, step=0.01, format="%.2f",
        ) / 100

        mde_type = st.radio(
            "MDE expressed as",
            ["Relative % (e.g. 10% lift)", "Absolute percentage points"],
            horizontal=True,
        )

        if mde_type == "Relative % (e.g. 10% lift)":
            mde_relative = st.number_input(
                "Minimum detectable effect (relative %)",
                min_value=0.1, max_value=200.0, value=10.0, step=0.5, format="%.1f",
            ) / 100
            mde_absolute = baseline_rate * mde_relative
        else:
            mde_absolute = st.number_input(
                "Minimum detectable effect (percentage points)",
                min_value=0.01, max_value=50.0, value=0.32, step=0.01, format="%.2f",
            ) / 100
            mde_relative = mde_absolute / baseline_rate if baseline_rate > 0 else 0

        expected_rate = baseline_rate + mde_absolute

        st.info(
            f"Baseline: **{baseline_rate:.2%}** → Target: **{expected_rate:.2%}** "
            f"(+{mde_absolute:.2%} absolute, +{mde_relative:.1%} relative)"
        )

        daily_traffic = st.number_input(
            "Total daily users (optional — for duration estimate)",
            min_value=0, value=0, step=100,
            help="Leave at 0 to skip the duration estimate.",
        )

    else:
        baseline_mean = st.number_input(
            "Baseline mean",
            min_value=0.01, value=45.00, step=0.01, format="%.2f",
        )
        baseline_std = st.number_input(
            "Baseline std dev",
            min_value=0.01, value=12.00, step=0.01, format="%.2f",
            help="If unknown, a coefficient of variation of 20-30% of the mean is a common starting point.",
        )

        mde_type = st.radio(
            "MDE expressed as",
            ["Relative % of mean (e.g. 5% lift)", "Absolute units"],
            horizontal=True,
        )

        if mde_type == "Relative % of mean (e.g. 5% lift)":
            mde_relative = st.number_input(
                "Minimum detectable effect (relative %)",
                min_value=0.1, max_value=200.0, value=5.0, step=0.5, format="%.1f",
            ) / 100
            mde_absolute = baseline_mean * mde_relative
        else:
            mde_absolute = st.number_input(
                "Minimum detectable effect (absolute units)",
                min_value=0.01, value=2.25, step=0.01, format="%.2f",
            )
            mde_relative = mde_absolute / baseline_mean if baseline_mean > 0 else 0

        st.info(
            f"Baseline: **{baseline_mean:.2f}** → Target: **{baseline_mean + mde_absolute:.2f}** "
            f"(+{mde_absolute:.2f} absolute, +{mde_relative:.1%} relative) · "
            f"Effect size (Cohen's d): **{mde_absolute / baseline_std:.2f}**"
        )

        daily_traffic = st.number_input(
            "Total daily users (optional — for duration estimate)",
            min_value=0, value=0, step=100,
            help="Leave at 0 to skip the duration estimate.",
        )

with col_results:
    st.subheader("Required Sample Size")

    if is_proportion:
        if mde_absolute <= 0 or mde_absolute >= 1:
            st.error("MDE must be between 0 and 100%.")
            st.stop()
        n = sample_size_for_proportion(baseline_rate, mde_absolute, alpha=alpha, power=power)
    else:
        if mde_absolute <= 0:
            st.error("MDE must be greater than 0.")
            st.stop()
        n = sample_size_for_continuous(baseline_std, mde_absolute, alpha=alpha, power=power)

    total = n * 2

    r1, r2 = st.columns(2)
    r1.metric("Per variant", f"{n:,}")
    r2.metric("Total (both variants)", f"{total:,}")

    if daily_traffic > 0:
        days = total / daily_traffic
        st.metric("Estimated test duration", f"{days:.1f} days ({days/7:.1f} weeks)")
        if days < 7:
            st.warning("Less than one week. Consider running at least 7 days to account for weekly seasonality.")
        elif days > 56:
            st.warning("More than 8 weeks. Consider raising your MDE or accepting a higher p-value threshold.")

    st.divider()
    st.markdown("**Sensitivity: n per variant at different power levels**")

    power_levels = [0.70, 0.80, 0.90]
    rows = []
    for p in power_levels:
        if is_proportion:
            n_p = sample_size_for_proportion(baseline_rate, mde_absolute, alpha=alpha, power=p)
        else:
            n_p = sample_size_for_continuous(baseline_std, mde_absolute, alpha=alpha, power=p)
        rows.append({
            "Power": f"{p:.0%}",
            "n per variant": f"{n_p:,}",
            "Total n": f"{n_p * 2:,}",
        })

    st.table(rows)

    st.divider()
    st.markdown("**Sensitivity: n per variant at different MDE sizes**")

    mde_multipliers = [0.5, 1.0, 1.5, 2.0]
    mde_rows = []
    for mult in mde_multipliers:
        mde_adj = mde_absolute * mult
        if is_proportion:
            if 0 < mde_adj < 1:
                n_m = sample_size_for_proportion(baseline_rate, mde_adj, alpha=alpha, power=power)
            else:
                continue
        else:
            n_m = sample_size_for_continuous(baseline_std, mde_adj, alpha=alpha, power=power)

        rel = mde_adj / baseline_rate if is_proportion and baseline_rate > 0 else mde_adj / baseline_mean if not is_proportion and baseline_mean > 0 else 0
        mde_rows.append({
            "MDE (relative)": f"{rel:.1%}",
            "MDE (absolute)": f"{mde_adj:.4f}" if is_proportion else f"{mde_adj:.2f}",
            "n per variant": f"{n_m:,}",
            "Total n": f"{n_m * 2:,}",
        })

    st.table(mde_rows)

    st.caption(
        "No Claude API call on this page — sample size is pure math. "
        "Once you have your results, use the A/B Test Interpreter for AI-powered analysis."
    )
