"""Eval loop for the Analytics AI Toolkit.

Generates outputs from the live app modules, grades them deterministically (and
optionally with an LLM judge), writes a timestamped result file, prints an
error-analysis summary, and exits non-zero if the deterministic pass rate falls
below THRESHOLD so it can gate CI.

Usage:
  python -m evals.run_evals            # deterministic graders only
  python -m evals.run_evals --judge    # also run the LLM-as-judge (costs API calls)

Both modes call each app module once to produce the output being graded, so an
ANTHROPIC_API_KEY (or whichever LLM_PROVIDER is configured) must be set.
"""
import argparse
import datetime
import json
import pathlib
import statistics
import sys
from collections import Counter

from evals.harness import run_case
from evals.graders import deterministic_grade, llm_judge

THRESHOLD = 0.80
ROOT = pathlib.Path(__file__).resolve().parent


def load_cases():
    with open(ROOT / "dataset.jsonl") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", action="store_true",
                    help="also run the LLM-as-judge scorer (costs API calls)")
    args = ap.parse_args()

    cases = load_cases()
    rows = []
    for c in cases:
        output, ctx = run_case(c)
        det = deterministic_grade(c, output, ctx)
        row = {"id": c["id"], "module": c["module"], "det_fails": det, "det_pass": not det}
        if args.judge:
            j = llm_judge(c, output, ctx)
            row.update({k: j.get(k, 0) for k in ("correctness", "faithfulness", "actionability")})
            row["judge_tags"] = j.get("failure_tags", [])
        rows.append(row)
        flag = "PASS" if row["det_pass"] else "FAIL"
        detail = "" if row["det_pass"] else "  <- " + "; ".join(det)
        print(f"  [{flag}] {c['id']:<26}{detail}")

    det_rate = sum(r["det_pass"] for r in rows) / len(rows)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    out = {"timestamp": stamp, "n": len(rows), "det_pass_rate": round(det_rate, 3), "results": rows}
    if args.judge:
        for k in ("correctness", "faithfulness", "actionability"):
            out[f"avg_{k}"] = round(statistics.mean(r[k] for r in rows), 2)

    (ROOT / "results").mkdir(exist_ok=True)
    result_path = ROOT / "results" / f"evals_{stamp}.json"
    with open(result_path, "w") as f:
        json.dump(out, f, indent=2)

    # Error analysis: which failure modes dominate this run.
    tags = Counter()
    for r in rows:
        tags.update(r["det_fails"])
        tags.update(r.get("judge_tags", []))

    print(f"\ndeterministic pass rate: {det_rate:.0%} "
          f"({sum(r['det_pass'] for r in rows)}/{len(rows)})")
    if args.judge:
        print("avg correctness / faithfulness / actionability: "
              + " / ".join(str(out[f'avg_{k}']) for k in ("correctness", "faithfulness", "actionability")))
    if tags:
        print("top failure modes:")
        for tag, n in tags.most_common(6):
            print(f"  {n:>2}x  {tag}")
    print(f"results -> evals/results/{result_path.name}")

    sys.exit(0 if det_rate >= THRESHOLD else 1)


if __name__ == "__main__":
    main()
