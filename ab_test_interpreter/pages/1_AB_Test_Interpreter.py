"""A/B Test Interpreter — Streamlit page (legacy path, kept for Streamlit Cloud routing)."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import numpy as np
import streamlit as st
import json
from ab_test_interpreter.stats import (
    run_proportion_test, run_ttest, minimum_detectable_effect,
    sample_size_for_proportion, sample_size_for_continuous,
    bayesian_ab_test,
)
from ab_test_interpreter.interpreter import interpret_results, interpret_continuous_results, build_handoff_context
from ab_test_interpreter.visualizations import (
    confidence_interval_plot, conversion_rate_bar, mean_bar_chart,
    power_curve, mde_curve,
    null_distribution_chart, lift_vs_mde_chart, beta_posterior_chart,
)
from shared.constants import MIN_SAMPLE_SIZE

SRM_CAUSES = [
    ("Bot traffic", "One arm may have higher bot traffic. Check device type distribution and user agent patterns."),
    ("Redirect latency", "Redirect delays cause differential drop-off at assignment. Compare server-side assignment logs with event logs."),
    ("Cache poisoning", "Cached pages may serve stale variant assignments. Purge CDN cache and check cache headers per arm."),
    ("Logging lag", "Event logging delays can undercount one arm. Compare assignment counts vs event counts for a 24h window."),
    ("Holdback contamination", "Users assigned to control may have been exposed to treatment via shared devices or a misconfigured holdback."),
]

st.set_page_config(
    page_title="A/B Test Interpreter",
    page_icon="🧪",
    layout="wide",
)

with st.sidebar:
    st.caption("Powered by Claude · [GitHub](https://github.com/vaishalizilpe/analytics-ai-toolkit)")

st.title("🧪 A/B Test Interpreter")
st.markdown(
    "Enter your experiment results. Get statistical analysis + AI-powered interpretation "
    "with a clear ship/don't-ship recommendation."
)

tab1, tab2 = st.tabs(["🔬 Analyze Results", "📐 Sample Size Calculator"])

# ── Tab 1: Analyze Results ────────────────────────────────────────────────────

with tab1:
    metric_type = st.selectbox(
        "Metric type",
        ["Conversion rate (proportion)", "Continuous (revenue, duration, engagement)"],
        help="Proportion: binary yes/no events (purchases, signups, clicks). "
             "Continuous: numeric values with a mean and standard deviation.",
    )
    is_proportion = metric_type == "Conversion rate (proportion)"

    with st.form("ab_test_form"):
        st.subheader("Experiment Setup")

        experiment_context = st.text_area(
            "Describe the experiment",
            placeholder="e.g. We redesigned the checkout button from gray to green on the iOS app. "
                        "Launched to 50% of users for 14 days. Primary metric: purchase conversion rate.",
            height=100,
        )
        metric_name = st.text_input("Primary metric name", value="", placeholder="e.g. Purchase conversion rate")

        col1, col2 = st.columns(2)

        if is_proportion:
            with col1:
                st.markdown("**Control group**")
                control_n = st.number_input("Users", min_value=1, value=10000, step=100, key="cn")
                control_conv = st.number_input("Conversions", min_value=0, value=320, step=10, key="cc")
            with col2:
                st.markdown("**Treatment group**")
                treatment_n = st.number_input("Users", min_value=1, value=10200, step=100, key="tn")
                treatment_conv = st.number_input("Conversions", min_value=0, value=374, step=10, key="tc")
        else:
            with col1:
                st.markdown("**Control group**")
                control_n = st.number_input("Users", min_value=2, value=10000, step=100, key="cn")
                control_mean = st.number_input("Mean", value=45.00, step=0.01, format="%.2f", key="cm")
                control_std = st.number_input("Std dev", min_value=0.01, value=12.00, step=0.01, format="%.2f", key="cs")
            with col2:
                st.markdown("**Treatment group**")
                treatment_n = st.number_input("Users", min_value=2, value=10200, step=100, key="tn")
                treatment_mean = st.number_input("Mean", value=47.50, step=0.01, format="%.2f", key="tm")
                treatment_std = st.number_input("Std dev", min_value=0.01, value=12.30, step=0.01, format="%.2f", key="ts")

        expected_split = st.slider(
            "Expected traffic split (control %)", min_value=10, max_value=90, value=50, step=5
        ) / 100

        col_adv1, col_adv2, col_adv3 = st.columns(3)
        with col_adv1:
            alpha = st.slider(
                "Significance threshold (α)",
                min_value=0.01, max_value=0.20, value=0.05, step=0.01,
                format="%.2f",
            )
        with col_adv2:
            n_metrics = st.number_input(
                "Metrics being tested simultaneously",
                min_value=1, max_value=100, value=1, step=1,
                help="For multiple testing correction. If you are testing 1 metric, leave at 1.",
            )
        with col_adv3:
            min_practical_effect = st.number_input(
                "Min practical significance (absolute, optional)",
                min_value=0.0, value=0.0, step=0.001, format="%.4f",
                help="Minimum lift worth shipping. 0 = skip this check.",
            )

        submitted = st.form_submit_button("Analyze", type="primary", use_container_width=True)

    if submitted:
        if not experiment_context.strip():
            st.warning("Please describe the experiment so Claude can provide meaningful context.")
            st.stop()
        if not metric_name.strip():
            st.warning("Please enter a metric name.")
            st.stop()

        corrected_alpha = alpha / n_metrics if n_metrics > 1 else alpha

        if is_proportion:
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
                    alpha=alpha,
                    expected_split=expected_split,
                )
        else:
            if int(control_n) < MIN_SAMPLE_SIZE or int(treatment_n) < MIN_SAMPLE_SIZE:
                st.warning(f"Sample size below minimum ({MIN_SAMPLE_SIZE:,} users). Results may not be reliable.")

            with st.spinner("Running statistical tests..."):
                result = run_ttest(
                    control_mean=float(control_mean),
                    control_std=float(control_std),
                    control_n=int(control_n),
                    treatment_mean=float(treatment_mean),
                    treatment_std=float(treatment_std),
                    treatment_n=int(treatment_n),
                    alpha=alpha,
                    expected_split=expected_split,
                )

        if is_proportion:
            if result.fisher_used:
                st.warning(
                    "Normal approximation invalid (n×p < 10 in one or more cells). "
                    "**Fisher's exact test** was used instead of the z-test. "
                    "The confidence interval is still Wald-based and should be treated as approximate."
                )
            if not result.significance_ci_consistent:
                st.info(
                    "Note: the p-value and confidence interval give different significance signals. "
                    "This happens because the z-test uses pooled SE (correct for testing H₀: p₁=p₂) "
                    "while the CI uses unpooled SE (correct for estimation). Both are methodologically valid — "
                    "the result is borderline and the two approaches bracket the decision boundary."
                )

        if result.srm_flagged:
            st.error(
                f"⚠️ **Sample Ratio Mismatch detected** (SRM p-value: {result.srm_p_value:.4f}). "
                "The traffic split differs significantly from expected. "
                "Do not draw conclusions from this test until you identify the root cause."
            )
            with st.expander("SRM diagnostic checklist"):
                for cause, description in SRM_CAUSES:
                    st.markdown(f"**{cause}:** {description}")

        st.subheader("Results at a Glance")
        m1, m2, m3, m4 = st.columns(4)
        lift_display = f"{result.relative_lift:+.2%}" if result.relative_lift is not None else "undefined"
        lift_delta = f"{'↑' if (result.relative_lift or 0) > 0 else '↓'} vs control" if result.relative_lift is not None else "0 control value"
        m1.metric("Relative Lift", lift_display, delta=lift_delta)
        m2.metric("p-value", f"{result.p_value:.4f}", delta="sig." if result.is_significant else "not sig.")

        if is_proportion:
            m3.metric("Control rate", f"{result.control_rate:.3%}")
            m4.metric("Treatment rate", f"{result.treatment_rate:.3%}")
        else:
            m3.metric("Control mean", f"{result.control_mean:.3f}")
            m4.metric("Treatment mean", f"{result.treatment_mean:.3f}")

        sig_badge = "✅ Statistically significant" if result.is_significant else "❌ Not statistically significant"
        abs_ci = f"95% CI on absolute lift: [{result.ci_lower:+.4f}, {result.ci_upper:+.4f}]"
        if is_proportion and result.relative_lift_ci_lower is not None:
            rel_ci = f" · 95% CI on relative lift: [{result.relative_lift_ci_lower:+.1%}, {result.relative_lift_ci_upper:+.1%}]"
        else:
            rel_ci = ""
        st.info(f"{sig_badge} at α={alpha} · {abs_ci}{rel_ci}")

        if n_metrics > 1:
            corrected_significant = result.p_value < corrected_alpha
            corrected_label = "✅ passes" if corrected_significant else "❌ fails"
            st.caption(
                f"Multiple testing correction (Bonferroni, {n_metrics} metrics): "
                f"corrected threshold α={corrected_alpha:.4f} — p={result.p_value:.4f} {corrected_label} the corrected threshold."
            )

        if min_practical_effect > 0 and result.is_significant:
            is_prac_sig = result.absolute_lift >= min_practical_effect and result.ci_lower > 0
            if not is_prac_sig:
                st.warning(
                    f"Statistically significant, but the observed lift ({result.absolute_lift:+.4f}) "
                    f"is below your practical significance threshold ({min_practical_effect:.4f}). "
                    "Consider not shipping — the effect may be real but too small to matter."
                )

        col_chart1, col_chart2 = st.columns([2, 1.5])
        with col_chart1:
            st.plotly_chart(confidence_interval_plot(result, metric_name), use_container_width=True)
        with col_chart2:
            if is_proportion:
                st.plotly_chart(conversion_rate_bar(result, metric_name), use_container_width=True)
            else:
                st.plotly_chart(mean_bar_chart(result, metric_name), use_container_width=True)

        if is_proportion and not result.fisher_used:
            st.plotly_chart(
                null_distribution_chart(result.p_value, result.absolute_lift, alpha),
                use_container_width=True,
            )

        if is_proportion:
            mde = minimum_detectable_effect(
                n_control=int(control_n),
                n_treatment=int(treatment_n),
                baseline_rate=result.control_rate,
                alpha=alpha,
            )
            mde_rel = mde / result.control_rate if result.control_rate > 0 else None
            observed_abs = abs(result.absolute_lift)
            adequately_powered = observed_abs >= mde

            with st.container(border=True):
                st.markdown("**Was this test adequately powered?**")
                adeq_cols = st.columns([1, 2])
                with adeq_cols[0]:
                    if adequately_powered:
                        st.success("Yes")
                    else:
                        st.error("No")
                    mde_display = f"{mde:.4f} abs"
                    if mde_rel is not None:
                        mde_display += f" ({mde_rel:.1%} rel)"
                    st.caption(f"MDE: {mde_display}")
                    st.caption(f"Observed: {result.absolute_lift:+.4f}")
                with adeq_cols[1]:
                    st.plotly_chart(
                        lift_vs_mde_chart(result.absolute_lift, result.ci_lower, result.ci_upper, mde),
                        use_container_width=True,
                    )

        if is_proportion:
            with st.expander("Bayesian Analysis (Beta-Binomial)"):
                st.caption(
                    "Frequentist p-values tell you P(data | H₀). "
                    "The Bayesian posterior tells you P(treatment wins | data) — "
                    "which is what most PMs actually want to know."
                )
                with st.spinner("Running simulation..."):
                    prob_wins, expected_lift = bayesian_ab_test(
                        int(control_conv), int(control_n),
                        int(treatment_conv), int(treatment_n),
                    )
                b1, b2 = st.columns(2)
                b1.metric("P(treatment > control)", f"{prob_wins:.1%}")
                b2.metric("Expected relative lift", f"{expected_lift:+.2%}")
                st.plotly_chart(
                    beta_posterior_chart(
                        int(control_conv), int(control_n),
                        int(treatment_conv), int(treatment_n),
                        prob_wins,
                    ),
                    use_container_width=True,
                )
                st.caption(
                    "Uniform prior Beta(1,1). With large samples, the posterior converges to the frequentist result. "
                    "At small samples, it regularizes toward 50/50 — which is often more honest than a sharp p-value."
                )

        st.subheader("AI Interpretation")
        with st.spinner("Claude is analyzing your results..."):
            try:
                if is_proportion:
                    interpretation = interpret_results(
                        result, metric_name, experiment_context,
                        min_practical_effect=min_practical_effect,
                        n_metrics=int(n_metrics),
                        corrected_alpha=corrected_alpha,
                    )
                else:
                    interpretation = interpret_continuous_results(result, metric_name, experiment_context)
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

# ── Tab 2: Sample Size Calculator ────────────────────────────────────────────

with tab2:
    st.subheader("Sample Size Calculator")
    st.caption("Figure out how many users you need before you start your test.")

    calc_type = st.radio(
        "Metric type",
        ["Conversion rate", "Continuous (revenue, duration, engagement)"],
        horizontal=True,
        key="calc_type",
    )
    is_prop_calc = calc_type == "Conversion rate"

    st.divider()

    col_in, col_out = st.columns([1, 1], gap="large")

    with col_in:
        st.markdown("**Test parameters**")

        calc_alpha = st.select_slider(
            "Significance level (α)",
            options=[0.01, 0.05, 0.10],
            value=0.05,
            format_func=lambda x: f"{x} ({int((1-x)*100)}% confidence)",
            key="calc_alpha",
        )
        calc_power = st.select_slider(
            "Statistical power",
            options=[0.70, 0.80, 0.90],
            value=0.80,
            format_func=lambda x: f"{x:.0%}",
            key="calc_power",
        )

        st.markdown("---")

        if is_prop_calc:
            calc_baseline = st.number_input(
                "Baseline conversion rate (%)",
                min_value=0.01, max_value=99.99, value=3.20, step=0.10, format="%.2f",
                key="calc_base",
            ) / 100
            calc_mde_type = st.radio(
                "MDE expressed as",
                ["Relative % lift", "Absolute percentage points"],
                horizontal=True,
                key="calc_mde_type",
            )
            if calc_mde_type == "Relative % lift":
                calc_mde_rel = st.number_input(
                    "Minimum detectable effect (relative %)",
                    min_value=0.1, max_value=200.0, value=10.0, step=0.5, format="%.1f",
                    key="calc_mde_r",
                ) / 100
                calc_mde_abs = calc_baseline * calc_mde_rel
            else:
                calc_mde_abs = st.number_input(
                    "Minimum detectable effect (percentage points)",
                    min_value=0.01, max_value=50.0, value=0.32, step=0.01, format="%.2f",
                    key="calc_mde_a",
                ) / 100
                calc_mde_rel = calc_mde_abs / calc_baseline if calc_baseline > 0 else 0
            calc_daily = st.number_input(
                "Daily users (optional — for duration estimate)",
                min_value=0, value=0, step=500, key="calc_daily",
            )
        else:
            calc_baseline_mean = st.number_input(
                "Baseline mean", min_value=0.01, value=45.00, step=0.01, format="%.2f", key="calc_mean",
            )
            calc_baseline_std = st.number_input(
                "Baseline std dev", min_value=0.01, value=12.00, step=0.01, format="%.2f", key="calc_std",
                help="If unknown, 20-30% of the mean is a common starting estimate.",
            )
            calc_mde_type_c = st.radio(
                "MDE expressed as", ["Relative % of mean", "Absolute units"],
                horizontal=True, key="calc_mde_type_c",
            )
            if calc_mde_type_c == "Relative % of mean":
                calc_mde_rel_c = st.number_input(
                    "Minimum detectable effect (relative %)",
                    min_value=0.1, max_value=200.0, value=5.0, step=0.5, format="%.1f", key="calc_mde_rc",
                ) / 100
                calc_mde_abs_c = calc_baseline_mean * calc_mde_rel_c
            else:
                calc_mde_abs_c = st.number_input(
                    "Minimum detectable effect (absolute units)",
                    min_value=0.01, value=2.25, step=0.01, format="%.2f", key="calc_mde_ac",
                )
                calc_mde_rel_c = calc_mde_abs_c / calc_baseline_mean if calc_baseline_mean > 0 else 0
            calc_daily = st.number_input(
                "Daily users (optional — for duration estimate)",
                min_value=0, value=0, step=500, key="calc_daily_c",
            )

    if is_prop_calc:
        valid = 0 < calc_mde_abs < 1
    else:
        valid = calc_mde_abs_c > 0

    with col_out:
        if not valid:
            st.error("MDE must be between 0% and 100%." if is_prop_calc else "MDE must be greater than 0.")
        else:
            if is_prop_calc:
                n = sample_size_for_proportion(calc_baseline, calc_mde_abs, alpha=calc_alpha, power=calc_power)
            else:
                n = sample_size_for_continuous(calc_baseline_std, calc_mde_abs_c, alpha=calc_alpha, power=calc_power)

            total = n * 2
            st.markdown("**Required sample size**")
            m1, m2 = st.columns(2)
            m1.metric("Per variant", f"{n:,}")
            m2.metric("Total (both variants)", f"{total:,}")

            if calc_daily > 0:
                days = total / calc_daily
                st.metric("Estimated test duration", f"{days:.1f} days ({days/7:.1f} weeks)")
                if days < 7:
                    st.warning("Under 7 days — run at least a full week to capture weekly seasonality.")
                elif days > 56:
                    st.warning("Over 8 weeks — consider raising your MDE or accepting a less strict α.")

            if is_prop_calc:
                st.info(
                    f"Detects **{calc_baseline:.2%} → {calc_baseline + calc_mde_abs:.2%}** "
                    f"(+{calc_mde_abs:.2%} absolute, +{calc_mde_rel:.1%} relative lift)"
                )
            else:
                st.info(
                    f"Detects **{calc_mde_rel_c:.1%} relative lift** · "
                    f"Cohen's d: **{calc_mde_abs_c / calc_baseline_std:.2f}**"
                )

            st.divider()

            if is_prop_calc:
                p2 = float(np.clip(calc_baseline + calc_mde_abs, 0, 1))
                pooled_var = (calc_baseline * (1 - calc_baseline) + p2 * (1 - p2)) / 2
                eff = calc_mde_abs / np.sqrt(pooled_var) if pooled_var > 0 else 0
            else:
                eff = calc_mde_abs_c / calc_baseline_std if calc_baseline_std > 0 else 0

            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(power_curve(eff, calc_alpha, n, calc_power), use_container_width=True)
            with c2:
                if is_prop_calc:
                    st.plotly_chart(mde_curve(calc_baseline, calc_alpha, calc_power, n), use_container_width=True)
                else:
                    st.caption("MDE sensitivity curve is available for conversion rate metrics.")

            st.caption(
                "No Claude API call on this page — sample size is pure math. "
                "Run your experiment, then use the Analyze Results tab for AI interpretation."
            )
