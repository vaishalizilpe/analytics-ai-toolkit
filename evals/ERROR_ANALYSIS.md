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
| 2026-08-15 | 83% (10/12) | 4.83 / 4.83 / 5.0 | Model drops a required section on a specific input: RCA omits TOP 3 PRIORITIES (rca_conversion_drop), trade-offs omits COMPOSITE METRIC (tradeoffs_pricing), one case each | Baseline, no change | Baseline set |

> First real run recorded 2026-08-15 (run via `env -u ANTHROPIC_API_KEY python -m evals.run_evals --judge`, a stale shell key had been shadowing the .env key). Deterministic pass rate 83% (10/12); LLM-judge averages 4.83 correctness, 4.83 faithfulness, 5.0 actionability. Both failures are the model omitting one required section on a specific input. Next cycle: read the actual header the model emits on the failing RCA case to decide genuine-omission vs grader-too-strict, then fix the right layer.
