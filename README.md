# Analytics AI Toolkit

An AI-powered analytics reasoning suite built with Streamlit. Four interconnected tools that mirror how senior analysts actually think — not just dashboards, but reasoning engines. Swap LLM providers (Claude, OpenAI, DeepSeek, Gemini) with a single env var — no code changes required.

## Live Demo

👉 [Try the A/B Test Interpreter](https://analytics-ai-toolkit-vz.streamlit.app)

![Analytics AI Toolkit Demo](analytics_toolkit_demo.gif)

## Tools

| Tool | Status | Description |
|------|--------|-------------|
| 🧪 A/B Test Interpreter | ✅ Live | Expert-level statistical analysis + AI interpretation + ship/don't-ship recommendation |
| 📐 Sample Size Calculator | ✅ Live | Pre-experiment power analysis with sensitivity curves |
| 🔍 Root Cause Analysis | ✅ Live | Structured hypothesis matrix for metric drops, diagnostic SQL templates, prioritized next steps |
| ⚖️ Metric Trade-offs | ✅ Live | Second-order effect mapping, metric hierarchy, guardrail recommendations |

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
cp .env.example .env        # set LLM_PROVIDER and add your API key
```

```bash
streamlit run app.py
```

All tools load from one URL. Use the sidebar to navigate between them.

## Tool breakdown

### 🧪 A/B Test Interpreter

**Statistical engine**
- Normal approximation validation — falls back to Fisher's exact test when n×p < 10
- Two-proportion z-test with Cohen's h effect size (arcsine transform, accurate at extreme rates)
- Welch's t-test for continuous metrics (revenue, duration, engagement)
- 95% CI on absolute lift (Wald) and relative lift (delta method)
- Configurable significance threshold (α slider: 0.01–0.20)
- Multiple testing correction (Bonferroni) when testing multiple metrics simultaneously
- Sample Ratio Mismatch detection with diagnostic checklist
- CI vs. p-value consistency check (flags pooled/unpooled SE disagreement)
- MDE adequacy check: "Was this test adequately powered?" — replaces misleading post-hoc power gauge
- Practical significance threshold: flags statistically significant but negligible lifts
- Bayesian analysis: P(treatment > control) via Beta-Binomial simulation

**AI interpretation**
- Plain-English explanation of what the result means
- Flags: SRM, assumption violations, practical vs. statistical significance gap
- RECOMMENDATION: Ship / Don't Ship / Extend Test
- FOLLOW-UP: segments to investigate, guardrail metrics, duration concerns

**Visualizations**
- Confidence interval forest plot
- Control vs. Treatment bar chart

### 📐 Sample Size Calculator

- Conversion rate and continuous metric modes
- MDE as relative % or absolute units
- Power curve: statistical power vs. n per variant
- MDE sensitivity curve: detectable lift vs. n per variant
- Test duration estimate from daily traffic
- Configurable α and power targets

### 🔍 Root Cause Analysis

**Input:** metric name, direction, magnitude, time window, known events, affected segments

**Output:**
- Immediate triage: data quality issue vs. real metric shift
- Hypothesis matrix across 5 categories: Data Quality/Pipeline, Product/Feature Changes, External/Seasonality, User Segment Shifts, Marketing/Business — each rated by likelihood and ease to check
- Diagnostic SQL templates: event volume, null rates, segment breakdown, before/after deploy
- Top 3 prioritized next steps

### ⚖️ Metric Trade-offs

Input a metric and proposed change. Output:
- Full metric hierarchy: North Star → Primary → Secondary → Guardrail → Diagnostic
- Trade-off surface: what likely improves, what's at risk, what's unknown
- Acceptable vs. unacceptable trade-offs given business goal
- Guardrail metric recommendations with rollback thresholds
- Ship / Don't Ship / Modify recommendation

## Environment

```
# Choose your provider — only the matching API key is required
LLM_PROVIDER=claude          # claude | openai | deepseek | gemini
LLM_MODEL=                   # optional — overrides the provider default

ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
GEMINI_API_KEY=
```

| Provider | Default model | Key required |
|----------|--------------|--------------|
| `claude` (default) | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| `openai` | `gpt-4o` | `OPENAI_API_KEY` |
| `deepseek` | `deepseek-chat` | `DEEPSEEK_API_KEY` |
| `gemini` | `gemini-1.5-pro` | `GEMINI_API_KEY` |

Never commit your `.env` file. It is in `.gitignore`.

## Tech stack

- Claude / OpenAI / DeepSeek / Gemini (configurable via `LLM_PROVIDER`) — AI reasoning
- [Streamlit](https://streamlit.io) — UI
- [SciPy](https://scipy.org) — statistical tests
- [Plotly](https://plotly.com) — interactive charts
- [python-dotenv](https://github.com/theskumar/python-dotenv) — environment config
