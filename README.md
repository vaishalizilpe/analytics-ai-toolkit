# Analytics AI Toolkit

An AI-powered analytics reasoning suite built with Claude + Streamlit. Three interconnected tools that mirror how senior analysts actually think — not just dashboards, but reasoning engines.

## Tools

| Tool | Status | Description |
|------|--------|-------------|
| 🧪 [A/B Test Interpreter](ab_test_interpreter/) | ✅ Live | Statistical analysis + AI interpretation + ship/don't-ship recommendation |
| 🔍 Root Cause Analysis | 🚧 Coming soon | Structured hypothesis generation for metric drops |
| ⚖️ Metric Trade-offs | 🚧 Coming soon | Second-order effect mapping for product decisions |

## How the tools connect

Each tool can hand off context to the next:
- **A/B test shows no lift?** → RCA to diagnose why
- **RCA surfaces a metric?** → Trade-offs to evaluate the cost of moving it
- **Trade-offs recommends a test?** → A/B Interpreter to evaluate results

## Quickstart

```bash
git clone https://github.com/vaishalizilpe/analytics-ai-toolkit.git
cd analytics-ai-toolkit
pip install -r requirements.txt
cp .env.example .env        # add your ANTHROPIC_API_KEY to .env
streamlit run ab_test_interpreter/app.py
```

## A/B Test Interpreter — what it does

**Statistical engine (`stats.py`)**
- Two-proportion z-test (p-value, significance)
- 95% confidence interval on absolute lift
- Post-hoc power calculation
- Sample Ratio Mismatch (SRM) detection
- Minimum Detectable Effect reference

**AI interpretation (`interpreter.py`)**
- Plain-English explanation of results
- Flags concerns: low power, SRM, novelty effects, peeking
- Clear RECOMMENDATION: Ship / Don't Ship / Extend Test
- FOLLOW-UP: segments, guardrail metrics, duration concerns

**Visualizations (`visualizations.py`)**
- Confidence interval forest plot
- Control vs. Treatment bar chart
- Post-hoc power gauge

## Environment

```
ANTHROPIC_API_KEY=your_key_here
```

Never commit your `.env` file. It is in `.gitignore`.

## Tech stack

- [Claude](https://www.anthropic.com) (claude-sonnet-4-6) — AI reasoning
- [Streamlit](https://streamlit.io) — UI
- [SciPy](https://scipy.org) — statistical tests
- [Plotly](https://plotly.com) — interactive charts
