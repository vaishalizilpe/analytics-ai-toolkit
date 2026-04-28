"""Shared UI helpers — CSS injection, sidebar, page headers."""
import streamlit as st

AUTHOR = "Vaishali Zilpe"
GITHUB_URL = "https://github.com/vaishalizilpe/analytics-ai-toolkit"
LINKEDIN_URL = "https://linkedin.com/in/vaishalizilpe"
LIVE_DEMO_URL = "https://analytics-ai-toolkit-vz.streamlit.app"

_CSS = """
<style>
/* ── Global ─────────────────────────────────────────── */
[data-testid="stAppViewContainer"] {
    background-color: #F8FAFC;
}
[data-testid="stSidebar"] {
    background-color: #0F172A;
}
[data-testid="stSidebar"] * {
    color: #CBD5E1 !important;
}
[data-testid="stSidebar"] a {
    color: #93C5FD !important;
    text-decoration: none;
}
[data-testid="stSidebar"] a:hover {
    color: #BFDBFE !important;
}
[data-testid="stSidebar"] hr {
    border-color: #1E293B !important;
}

/* ── Metric cards ───────────────────────────────────── */
[data-testid="metric-container"] {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

/* ── Form ───────────────────────────────────────────── */
[data-testid="stForm"] {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

/* ── Tabs ───────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 4px;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 6px 6px 0 0;
}

/* ── Expander ───────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
}
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def render_sidebar(current_tool: str = ""):
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding: 0.5rem 0 1rem 0;">
                <div style="font-size:1.1rem; font-weight:700; color:#F1F5F9; letter-spacing:0.01em;">
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

        tools = [
            ("🧪", "A/B Test Interpreter",   "pages/1_AB_Test_Interpreter.py"),
            ("🔍", "Root Cause Analysis",     "pages/2_Root_Cause_Analysis.py"),
            ("⚖️", "Metric Trade-offs",       "pages/3_Metric_Tradeoffs.py"),
        ]
        for icon, name, page in tools:
            label = f"{icon} **{name}**" if name == current_tool else f"{icon} {name}"
            st.page_link(page, label=label)

        st.divider()
        st.markdown(
            f'<div style="font-size:0.75rem; color:#475569; line-height:1.6;">'
            f'Powered by <a href="https://anthropic.com" target="_blank">Claude</a> · '
            f'<a href="{GITHUB_URL}" target="_blank">GitHub</a>'
            f"</div>",
            unsafe_allow_html=True,
        )


def hero(icon: str, title: str, subtitle: str):
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 100%);
            border-radius: 14px;
            padding: 2.2rem 2rem 1.8rem 2rem;
            margin-bottom: 1.5rem;
        ">
            <div style="font-size:2rem; margin-bottom:0.3rem;">{icon}</div>
            <h1 style="color:#F1F5F9; font-size:1.75rem; margin:0 0 0.4rem 0;
                       font-weight:700; line-height:1.2;">{title}</h1>
            <p style="color:#94A3B8; font-size:0.95rem; margin:0;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
