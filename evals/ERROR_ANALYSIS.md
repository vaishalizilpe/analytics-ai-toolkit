# Error Analysis Loop

The improvement ledger for the toolkit's LLM outputs. Same discipline as a model error-analysis loop: measure on a fixed set, find the single biggest failure mode, change ONE thing, re-run, record whether it moved. One change per cycle so the effect is attributable.

## How a cycle works
1. Run `python -m evals.run_evals --judge` to score the current build and write a dated file to `evals/results/`.
2. Read the "top failure modes" summary. Pick the ONE bucket costing the most passes.
3. Change one thing: a prompt line in `shared/prompts.py`, a section instruction in the module, or a grader if the check itself is wrong.
4. Re-run. Keep the change if the pass rate rose, revert if it did not.
5. Log the cycle below.

## Ledger
| Date | Det. pass rate | Judge (corr/faith/act) | Biggest failure mode | ONE change made | Result next run |
|---|---|---|---|---|---|
| pending | not yet run | not yet run | identify on first live run | none yet | Blocked on a valid `ANTHROPIC_API_KEY`. Set the key, run `python -m evals.run_evals --judge`, then fill this row and start the loop. |

> This loop has not produced a baseline number yet. The graders and harness are unit-tested (`tests/test_evals_graders.py`), but a real pass rate requires one live run against the model, which needs a working API key. Until then this is a wired-up loop awaiting its first measurement, not a measured one.
