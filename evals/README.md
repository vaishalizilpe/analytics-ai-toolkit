# Evals: measuring and improving the LLM outputs

This toolkit turns analytics inputs into LLM-generated recommendations. LLM output is not predictable, so quality has to be measured, not assumed. This directory is a graded eval suite plus an error-analysis loop that does exactly that.

## What it checks
Each case in `dataset.jsonl` runs through the same functions the app uses, then two layers of grading:

- **Deterministic graders** (`graders.py`, no API, run in CI): structural checks that the required sections are present, and, for A/B tests, faithfulness checks against the deterministic ground-truth stats. Examples: a non-significant result may not be sold as a clean Ship; a Sample Ratio Mismatch must be surfaced; a 0% control rate may not quote a relative-lift number.
- **LLM-as-judge** (optional, costs API calls): scores correctness, faithfulness, and actionability 0-5 against the ground truth. Nondeterministic, so it informs error analysis but is not the pass/fail gate.

## Run it
```bash
python -m evals.run_evals            # deterministic graders only
python -m evals.run_evals --judge    # also run the LLM-as-judge (uses your configured LLM_PROVIDER)
```
Both modes call each app module once to produce the output being graded, so both need a valid API key and cost a little. The only layer that runs with no key and no cost is the grader unit tests (`tests/test_evals_graders.py`), which is what CI runs on every push.

Results write to `evals/results/evals_<timestamp>.json` and are committed intentionally: the dated result files plus `ERROR_ANALYSIS.md` are the evidence that the loop actually ran and where the pass rate moved over time. The run exits non-zero if the deterministic pass rate drops below 0.80, so it can gate CI.

## Coverage
Cases in `dataset.jsonl` exercise both A/B paths (proportion z-test and the continuous Welch t-test via `kind: "continuous"`), the Fisher's-exact fallback (asserted with `expect.fisher_used`), RCA, and trade-offs. RCA and trade-offs are graded beyond section-presence: the RCA hypothesis matrix must cover at least four of the five required categories, and the trade-offs composite metric must contain an actual formula.

## The loop
`ERROR_ANALYSIS.md` is the ledger. Each cycle: run the suite, find the single biggest failure mode, change one thing (usually a prompt line), re-run, and record whether the number moved. One change at a time keeps the effect attributable.

## CI
`.github/workflows/evals.yml` runs the deterministic grader unit tests on every push (free, no key). The full live eval runs on a weekly schedule and on manual dispatch, with the API key from repository secrets, and uploads the result file as a build artifact.
