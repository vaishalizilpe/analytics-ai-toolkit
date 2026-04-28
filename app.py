"""Analytics AI Toolkit — home page."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import streamlit as st

st.set_page_config(
    page_title="Analytics AI Toolkit",
    page_icon="📊",
    layout="wide",
)

with st.sidebar:
    st.caption("Powered by Claude · [GitHub](https://github.com/vaishalizilpe/analytics-ai-toolkit)")

st.title("📊 Analytics AI Toolkit")
st.markdown(
    "An AI-powered analytics reasoning suite that mirrors how senior analysts actually think. "
    "Three interconnected tools — pick the one that fits your situation."
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🧪 A/B Test Interpreter")
    st.markdown(
        "Enter experiment results. Get a z-test, confidence interval, power calculation, "
        "SRM detection, and a Claude-generated ship/don't-ship recommendation."
    )
    st.page_link("pages/1_AB_Test_Interpreter.py", label="Open A/B Test Interpreter →")

with col2:
    st.markdown("### 🔍 Root Cause Analysis")
    st.markdown(
        "Describe a metric drop or unexpected movement. Get a structured hypothesis matrix "
        "across 5 categories, diagnostic SQL templates, and prioritized next steps."
    )
    st.page_link("pages/2_Root_Cause_Analysis.py", label="Open Root Cause Analysis →")

with col3:
    st.markdown("### ⚖️ Metric Trade-offs")
    st.markdown(
        "Map the second-order effects of any metric optimization. Get a full metric hierarchy, "
        "trade-off surface, guardrail recommendations, and an interview prep drill."
    )
    st.page_link("pages/3_Metric_Tradeoffs.py", label="Open Metric Trade-offs →")

st.divider()
st.markdown(
    "**How the tools connect:** Run an A/B test → export context JSON → paste into RCA to diagnose "
    "why a metric didn't move → paste into Metric Trade-offs to evaluate the cost of fixing it."
)
