"""Analytics AI Toolkit — home page (Streamlit Cloud entry point)."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from shared.ui import inject_css, render_sidebar, hero, AUTHOR, GITHUB_URL, LINKEDIN_URL, LIVE_DEMO_URL

st.set_page_config(
    page_title="Analytics AI Toolkit",
    page_icon="📊",
    layout="wide",
)

inject_css()

with st.sidebar:
    st.markdown(
        f"""
        <div style="padding: 0.5rem 0 1rem 0;">
            <div style="font-size:1.1rem; font-weight:700; color:#F1F5F9;">
                📊 Analytics AI Toolkit
            </div>
            <div style="font-size:0.78rem; color:#64748B; margin-top:2px;">
                by <a href="{LINKEDIN_URL}" target="_blank"
                   style="color:#93C5FD !important;">{AUTHOR}</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("**Tools**")
    st.page_link("pages/1_AB_Test_Interpreter.py", label="🧪 A/B Test Interpreter")
    st.page_link("pages/2_Root_Cause_Analysis.py", label="🔍 Root Cause Analysis")
    st.page_link("pages/3_Metric_Tradeoffs.py",    label="⚖️ Metric Trade-offs")
    st.divider()
    st.markdown(
        f'<div style="font-size:0.75rem; color:#475569; line-height:1.6;">'
        f'Powered by <a href="https://anthropic.com" target="_blank">Claude</a> · '
        f'<a href="{GITHUB_URL}" target="_blank">GitHub</a>'
        f"</div>",
        unsafe_allow_html=True,
    )

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 100%);
        border-radius: 14px;
        padding: 2.8rem 2.5rem 2.2rem 2.5rem;
        margin-bottom: 2rem;
    ">
        <h1 style="color:#F1F5F9; font-size:2.2rem; margin:0 0 0.5rem 0; font-weight:800;">
            📊 Analytics AI Toolkit
        </h1>
        <p style="color:#94A3B8; font-size:1.05rem; margin:0 0 0.8rem 0;">
            AI-powered reasoning suite for analysts and data scientists.
            Built with Claude + Streamlit + SciPy.
        </p>
        <p style="color:#64748B; font-size:0.85rem; margin:0;">
            Built by
            <a href="{LINKEDIN_URL}" target="_blank"
               style="color:#93C5FD; text-decoration:none; font-weight:600;">{AUTHOR}</a>
            &nbsp;·&nbsp;
            <a href="{GITHUB_URL}" target="_blank"
               style="color:#93C5FD; text-decoration:none;">View on GitHub</a>
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Tool cards ────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3, gap="large")

card_style = """
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1.6rem 1.4rem 1.2rem 1.4rem;
    height: 100%;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
"""

with col1:
    st.markdown(
        f'<div style="{card_style}">'
        '<div style="font-size:1.8rem; margin-bottom:0.5rem;">🧪</div>'
        '<h3 style="margin:0 0 0.6rem 0; font-size:1.1rem;">A/B Test Interpreter</h3>'
        '<p style="color:#64748B; font-size:0.88rem; line-height:1.55; margin:0 0 1rem 0;">'
        'Run a two-proportion z-test, get a 95% confidence interval, detect SRM, '
        'calculate post-hoc power, and receive a Claude-generated ship / don\'t-ship recommendation.'
        '</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_AB_Test_Interpreter.py", label="Open A/B Test Interpreter →")

with col2:
    st.markdown(
        f'<div style="{card_style}">'
        '<div style="font-size:1.8rem; margin-bottom:0.5rem;">🔍</div>'
        '<h3 style="margin:0 0 0.6rem 0; font-size:1.1rem;">Root Cause Analysis</h3>'
        '<p style="color:#64748B; font-size:0.88rem; line-height:1.55; margin:0 0 1rem 0;">'
        'Describe a metric movement. Get a structured hypothesis matrix across 5 categories, '
        'diagnostic SQL templates, and AI-prioritized next steps.'
        '</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Root_Cause_Analysis.py", label="Open Root Cause Analysis →")

with col3:
    st.markdown(
        f'<div style="{card_style}">'
        '<div style="font-size:1.8rem; margin-bottom:0.5rem;">⚖️</div>'
        '<h3 style="margin:0 0 0.6rem 0; font-size:1.1rem;">Metric Trade-offs</h3>'
        '<p style="color:#64748B; font-size:0.88rem; line-height:1.55; margin:0 0 1rem 0;">'
        'Map the second-order effects of any metric optimization. Get a full metric hierarchy, '
        'trade-off surface, guardrail recommendations, and a ship recommendation.'
        '</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_Metric_Tradeoffs.py", label="Open Metric Trade-offs →")

# ── How tools connect ─────────────────────────────────────────────────────────
st.divider()
st.markdown(
    """
    <div style="background:white; border:1px solid #E2E8F0; border-radius:12px;
                padding:1.4rem 1.6rem; box-shadow:0 1px 4px rgba(0,0,0,0.06);">
        <h4 style="margin:0 0 0.6rem 0; color:#0F172A;">How the tools connect</h4>
        <p style="color:#475569; font-size:0.88rem; margin:0; line-height:1.7;">
            <strong>A/B test shows no lift</strong> → export JSON → paste into
            <strong>Root Cause Analysis</strong> to diagnose why &nbsp;→&nbsp;
            export JSON → paste into <strong>Metric Trade-offs</strong> to evaluate
            the cost of fixing it.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
