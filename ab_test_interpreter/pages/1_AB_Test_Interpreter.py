"""A/B Test Interpreter — Streamlit page."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
import json
from ab_test_interpreter.stats import run_proportion_test, minimum_detectable_effect
from ab_test_interpreter.interpreter import interpret_results, build_handoff_context
from ab_test_interpreter.visualizations import confidence_interval_plot, conversion_rate_bar, power_gauge
from shared.constants import MIN_SAMPLE_SIZE
from shared.ui import inject_css, render_sidebar, hero

st.set_page_config(page_title="A/B Test Interpreter", page_icon="🧪", layout="wide")
inject_css()
render_sidebar("A/B Test Interpreter")

hero(
    "🧪",
    "A/B Test Interpreter",
    "Enter your experiment results. Get statistical analysis + AI-powered interpretation "
    "with a clear ship / don't-ship recommendation.",
)

with st.form("ab_test_form"):
    st.subheader("Experiment Setup")
    experiment_context = st.text_area(
        "Describe the experiment",
        placeholder="e.g. We redesigned the checkout button from gray to green on the iOS app. "
                    "Launched to 50% of users for 14 days. Primary metric: purchase conversion rate.",
        height=100,
    )
    metric_name = st.text_input("Primary metric name", placeholder="e.g. Purchase conversion rate")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Control group**")
        control_n    = st.number_input("Users",       min_value=1, value=10000, step=100, key="cn")
        control_conv = st.number_input("Conversions", min_value=0, value=320,   step=10,  key="cc")
    with col2:
        st.markdown("**Treatment group**")
        treatment_n    = st.number_input("Users",       min_value=1, value=10200, step=100, key="tn")
        treatment_conv = st.number_input("Conversions", min_value=0, value=374,   step=10,  key="tc")

    expected_split = st.slider(
        "Expected traffic split (control %)", min_value=10, max_value=90, value=50, step=5
    ) / 100
    submitted = st.form_submit_button("Analyze", type="primary", use_container_width=True)

if submitted:
    if not experiment_context.strip():
        st.warning("Please describe the experiment so Claude can provide meaningful context.")
        st.stop()
    if not metric_name.strip():
        st.warning("Please enter a metric name.")
        st.stop()
    if int(control_conv) > int(control_n):
        st.error("Control conversions cannot exceed control users.")
        st.stop()
    if int(treatment_conv) > int(treatment_n):
        st.error("Treatment conversions cannot exceed treatment users.")
        st.stop()
    if int(control_n) < MIN_SAMPLE_SIZE or int(treatment_n) < MIN_SAMPLE_SIZE:
        st.warning(f"Sample size below minimum ({MIN_SAMPLE_SIZE:,} users). Results may not be reliable.")

    with st.spinner("Running statistical tests..."):
        result = run_proportion_test(
            control_conversions=int(control_conv),
            control_n=int(control_n),
            treatment_conversions=int(treatment_conv),
            treatment_n=int(treatment_n),
            expected_split=expected_split,
        )

    if result.srm_flagged:
        st.error(
            f"⚠️ **Sample Ratio Mismatch detected** (SRM p-value: {result.srm_p_value:.4f}). "
            "The traffic split differs significantly from expected. "
            "Do not draw conclusions from this test until you identify the root cause."
        )

    st.subheader("Results at a Glance")
    m1, m2, m3, m4 = st.columns(4)
    lift_display = f"{result.relative_lift:+.2%}" if result.relative_lift is not None else "undefined"
    lift_delta   = (f"{'↑' if (result.relative_lift or 0) > 0 else '↓'} vs control"
                    if result.relative_lift is not None else "0% control rate")
    m1.metric("Relative Lift",   lift_display, delta=lift_delta)
    m2.metric("p-value",         f"{result.p_value:.4f}", delta="sig." if result.is_significant else "not sig.")
    m3.metric("Control rate",    f"{result.control_rate:.3%}")
    m4.metric("Treatment rate",  f"{result.treatment_rate:.3%}")

    sig_badge = "✅ Statistically significant" if result.is_significant else "❌ Not statistically significant"
    st.info(sig_badge + f" at α=0.05 · 95% CI: [{result.ci_lower:+.4f}, {result.ci_upper:+.4f}]")

    col_c1, col_c2, col_c3 = st.columns([2, 1.5, 1])
    with col_c1:
        st.plotly_chart(confidence_interval_plot(result, metric_name), use_container_width=True)
    with col_c2:
        st.plotly_chart(conversion_rate_bar(result, metric_name), use_container_width=True)
    with col_c3:
        st.plotly_chart(power_gauge(result.power), use_container_width=True)
        st.caption("*Post-hoc power is for reference only.")

    mde = minimum_detectable_effect(
        n_per_variant=min(int(control_n), int(treatment_n)),
        baseline_rate=result.control_rate,
    )
    mde_relative = f" ({mde/result.control_rate:.2%} relative)" if result.control_rate > 0 else ""
    st.caption(f"MDE at 80% power: ±{mde:.4f} absolute{mde_relative}")

    st.subheader("AI Interpretation")
    with st.spinner("Claude is analyzing your results..."):
        try:
            interpretation = interpret_results(result, metric_name, experiment_context)
            st.markdown(interpretation)
        except EnvironmentError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Claude API error: {e}")
            st.stop()

    st.subheader("Continue Your Analysis")
    handoff = build_handoff_context(result, metric_name, experiment_context)
    hcol1, hcol2 = st.columns(2)
    with hcol1:
        if not result.is_significant or (result.relative_lift is not None and result.relative_lift < 0):
            st.markdown("**Metric didn't move as expected?**")
            st.page_link("pages/2_Root_Cause_Analysis.py", label="🔍 Diagnose with Root Cause Analysis →")
    with hcol2:
        if result.is_significant:
            st.markdown("**Before you ship — check the second-order effects.**")
            st.page_link("pages/3_Metric_Tradeoffs.py", label="⚖️ Analyze with Metric Trade-offs →")

    with st.expander("Export experiment context (for RCA / Trade-offs tools)"):
        st.code(json.dumps(handoff, indent=2), language="json")
        st.caption("Copy this JSON to pre-load context into other tools in the suite.")
