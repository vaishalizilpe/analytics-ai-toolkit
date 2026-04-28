# Analytics AI Toolkit

An AI-powered analytics reasoning suite built with Claude + Streamlit. Three interconnected tools that mirror how senior analysts actually think — not just dashboards, but reasoning engines.

## Tools

| Tool | Status | Description |
|------|--------|-------------|
| 🧪 A/B Test Interpreter | ✅ Live | Statistical analysis (z-test, CI, SRM, power) + AI interpretation + ship/don't-ship recommendation |
| 🔍 Root Cause Analysis | ✅ Live | Structured hypothesis matrix for metric drops, diagnostic SQL templates, prioritized next steps |
| ⚖️ Metric Trade-offs | ✅ Live | Second-order effect mapping, metric hierarchy, guardrail recommendations, interview prep drill |

## How the tools connect

Each tool hands off context to the next via a JSON export:

```
A/B test shows no lift  →  RCA to diagnose why
RCA surfaces a cause    →  Trade-offs to evaluate the cost of fixing it
Trade-offs recommends a test  →  A/B Interpreter to evaluate results
```

Copy the JSON from the "Export context" expander in any tool and paste it into the next.

## Quickstart

```bash
git clone https://github.com/vaishalizilpe/analytics-ai-toolkit.git
cd analytics-ai-toolkit
pip install -r requirements.txt
cp .env.example .env        # add your ANTHROPIC_API_KEY
```

Run each tool in a separate terminal:

```bash
streamlit run ab_test_interpreter/app.py     # localhost:8501
streamlit run root_cause_analysis/app.py     # localhost:8502
streamlit run metric_tradeoffs/app.py        # localhost:8503
```

## Tool breakdown

### 🧪 A/B Test Interpreter

**Statistical engine**
- Two-proportion z-test (p-value, significance at configurable alpha)
- 95% confidence interval on absolute lift
- Post-hoc power calculation
- Sample Ratio Mismatch (SRM) detection
- Minimum Detectable Effect reference

**AI interpretation**
- Plain-English explanation of what the result means
- Flags: low power, SRM, novelty effects, peeking
- RECOMMENDATION: Ship / Don't Ship / Extend Test
- FOLLOW-UP: segments to investigate, guardrail metrics, duration concerns

**Visualizations**
- Confidence interval forest plot
- Control vs. Treatment bar chart
- Post-hoc power gauge

### 🔍 Root Cause Analysis

**Input:** metric name, direction, magnitude, time window, known events, affected segments

**Output:**
- Immediate triage: data quality issue vs. real metric shift
- Hypothesis matrix across 5 categories: Data Quality/Pipeline, Product/Feature Changes, External/Seasonality, User Segment Shifts, Marketing/Business — each rated by likelihood and ease to check
- Diagnostic SQL templates: event volume, null rates, segment breakdown, before/after deploy
- Top 3 prioritized next steps

### ⚖️ Metric Trade-offs

**Analyze Trade-offs tab**

Input a metric and proposed change. Output:
- Full metric hierarchy: North Star → Primary → Secondary → Guardrail → Diagnostic
- Trade-off surface: what likely improves, what's at risk, what's unknown
- Acceptable vs. unacceptable trade-offs given business goal
- Guardrail metric recommendations with rollback thresholds
- Composite metric formula proposal
- Ship / Don't Ship / Modify recommendation

**Interview Prep: Metric Drill tab**

A practice tool for Staff Data Scientist interviews. Pick a product (Spotify, Airbnb, LinkedIn, Instacart, Apple Pay, and more). Write your own answers to the 5 standard metric definition questions, then generate a model Staff-level answer to compare against.

The 5 questions: North Star Metric, 3 input metrics, 2 guardrail metrics, and 3 hypotheses for a 5% NSM drop.

## Environment

```
ANTHROPIC_API_KEY=your_key_here
CLAUDE_MODEL=claude-sonnet-4-6      # optional, defaults to claude-sonnet-4-6
```

Never commit your `.env` file. It is in `.gitignore`.

## Screenshots

> Coming soon — demo GIF in progress.

## Tech stack

- [Claude](https://www.anthropic.com) (configurable via `CLAUDE_MODEL`) — AI reasoning
- [Streamlit](https://streamlit.io) — UI
- [SciPy](https://scipy.org) — statistical tests
- [Plotly](https://plotly.com) — interactive charts
- [python-dotenv](https://github.com/theskumar/python-dotenv) — environment config
