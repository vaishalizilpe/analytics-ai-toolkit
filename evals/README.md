# Evals: measuring and improving the LLM outputs

This toolkit turns analytics inputs into LLM-generated recommendations. LLM output is not predictable, so quality has to be measured, not assumed. This directory is a graded eval suite plus an error-analysis loop that does exactly that.

## What it checks
Each case in `dataset.jsonl` runs through the same functions the app uses, then two layers of grading:

- **Deterministic graders** (`graders.py`, no API, run in CI): structural checks that the required sections are present, and, for A/B tests, faithfulness checks against the deterministic ground-truth stats. Examples: a non-significant result may not be sold as a clean Ship; a Sample Ratio Mismatch must be surfaced; a 0% control rate may not quote a relative-lift number.
- **LLM-as-judge** (optional, costs API calls): scores correctness, faithfulness, and actionability 0-5 against the ground truth. Nondeterministic, so it informs error analysis but is not the pass/fail gate.

## Run it
```bash
python -m evals.run_evals            # deterministic graders only
python -m evals.run_evals --judge    # add the LLM-as-judge (uses your configured LLM_PROVIDER)
```
Results write to `evals/results/evals_<timestamp>.json`. The run exits non-zero if the deterministic pass rate drops below 0.80, so it can gate CI.

## The loop
`ERROR_ANALYSIS.md` is the ledger. Each cycle: run the suite, find the single biggest failure mode, change one thing (usually a prompt line), re-run, and record whether the number moved. One change at a time keeps the effect attributable.

## CI
`.github/workflows/evals.yml` runs the deterministic grader unit tests on every push (free, no key). The full live eval runs on a weekly schedule and on manual dispatch, with the API key from repository secrets, and uploads the result file as a build artifact.
