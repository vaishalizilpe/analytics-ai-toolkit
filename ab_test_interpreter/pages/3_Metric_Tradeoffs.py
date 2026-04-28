"""Metric Trade-offs — Streamlit page."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import streamlit as st
from metric_tradeoffs.tradeoffs import analyze_tradeoffs, CHANGE_TYPES
from shared.ui import inject_css, render_sidebar, hero

st.set_page_config(page_title="Metric Trade-offs", page_icon="⚖️", layout="wide")
inject_css()
render_sidebar("Metric Trade-offs")

hero(
    "⚖️",
    "Metric Trade-offs",
    "Describe a metric you want to optimize and the proposed change. Get a full metric hierarchy, "
    "trade-off surface, guardrail recommendations, and a ship recommendation.",
)

with st.expander("Import context from A/B Test Interpreter or RCA tool (optional)"):
    handoff_raw = st.text_area(
        "Paste context JSON",
        placeholder='{"source": "ab_test_interpreter", "metric": "...", "experiment_context": "..."}',
        height=90, key="tradeoffs_handoff_input",
    )
    handoff = None
    if handoff_raw.strip():
        try:
            handoff = json.loads(handoff_raw)
            st.success(f"Loaded from {handoff.get('source', 'unknown')}: **{handoff.get('metric', '?')}**")
        except json.JSONDecodeError:
            st.error("Invalid JSON.")
            handoff = None

default_metric  = handoff.get("metric", "") if handoff else ""
default_context = (handoff.get("experiment_context") or handoff.get("context", "")) if handoff else ""

with st.form("tradeoffs_form"):
    st.subheader("What are you optimizing?")
    c1, c2 = st.columns([2, 1])
    with c1:
        primary_metric = st.text_input(
            "Primary metric", value=default_metric,
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
        "Product / platform context", value=default_context,
        placeholder="e.g. iOS e-commerce app, B2B SaaS, two-sided marketplace", height=75,
    )
    business_goal = st.text_input(
        "Business goal", placeholder="e.g. Increase Q3 revenue, improve 30-day retention, reduce churn",
    )
    secondary_metrics = st.text_input(
        "Other metrics you're tracking (optional)",
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

    st.subheader("Analysis Summary")
    s1, s2, s3 = st.columns(3)
    s1.metric("Optimizing", primary_metric)
    s2.metric("Change type", change_type)
    s3.metric("Goal", business_goal or "not specified")

    st.subheader("AI Trade-off Analysis")
    with st.spinner("Claude is mapping the trade-off surface..."):
        try:
            analysis = analyze_tradeoffs(
                primary_metric=primary_metric, change_type=change_type,
                change_description=change_description, product_context=product_context,
                business_goal=business_goal or "not specified", secondary_metrics=secondary_metrics,
            )
            st.markdown(analysis)
        except EnvironmentError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Claude API error: {e}")
            st.stop()
