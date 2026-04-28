"""Root Cause Analysis — Streamlit app."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import streamlit as st
from root_cause_analysis.rca import analyze_metric_movement, DIAGNOSTIC_QUERIES

st.set_page_config(
    page_title="Root Cause Analysis",
    page_icon="🔍",
    layout="wide",
)

with st.sidebar:
    st.title("Analytics AI Toolkit")
    st.markdown("---")
    st.markdown("**Tools**")
    st.markdown("🧪 [A/B Test Interpreter](http://localhost:8501)")
    st.markdown("🔍 **Root Cause Analysis** ← you are here")
    st.markdown("⚖️ [Metric Trade-offs](http://localhost:8503)")
    st.markdown("---")
    st.caption("Powered by Claude · [GitHub](https://github.com/vaishalizilpe/analytics-ai-toolkit)")

st.title("🔍 Root Cause Analysis")
st.markdown(
    "Describe a metric movement. Get a structured hypothesis matrix, diagnostic SQL templates, "
    "and AI-powered analysis — organized by priority."
)

# ── Import from A/B Test Interpreter ─────────────────────────────────────────
with st.expander("Import experiment context from A/B Test Interpreter (optional)"):
    handoff_raw = st.text_area(
        "Paste experiment JSON",
        placeholder='{"source": "ab_test_interpreter", "metric": "...", "lift": -0.05, ...}',
        height=90,
        key="rca_handoff_input",
    )
    handoff = None
    if handoff_raw.strip():
        try:
            handoff = json.loads(handoff_raw)
            if handoff.get("source") == "ab_test_interpreter":
                lift = handoff.get("lift")
                st.success(
                    f"Loaded: **{handoff.get('metric', '?')}** — "
                    f"lift {lift:+.1%}" + (", not significant" if not handoff.get("significant") else ", significant")
                    if lift is not None
                    else f"Loaded: **{handoff.get('metric', '?')}**"
                )
        except json.JSONDecodeError:
            st.error("Invalid JSON.")
            handoff = None

default_metric = handoff.get("metric", "") if handoff else ""
default_magnitude = (
    f"{abs(handoff['lift']):.1%}" if handoff and handoff.get("lift") is not None else ""
)
default_context = handoff.get("experiment_context", "") if handoff else ""

# ── Input form ────────────────────────────────────────────────────────────────
with st.form("rca_form"):
    st.subheader("Describe the Metric Movement")

    c1, c2 = st.columns([3, 1])
    with c1:
        metric_name = st.text_input(
            "Metric name",
            value=default_metric,
            placeholder="e.g. 7-day retention, checkout conversion rate, DAU/MAU",
        )
    with c2:
        direction = st.selectbox(
            "Direction",
            ["dropped", "increased unexpectedly", "is volatile / erratic"],
        )

    c3, c4 = st.columns(2)
    with c3:
        magnitude = st.text_input(
            "Magnitude",
            value=default_magnitude,
            placeholder="e.g. -8% relative, dropped from 32% to 29%",
        )
    with c4:
        time_period = st.text_input(
            "When / time window",
            placeholder="e.g. last Monday, 7-day rolling vs prior period",
        )

    product_context = st.text_area(
        "Product / platform context",
        value=default_context,
        placeholder="e.g. iOS checkout flow, B2B SaaS dashboard, marketplace for freelancers",
        height=75,
    )
    known_events = st.text_area(
        "Known events around this time",
        placeholder="e.g. deployed v4.2 on Friday, ran email campaign, Thanksgiving week",
        height=75,
    )

    st.markdown("**Which user segments are affected?**")
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        seg_all = st.checkbox("All users", value=True)
        seg_new = st.checkbox("New users")
    with sc2:
        seg_returning = st.checkbox("Returning users")
        seg_mobile = st.checkbox("Mobile")
    with sc3:
        seg_desktop = st.checkbox("Desktop")
        seg_geo = st.checkbox("Specific geo")
    with sc4:
        seg_cohort = st.checkbox("Specific cohort")
        seg_unknown = st.checkbox("Not yet investigated")

    submitted = st.form_submit_button("Analyze", type="primary", use_container_width=True)

# ── Results ───────────────────────────────────────────────────────────────────
if submitted:
    if not metric_name.strip():
        st.warning("Enter a metric name.")
        st.stop()
    if not magnitude.strip():
        st.warning("Describe the magnitude of the change.")
        st.stop()

    segments = [
        label
        for flag, label in [
            (seg_all, "all users"),
            (seg_new, "new users"),
            (seg_returning, "returning users"),
            (seg_mobile, "mobile"),
            (seg_desktop, "desktop"),
            (seg_geo, "specific geo"),
            (seg_cohort, "specific cohort"),
            (seg_unknown, "not yet investigated"),
        ]
        if flag
    ]

    # Situation summary
    st.subheader("Situation Summary")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Metric", metric_name)
    m2.metric("Direction", direction.split()[0].capitalize())
    m3.metric("Magnitude", magnitude)
    m4.metric("Segments", ", ".join(segments) if segments else "unknown")

    if known_events.strip():
        st.info(f"Known events: {known_events}")

    # Diagnostic query templates
    st.subheader("Diagnostic Query Templates")
    st.caption("Run these first — ruling out data issues eliminates false alarms before you hypothesize.")

    tab_dq, tab_seg, tab_deploy = st.tabs([
        "1. Data Quality / Pipeline",
        "2. Segment Breakdown",
        "3. Deploy / Event Impact",
    ])

    with tab_dq:
        st.markdown("Start here. A logging bug or pipeline failure can mimic any metric drop.")
        for q in DIAGNOSTIC_QUERIES["Data Quality / Pipeline"]:
            st.markdown(f"**{q['name']}** — *{q['description']}*")
            st.code(q["sql"], language="sql")

    with tab_seg:
        st.markdown("Break the aggregate into segments. The drop is usually concentrated in one slice.")
        for q in DIAGNOSTIC_QUERIES["User Segment Shifts"]:
            st.markdown(f"**{q['name']}** — *{q['description']}*")
            st.code(q["sql"], language="sql")

    with tab_deploy:
        st.markdown("If there was a recent deploy or campaign, compare the metric before and after.")
        for q in DIAGNOSTIC_QUERIES["Product / Feature Changes"]:
            st.markdown(f"**{q['name']}** — *{q['description']}*")
            st.code(q["sql"], language="sql")

    # Claude analysis
    st.subheader("AI Root Cause Analysis")
    with st.spinner("Claude is building your hypothesis matrix..."):
        try:
            analysis = analyze_metric_movement(
                metric_name=metric_name,
                movement_direction=direction,
                magnitude=magnitude,
                time_period=time_period or "not specified",
                product_context=product_context or "not specified",
                known_events=known_events,
                affected_segments=segments,
            )
            st.markdown(analysis)
        except EnvironmentError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Claude API error: {e}")
            st.stop()

    # Handoff
    st.subheader("Continue Your Analysis")
    st.markdown("Once you have a hypothesis about what changed, use the Metric Trade-offs tool to analyze second-order effects.")
    handoff_out = {
        "source": "root_cause_analysis",
        "metric": metric_name,
        "movement": direction,
        "magnitude": magnitude,
        "context": product_context,
        "known_events": known_events,
    }
    with st.expander("Export context for Metric Trade-offs tool"):
        st.code(json.dumps(handoff_out, indent=2), language="json")
        st.caption("Copy this JSON and paste it into the Metric Trade-offs tool to analyze the proposed fix.")
