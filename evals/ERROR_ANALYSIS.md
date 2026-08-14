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
| _seed_ | run to fill | run to fill | to be identified on first run | baseline, no change yet | pending |
