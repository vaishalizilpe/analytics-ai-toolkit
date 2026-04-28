"""Metric Trade-offs — Streamlit app."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import streamlit as st
from metric_tradeoffs.tradeoffs import analyze_tradeoffs, generate_drill_answer, CHANGE_TYPES, PRACTICE_PRODUCTS

st.set_page_config(
    page_title="Metric Trade-offs",
    page_icon="⚖️",
    layout="wide",
)

with st.sidebar:
    st.title("Analytics AI Toolkit")
    st.markdown("---")
    st.markdown("**Tools**")
    st.markdown("🧪 [A/B Test Interpreter](http://localhost:8501)")
    st.markdown("🔍 [Root Cause Analysis](http://localhost:8502)")
    st.markdown("⚖️ **Metric Trade-offs** ← you are here")
    st.markdown("---")
    st.caption("Powered by Claude · [GitHub](https://github.com/vaishalizilpe/analytics-ai-toolkit)")

st.title("⚖️ Metric Trade-offs")

tab_analyze, tab_drill = st.tabs(["Analyze Trade-offs", "Interview Prep: Metric Drill"])

# ══════════════════════════════════════════════════════════════════════════════
# Tab 1: Analyze Trade-offs
# ══════════════════════════════════════════════════════════════════════════════
with tab_analyze:
    st.markdown(
        "Describe a metric you want to optimize and the proposed change. "
        "Get a full metric hierarchy, trade-off surface, guardrail recommendations, and a ship recommendation."
    )

    # Import from A/B test or RCA
    with st.expander("Import context from A/B Test Interpreter or RCA tool (optional)"):
        handoff_raw = st.text_area(
            "Paste context JSON",
            placeholder='{"source": "ab_test_interpreter", "metric": "...", "experiment_context": "..."}',
            height=90,
            key="tradeoffs_handoff_input",
        )
        handoff = None
        if handoff_raw.strip():
            try:
                handoff = json.loads(handoff_raw)
                source = handoff.get("source", "unknown")
                metric = handoff.get("metric", "?")
                st.success(f"Loaded from {source}: **{metric}**")
            except json.JSONDecodeError:
                st.error("Invalid JSON.")
                handoff = None

    default_metric = handoff.get("metric", "") if handoff else ""
    default_context = (
        handoff.get("experiment_context") or handoff.get("context", "")
        if handoff else ""
    )

    with st.form("tradeoffs_form"):
        st.subheader("What are you optimizing?")

        c1, c2 = st.columns([2, 1])
        with c1:
            primary_metric = st.text_input(
                "Primary metric",
                value=default_metric,
                placeholder="e.g. checkout conversion rate, 7-day retention, time-on-platform",
            )
        with c2:
            change_type = st.selectbox("Type of change", CHANGE_TYPES)

        change_description = st.text_area(
            "What does the change do?",
            placeholder="e.g. Replace gray checkout button with green, add urgency messaging to listing page",
            height=75,
        )
        product_context = st.text_area(
            "Product / platform context",
            value=default_context,
            placeholder="e.g. iOS e-commerce app, B2B SaaS, two-sided marketplace",
            height=75,
        )
        business_goal = st.text_input(
            "Business goal",
            placeholder="e.g. Increase Q3 revenue, improve 30-day retention, reduce churn",
        )
        secondary_metrics = st.text_input(
            "Other metrics you're currently tracking (optional)",
            placeholder="e.g. AOV, session length, support ticket rate, NPS",
        )

        submitted = st.form_submit_button("Analyze Trade-offs", type="primary", use_container_width=True)

    if submitted:
        if not primary_metric.strip():
            st.warning("Enter the primary metric you're optimizing.")
            st.stop()
        if not change_description.strip():
            st.warning("Describe what the change does.")
            st.stop()
        if not product_context.strip():
            st.warning("Add product context so Claude can generate a relevant metric hierarchy.")
            st.stop()

        # Summary
        st.subheader("Analysis Summary")
        s1, s2, s3 = st.columns(3)
        s1.metric("Optimizing", primary_metric)
        s2.metric("Change type", change_type)
        s3.metric("Goal", business_goal or "not specified")

        # Claude analysis
        st.subheader("AI Trade-off Analysis")
        with st.spinner("Claude is mapping the trade-off surface..."):
            try:
                analysis = analyze_tradeoffs(
                    primary_metric=primary_metric,
                    change_type=change_type,
                    change_description=change_description,
                    product_context=product_context,
                    business_goal=business_goal or "not specified",
                    secondary_metrics=secondary_metrics,
                )
                st.markdown(analysis)
            except EnvironmentError as e:
                st.error(str(e))
                st.stop()
            except Exception as e:
                st.error(f"Claude API error: {e}")
                st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# Tab 2: Interview Prep — 7-Day Metric Drill
# ══════════════════════════════════════════════════════════════════════════════
with tab_drill:
    st.markdown(
        "**Staff-level interview prep.** Practice defining a metric hierarchy for any product "
        "in under 90 seconds — the skill interviewers test at Staff and above."
    )
    st.markdown(
        "How to use: write your own answers first, then generate the model answer and compare. "
        "The gap between your answer and the model answer is your study target."
    )

    st.divider()
    st.subheader("The 5 Questions")
    st.markdown("""
1. What does success look like for this product?
2. What is the North Star Metric?
3. What are 3 input metrics that drive the North Star?
4. What are 2 guardrail metrics?
5. The North Star dropped 5% last week with no known changes. What are your first 3 hypotheses?
""")
    st.divider()

    drill_product = st.selectbox("Pick a product", PRACTICE_PRODUCTS, key="drill_product")

    your_answer = st.text_area(
        "Your answer (write this before generating the model answer)",
        placeholder="Write your answers to the 5 questions here before clicking Generate...",
        height=200,
        key="drill_your_answer",
    )

    generate_clicked = st.button(
        f"Generate model answer for {drill_product}",
        type="primary",
        key="drill_generate",
    )

    if generate_clicked:
        if not your_answer.strip():
            st.warning("Try writing your own answer first — the gap between yours and the model is where the learning is.")

        with st.spinner(f"Claude is generating a Staff-level model answer for {drill_product}..."):
            try:
                model_answer = generate_drill_answer(drill_product)
                st.subheader(f"Model Answer: {drill_product}")
                st.markdown(model_answer)

                if your_answer.strip():
                    st.divider()
                    st.subheader("Your Answer")
                    st.markdown(your_answer)
                    st.caption(
                        "Compare the two. Where was yours less specific? "
                        "What mechanisms did you miss? That's your study target for this product."
                    )
            except EnvironmentError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Claude API error: {e}")
