"""A/B Test Interpreter — Streamlit app."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import json
from ab_test_interpreter.stats import run_proportion_test, minimum_detectable_effect
from ab_test_interpreter.interpreter import interpret_results, build_handoff_context
from ab_test_interpreter.visualizations import confidence_interval_plot, conversion_rate_bar, power_gauge

st.set_page_config(
    page_title="A/B Test Interpreter",
    page_icon="🧪",
    layout="wide",
)

# ── Sidebar: suite navigation ──────────────────────────────────────────────
with st.sidebar:
    st.title("Analytics AI Toolkit")
    st.markdown("---")
    st.markdown("**Tools**")
    st.markdown("🧪 **A/B Test Interpreter** ← you are here")
    st.markdown("🔍 Root Cause Analysis *(coming soon)*")
    st.markdown("⚖️ Metric Trade-offs *(coming soon)*")
    st.markdown("---")
    st.caption("Powered by Claude · [GitHub](https://github.com/vaishalizilpe/analytics-ai-toolkit)")

# ── Header ─────────────────────────────────────────────────────────────────
st.title("🧪 A/B Test Interpreter")
st.markdown(
    "Enter your experiment results. Get statistical analysis + AI-powered interpretation "
    "with a clear ship/don't-ship recommendation."
)

# ── Input form ─────────────────────────────────────────────────────────────
with st.form("ab_test_form"):
    st.subheader("Experiment Setup")

    experiment_context = st.text_area(
        "Describe the experiment",
        placeholder="e.g. We redesigned the checkout button from gray to green on the iOS app. "
                    "Launched to 50% of users for 14 days. Primary metric: purchase conversion rate.",
        height=100,
    )
    metric_name = st.text_input("Primary metric name", value="Purchase conversion rate")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Control group**")
        control_n = st.number_input("Users", min_value=1, value=10000, step=100, key="cn")
        control_conv = st.number_input("Conversions", min_value=0, value=320, step=10, key="cc")
    with col2:
        st.markdown("**Treatment group**")
        treatment_n = st.number_input("Users", min_value=1, value=10200, step=100, key="tn")
        treatment_conv = st.number_input("Conversions", min_value=0, value=374, step=10, key="tc")

    expected_split = st.slider(
        "Expected traffic split (control %)", min_value=10, max_value=90, value=50, step=5
    ) / 100

    submitted = st.form_submit_button("Analyze", type="primary", use_container_width=True)

# ── Results ────────────────────────────────────────────────────────────────
if submitted:
    if not experiment_context.strip():
        st.warning("Please describe the experiment so Claude can provide meaningful context.")
        st.stop()

    with st.spinner("Running statistical tests..."):
        result = run_proportion_test(
            control_conversions=int(control_conv),
            control_n=int(control_n),
            treatment_conversions=int(treatment_conv),
            treatment_n=int(treatment_n),
            expected_split=expected_split,
        )

    # ── SRM warning (shown before everything else) ──────────────────────
    if result.srm_flagged:
        st.error(
            f"⚠️ **Sample Ratio Mismatch detected** (SRM p-value: {result.srm_p_value:.4f}). "
            "The traffic split differs significantly from expected. "
            "Do not draw conclusions from this test until you identify the root cause "
            "(e.g. bot traffic, logging bug, assignment skew)."
        )

    # ── Key metrics row ─────────────────────────────────────────────────
    st.subheader("Results at a Glance")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Relative Lift",
        f"{result.relative_lift:+.2%}",
        delta=f"{'↑' if result.relative_lift > 0 else '↓'} vs control",
    )
    m2.metric("p-value", f"{result.p_value:.4f}", delta="sig." if result.is_significant else "not sig.")
    m3.metric("Control rate", f"{result.control_rate:.3%}")
    m4.metric("Treatment rate", f"{result.treatment_rate:.3%}")

    sig_badge = "✅ Statistically significant" if result.is_significant else "❌ Not statistically significant"
    st.info(sig_badge + f" at α=0.05 · 95% CI: [{result.ci_lower:+.4f}, {result.ci_upper:+.4f}]")

    # ── Charts ──────────────────────────────────────────────────────────
    col_chart1, col_chart2, col_chart3 = st.columns([2, 1.5, 1])
    with col_chart1:
        st.plotly_chart(confidence_interval_plot(result, metric_name), use_container_width=True)
    with col_chart2:
        st.plotly_chart(conversion_rate_bar(result, metric_name), use_container_width=True)
    with col_chart3:
        st.plotly_chart(power_gauge(result.power), use_container_width=True)

    # ── MDE reference ───────────────────────────────────────────────────
    mde = minimum_detectable_effect(
        n_per_variant=min(int(control_n), int(treatment_n)),
        baseline_rate=result.control_rate,
    )
    st.caption(
        f"Minimum detectable effect at 80% power with this sample size: ±{mde:.4f} absolute ({mde/result.control_rate:.2%} relative)"
    )

    # ── Claude interpretation ────────────────────────────────────────────
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

    # ── Handoff buttons ─────────────────────────────────────────────────
    st.subheader("Continue Your Analysis")
    handoff = build_handoff_context(result, metric_name, experiment_context)

    hcol1, hcol2 = st.columns(2)
    with hcol1:
        if not result.is_significant or result.relative_lift < 0:
            st.button(
                "🔍 Diagnose why this metric didn't move → Root Cause Analysis",
                help="Coming soon — will pre-load this experiment's context into the RCA tool.",
                disabled=True,
            )
    with hcol2:
        if result.is_significant:
            st.button(
                "⚖️ Analyze metric trade-offs for this change → Metric Trade-offs",
                help="Coming soon — will pre-load this metric into the Trade-offs tool.",
                disabled=True,
            )

    # ── Export context (for manual handoff now) ──────────────────────────
    with st.expander("Export experiment context (for RCA / Trade-offs tools)"):
        st.code(json.dumps(handoff, indent=2), language="json")
        st.caption("Copy this JSON to pre-load context into other tools in the suite.")
