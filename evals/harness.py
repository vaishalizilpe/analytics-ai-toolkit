"""Run one eval case through the real app module and return its output.

This calls the same functions the Streamlit app calls, so an eval measures the
production path, not a copy of it. For the A/B module it first computes the
deterministic stats (ground truth) with run_proportion_test, then asks the model
to interpret them, so graders can check the interpretation against known-correct
numbers.
"""
from ab_test_interpreter.stats import run_proportion_test
from ab_test_interpreter.interpreter import interpret_results
from root_cause_analysis.rca import analyze_metric_movement
from metric_tradeoffs.tradeoffs import analyze_tradeoffs


def run_case(case):
    """Return (output_text, context). context carries ground truth for graders."""
    module = case["module"]
    inp = case["input"]

    if module == "ab_test":
        result = run_proportion_test(
            inp["control_conversions"], inp["control_n"],
            inp["treatment_conversions"], inp["treatment_n"],
        )
        output = interpret_results(result, inp["metric_name"], inp["experiment_context"])
        return output, {"result": result}

    if module == "rca":
        output = analyze_metric_movement(
            inp["metric_name"], inp["movement_direction"], inp["magnitude"],
            inp["time_period"], inp["product_context"],
            inp.get("known_events", ""), inp.get("affected_segments", []),
        )
        return output, {}

    if module == "tradeoffs":
        output = analyze_tradeoffs(
            inp["primary_metric"], inp["change_type"], inp["change_description"],
            inp["product_context"], inp["business_goal"], inp.get("secondary_metrics", ""),
        )
        return output, {}

    raise ValueError(f"unknown module: {module}")
