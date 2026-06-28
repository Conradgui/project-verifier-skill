#!/usr/bin/env python3
"""
Evidence-backed benchmark evaluator template.

This evaluator intentionally avoids default scores. A metric receives a numeric
score only when the task definition contains an approved rubric and the runner
output contains the required evidence. Missing evidence is reported as not
measured instead of being treated as proof.
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime


METRICS = [
    "completeness",
    "auditability",
    "stability",
    "control",
    "cost_efficiency",
    "latency",
    "ux",
]

METRIC_LABELS = {
    "completeness": "Completeness",
    "auditability": "Auditability",
    "stability": "Stability & Accuracy",
    "control": "Control & Safety",
    "cost_efficiency": "Cost Efficiency",
    "latency": "Latency",
    "ux": "UX & Diagnostics",
}


def metric_result(
    score=None,
    confidence="not_measured",
    evidence=None,
    not_measured_reason="",
    raw_value=None,
    threshold_met=None,
):
    return {
        "score": score,
        "confidence": confidence,
        "evidence": evidence or [],
        "not_measured_reason": not_measured_reason,
        "raw_value": raw_value,
        "threshold_met": threshold_met,
    }


def score_display(result):
    return "N/A" if result["score"] is None else str(result["score"])


def evidence_display(result):
    if result["evidence"]:
        return "<br>".join(result["evidence"])
    return f"Not measured: {result['not_measured_reason']}"


def raw_display(result):
    value = result.get("raw_value")
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def threshold_display(result):
    value = result.get("threshold_met")
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "N/A"


def json_for_script(value):
    return (
        json.dumps(value)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


class BenchmarkEvaluator:
    def __init__(self, tool_output_path, baseline_output_path, task_definition_path=None):
        self.tool_output_path = tool_output_path
        self.baseline_output_path = baseline_output_path
        self.task_definition_path = task_definition_path
        self.scores = {
            "tool": {metric: metric_result() for metric in METRICS},
            "baseline": {metric: metric_result() for metric in METRICS},
        }
        self.tool_data = {}
        self.baseline_data = {}
        self.task_definition = {}
        self.tool_label = "Tool"
        self.baseline_label = "Baseline"
        self.validation_errors = []

    def load_data(self):
        self.tool_data = self._load_json(self.tool_output_path, "tool")
        self.baseline_data = self._load_json(self.baseline_output_path, "baseline")
        if self.task_definition_path:
            self.task_definition = self._load_json(self.task_definition_path, "task")
        else:
            self.task_definition = {}
        self.tool_label = self.task_definition.get("tool_label", "Tool")
        baseline = self.task_definition.get("baseline") or {}
        if not isinstance(baseline, dict):
            baseline = {}
        self.baseline_label = baseline.get("label", self.task_definition.get("baseline_label", "Baseline"))

    def _load_json(self, path, runner_type):
        try:
            with open(path, "r", encoding="utf-8") as file:
                payload = json.load(file)
            payload.setdefault("status", "unknown")
            payload.setdefault("errors", [])
            payload.setdefault("assertions", [])
            payload.setdefault("artifacts_created", [])
            return payload
        except Exception as exc:
            print(f"Error loading {runner_type} output: {exc}", file=sys.stderr)
            return {
                "runner_type": runner_type,
                "load_error": str(exc),
                "exit_code": 1,
                "errors": [str(exc)],
                "assertions": [],
                "artifacts_created": [],
            }

    def evaluate(self):
        self.validation_errors = self._validate_comparison()
        if self.validation_errors:
            reason = "Comparison validation failed: " + "; ".join(self.validation_errors)
            self.scores = {
                role: {metric: metric_result(not_measured_reason=reason) for metric in METRICS}
                for role in ("tool", "baseline")
            }
            return
        self.scores["tool"] = self._evaluate_runner(self.tool_data, self.baseline_data)
        self.scores["baseline"] = self._evaluate_runner(self.baseline_data, self.tool_data)

    def _validate_comparison(self):
        errors = []
        task_id = self.task_definition.get("task_id")
        tool_task_id = self.tool_data.get("task_id")
        baseline_task_id = self.baseline_data.get("task_id")
        if not task_id or task_id != tool_task_id or task_id != baseline_task_id:
            errors.append(
                f"task_id mismatch (task={task_id!r}, tool={tool_task_id!r}, baseline={baseline_task_id!r})"
            )
        if self.tool_data.get("runner_type") != "tool":
            errors.append("tool output must declare runner_type=tool")
        if self.baseline_data.get("runner_type") != "baseline":
            errors.append("baseline output must declare runner_type=baseline")
        for role, data in (("tool", self.tool_data), ("baseline", self.baseline_data)):
            if data.get("status") != "completed":
                errors.append(f"{role} status is {data.get('status', 'unknown')}, not completed")
            if data.get("execution_mode") != "full":
                errors.append(
                    f"{role} execution_mode is {data.get('execution_mode', 'missing')}, not full"
                )
            if data.get("exit_code") != 0:
                errors.append(f"{role} exit_code is {data.get('exit_code', 'missing')}, not 0")
        return errors

    def _evaluate_runner(self, data, comparison_data):
        if data.get("status") != "completed":
            status = data.get("status", "unknown")
            return {
                metric: metric_result(
                    not_measured_reason=(
                        f"Runner status is {status}; only a completed full run can be scored."
                    )
                )
                for metric in METRICS
            }

        definitions = {
            item.get("id"): item
            for item in self.task_definition.get("metrics", [])
            if isinstance(item, dict) and item.get("id")
        }
        return {
            metric: self._evaluate_metric(metric, definitions.get(metric), data, comparison_data)
            for metric in METRICS
        }

    def _evaluate_metric(self, metric, definition, data, comparison_data):
        if not definition:
            return metric_result(
                not_measured_reason="No pre-approved metric rubric was supplied in the task definition."
            )

        required = (
            "measurement_method",
            "success_threshold",
            "score_mapping",
            "minimum_samples",
            "evidence_fields",
        )
        missing = [field for field in required if field not in definition]
        if missing:
            return metric_result(
                not_measured_reason=f"Metric rubric is incomplete; missing: {', '.join(missing)}."
            )

        threshold = definition.get("success_threshold")
        if (
            not isinstance(threshold, dict)
            or threshold.get("operator") not in (">=", "<=", ">", "<", "==")
            or not self._finite_number(threshold.get("value"))
        ):
            return metric_result(
                not_measured_reason=(
                    "success_threshold must contain a numeric value and one of: >=, <=, >, <, ==."
                )
            )
        minimum_samples = self._positive_int(definition.get("minimum_samples"))
        if minimum_samples is None:
            return metric_result(not_measured_reason="minimum_samples must be a positive integer.")
        evidence_fields = definition.get("evidence_fields")
        if not isinstance(evidence_fields, list) or not evidence_fields:
            return metric_result(not_measured_reason="evidence_fields must be a non-empty list.")
        if not all(isinstance(field, str) and field.strip() for field in evidence_fields):
            return metric_result(
                not_measured_reason="evidence_fields must contain only non-empty field names."
            )

        mapping_error = self._score_mapping_error(definition)
        if mapping_error:
            return metric_result(not_measured_reason=mapping_error)

        absent_evidence = [field for field in evidence_fields if not data.get(field)]
        if absent_evidence:
            return metric_result(
                not_measured_reason=(
                    "Runner output is missing required evidence fields: "
                    + ", ".join(absent_evidence)
                    + "."
                )
            )

        method = definition.get("measurement_method")
        if method == "assertion_rate":
            return self._evaluate_assertion_rate(metric, definition, data)
        if method == "repeated_success_rate":
            return self._evaluate_repeated_success(definition, data)
        if method == "numeric_ratio":
            return self._evaluate_numeric_ratio(definition, data, comparison_data)
        if method == "llm_judge_score":
            return self._evaluate_llm_judge(metric, definition, data)
        return metric_result(
            not_measured_reason=f"Unsupported measurement_method: {method}."
        )

    def _evaluate_assertion_rate(self, metric, definition, data):
        configured_tags = definition.get("assertion_tags") or [metric]
        if not isinstance(configured_tags, list) or not all(
            isinstance(tag, str) and tag for tag in configured_tags
        ):
            return metric_result(
                not_measured_reason="assertion_tags must contain only non-empty strings."
            )
        tags = set(configured_tags)
        if not isinstance(data.get("assertions"), list):
            return metric_result(not_measured_reason="assertions must be a list of evidence objects.")
        assertions = [
            item
            for item in data.get("assertions", [])
            if isinstance(item, dict)
            and isinstance(item.get("tags"), list)
            and tags.intersection(item.get("tags", []))
            and item.get("text")
            and isinstance(item.get("passed"), bool)
            and item.get("evidence")
        ]
        minimum = int(definition.get("minimum_samples", 1))
        if len(assertions) < minimum:
            return metric_result(
                not_measured_reason=(
                    f"Only {len(assertions)} evidenced assertion(s); minimum_samples={minimum}."
                )
            )
        passed = sum(1 for item in assertions if item["passed"])
        rate = passed / len(assertions)
        mapping = definition.get("score_mapping")
        if mapping != "pass_rate_x_10":
            return metric_result(
                not_measured_reason="Unsupported assertion score_mapping; no default mapping is allowed.",
                raw_value=rate,
            )
        return metric_result(
            score=round(rate * 10),
            confidence=self._confidence(len(assertions), minimum),
            evidence=[
                f"{passed}/{len(assertions)} rubric-matched assertions passed.",
                *[f"{item['text']}: {item['evidence']}" for item in assertions],
            ],
            raw_value=rate,
            threshold_met=self._threshold_met(definition, rate),
        )

    def _evaluate_repeated_success(self, definition, data):
        if not isinstance(data.get("runs"), list):
            return metric_result(not_measured_reason="runs must be a list of execution result objects.")
        runs = [item for item in data["runs"] if isinstance(item, dict)]
        minimum = int(definition.get("minimum_samples", 1))
        if len(runs) < minimum:
            return metric_result(
                not_measured_reason=f"Only {len(runs)} run(s); minimum_samples={minimum}."
            )
        successes = sum(
            1
            for run in runs
            if run.get("exit_code") == 0 and not (run.get("errors") or [])
        )
        rate = successes / len(runs)
        if definition.get("score_mapping") != "success_rate_x_10":
            return metric_result(
                not_measured_reason="Unsupported stability score_mapping; no default mapping is allowed.",
                raw_value=rate,
            )
        return metric_result(
            score=round(rate * 10),
            confidence=self._confidence(len(runs), minimum),
            evidence=[f"{successes}/{len(runs)} repeated runs completed without recorded errors."],
            raw_value=rate,
            threshold_met=self._threshold_met(definition, rate),
        )

    def _evaluate_numeric_ratio(self, definition, data, comparison_data):
        field = definition.get("source_field")
        value = data.get(field) if field else None
        comparison = comparison_data.get(field) if field else None
        minimum = int(definition.get("minimum_samples", 1))
        samples = self._positive_int(data.get("sample_count", 1))
        comparison_samples = self._positive_int(comparison_data.get("sample_count", 1))
        if samples is None or comparison_samples is None:
            return metric_result(
                not_measured_reason="sample_count must be a positive integer for both runners."
            )
        if samples < minimum or comparison_samples < minimum:
            return metric_result(
                not_measured_reason=(
                    f"Numeric comparison requires minimum_samples={minimum}; "
                    f"received {samples} and {comparison_samples}."
                )
            )
        if not self._finite_number(value) or not self._finite_number(comparison) or comparison == 0:
            return metric_result(
                not_measured_reason=(
                    f"Both runners must provide finite numeric comparison data for {field}, "
                    "and the baseline value must be non-zero."
                )
            )
        ratio = value / comparison
        mapping = definition.get("score_mapping")
        if not isinstance(mapping, list):
            return metric_result(
                not_measured_reason="numeric_ratio requires a pre-approved score_mapping list.",
                raw_value=ratio,
            )
        score = None
        for rule in mapping:
            minimum_ratio = rule.get("min_ratio", float("-inf"))
            maximum_ratio = rule.get("max_ratio", float("inf"))
            if minimum_ratio <= ratio <= maximum_ratio:
                score = rule.get("score")
                break
        if not isinstance(score, (int, float)):
            return metric_result(
                not_measured_reason="The approved ratio rubric did not cover the observed value.",
                raw_value=ratio,
            )
        return metric_result(
            score=score,
            confidence=self._confidence(min(samples, comparison_samples), minimum),
            evidence=[f"Approved field {field}: observed ratio {ratio:.3f}."],
            raw_value=ratio,
            threshold_met=self._threshold_met(definition, ratio),
        )

    def _evaluate_llm_judge(self, metric, definition, data):
        minimum = int(definition.get("minimum_samples", 1))
        if not isinstance(data.get("judge_results"), list):
            return metric_result(
                not_measured_reason="judge_results must be a list of traceable judge result objects."
            )
        valid_results = []
        for item in data["judge_results"]:
            if not isinstance(item, dict):
                continue
            score = item.get("score")
            if item.get("metric_id") != metric:
                continue
            if not self._valid_score(score):
                continue
            if not all(item.get(field) for field in ("evidence", "judge_prompt", "model", "confidence")):
                continue
            if item.get("confidence") not in ("low", "medium", "high"):
                continue
            valid_results.append(item)
        if len(valid_results) < minimum:
            return metric_result(
                not_measured_reason=(
                    f"Only {len(valid_results)} traceable judge result(s); minimum_samples={minimum}."
                )
            )
        score = round(sum(item["score"] for item in valid_results) / len(valid_results), 2)
        confidence_order = {"low": 0, "medium": 1, "high": 2}
        confidence = min(
            (item["confidence"] for item in valid_results),
            key=lambda value: confidence_order.get(value, -1),
        )
        evidence = []
        for item in valid_results:
            evidence.append(
                "Judge model={model}; confidence={confidence}; evidence={evidence}; prompt={prompt}".format(
                    model=item["model"],
                    confidence=item["confidence"],
                    evidence=item["evidence"],
                    prompt=item["judge_prompt"],
                )
            )
        return metric_result(
            score=score,
            confidence=confidence if confidence in confidence_order else "low",
            evidence=evidence,
            raw_value=score,
            threshold_met=self._threshold_met(definition, score),
        )

    def _score_mapping_error(self, definition):
        method = definition.get("measurement_method")
        mapping = definition.get("score_mapping")
        expected = {
            "assertion_rate": "pass_rate_x_10",
            "repeated_success_rate": "success_rate_x_10",
            "llm_judge_score": "judge_score_0_to_10",
        }
        if method in expected:
            if mapping != expected[method]:
                return f"{method} requires score_mapping={expected[method]}."
            return ""
        if method != "numeric_ratio":
            return ""
        if not isinstance(mapping, list) or not mapping:
            return "numeric_ratio requires a non-empty score_mapping list."
        previous_max = float("-inf")
        fallback_seen = False
        for index, rule in enumerate(mapping):
            if not isinstance(rule, dict):
                return "Every numeric ratio score rule must be an object."
            if not self._valid_score(rule.get("score")):
                return "Every numeric ratio score must be between 0 and 10."
            has_min = "min_ratio" in rule
            has_max = "max_ratio" in rule
            if not has_min and not has_max:
                if index != len(mapping) - 1:
                    return "An unbounded fallback score rule must be last."
                fallback_seen = True
                continue
            for field in ("min_ratio", "max_ratio"):
                if field in rule and not self._finite_number(rule[field]):
                    return f"{field} must be a finite number."
            minimum = rule.get("min_ratio", previous_max)
            maximum = rule.get("max_ratio", float("inf"))
            if minimum > maximum:
                return "A numeric ratio rule has min_ratio greater than max_ratio."
            if not has_min and has_max and maximum <= previous_max:
                return "max_ratio thresholds must be strictly increasing."
            previous_max = maximum
        if fallback_seen and len(mapping) == 1:
            return "A numeric ratio rubric needs at least one bounded rule before its fallback."
        return ""

    def _positive_int(self, value):
        if isinstance(value, bool):
            return None
        if isinstance(value, float) and not value.is_integer():
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _finite_number(self, value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    def _valid_score(self, value):
        return self._finite_number(value) and 0 <= value <= 10

    def _confidence(self, samples, minimum):
        if samples >= minimum * 3:
            return "high"
        if samples >= minimum * 2:
            return "medium"
        return "low"

    def _threshold_met(self, definition, raw_value):
        threshold = definition["success_threshold"]
        expected = threshold["value"]
        operator = threshold["operator"]
        if operator == ">=":
            return raw_value >= expected
        if operator == "<=":
            return raw_value <= expected
        if operator == ">":
            return raw_value > expected
        if operator == "<":
            return raw_value < expected
        return raw_value == expected

    def generate_report(self, output_markdown_path):
        output_dir = os.path.dirname(output_markdown_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        rows = []
        measured = []
        not_measured = []
        for metric in METRICS:
            tool_result = self.scores["tool"][metric]
            baseline_result = self.scores["baseline"][metric]
            rows.append(
                "| **{label}** | {tool_raw} | {base_raw} | {tool_score} | {baseline_score} | {tool_threshold} | {base_threshold} | {tool_label}: {tool_evidence}<br>{baseline_label}: {base_evidence} |".format(
                    label=METRIC_LABELS[metric],
                    tool_raw=raw_display(tool_result),
                    base_raw=raw_display(baseline_result),
                    tool_score=score_display(tool_result),
                    baseline_score=score_display(baseline_result),
                    tool_threshold=threshold_display(tool_result),
                    base_threshold=threshold_display(baseline_result),
                    tool_evidence=evidence_display(tool_result),
                    base_evidence=evidence_display(baseline_result),
                    tool_label=self.tool_label,
                    baseline_label=self.baseline_label,
                )
            )
            if tool_result["score"] is None or baseline_result["score"] is None:
                not_measured.append(metric)
            else:
                measured.append(metric)

        report_content = """# Benchmark Comparison Report
Generated: {timestamp}

## Performance Overview

| Metric Dimension | Tool Raw Value | Baseline Raw Value | Tool Score (0-10) | Baseline Score (0-10) | Tool Threshold Met | Baseline Threshold Met | Evidence / Measurement Boundary |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
{rows}

## Evidence-Backed Claims
{measured_claims}

## Not Yet Proven
{not_measured_claims}
""".format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            rows="\n".join(rows),
            measured_claims=self._claim_lines(measured, "Measured with runner-provided evidence."),
            not_measured_claims=self._claim_lines(not_measured, "Do not claim this dimension without additional evidence."),
        )
        with open(output_markdown_path, "w", encoding="utf-8") as file:
            file.write(report_content)
        print(f"Report generated successfully: {output_markdown_path}")

    def _claim_lines(self, metrics, suffix):
        if not metrics:
            return "- None."
        return "\n".join(f"- {METRIC_LABELS[metric]}: {suffix}" for metric in metrics)

    def generate_html_dashboard(self, output_html_path):
        comparable_metrics = [
            metric
            for metric in METRICS
            if isinstance(self.scores["tool"][metric]["score"], (int, float))
            and isinstance(self.scores["baseline"][metric]["score"], (int, float))
        ]
        if len(comparable_metrics) < 3:
            print(
                "HTML dashboard not generated: at least three rubric-backed comparable metrics are required."
            )
            return False

        output_dir = os.path.dirname(output_html_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        tool_scores = [self.scores["tool"][metric]["score"] for metric in comparable_metrics]
        baseline_scores = [self.scores["baseline"][metric]["score"] for metric in comparable_metrics]

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>项目性能评估雷达图 Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
            padding: 32px;
            margin: 0;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 32px;
        }}
        h1 {{
            margin-top: 0;
            font-size: 24px;
            font-weight: 700;
            color: #1e293b;
            text-align: center;
        }}
        .subtitle {{
            text-align: center;
            color: #64748b;
            font-size: 14px;
            margin-bottom: 24px;
        }}
        .chart-box {{
            width: 480px;
            height: 480px;
            margin: 0 auto 24px auto;
        }}
        .note {{
            color: #475569;
            font-size: 14px;
            line-height: 1.5;
        }}
    </style>
</head>
<body>
<div class="container">
    <h1>项目性能验证对比 Dashboard</h1>
    <div class="subtitle">运行时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
    <div class="chart-box">
        <canvas id="radarChart"></canvas>
    </div>
    <p class="note">说明：图中空缺维度表示没有足够证据，不能作为优势主张使用。完整证据边界以 Markdown 报告为准。</p>
</div>
<script>
    const ctx = document.getElementById('radarChart').getContext('2d');
    new Chart(ctx, {{
        type: 'radar',
        data: {{
            labels: {json_for_script([METRIC_LABELS[metric] for metric in comparable_metrics])},
            datasets: [{{
                label: {json_for_script(self.tool_label)},
                data: {json_for_script(tool_scores)},
                fill: true,
                backgroundColor: 'rgba(37, 99, 235, 0.12)',
                borderColor: 'rgb(37, 99, 235)',
                pointBackgroundColor: 'rgb(37, 99, 235)',
                borderWidth: 2
            }}, {{
                label: {json_for_script(self.baseline_label)},
                data: {json_for_script(baseline_scores)},
                fill: true,
                backgroundColor: 'rgba(220, 38, 38, 0.12)',
                borderColor: 'rgb(220, 38, 38)',
                pointBackgroundColor: 'rgb(220, 38, 38)',
                borderWidth: 2
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{
                r: {{
                    suggestedMin: 0,
                    suggestedMax: 10,
                    ticks: {{ stepSize: 2 }}
                }}
            }}
        }}
    }});
</script>
</body>
</html>
"""
        with open(output_html_path, "w", encoding="utf-8") as file:
            file.write(html_content)
        print(f"HTML Dashboard generated successfully: {output_html_path}")
        return True


def main():
    parser = argparse.ArgumentParser(description="Evaluate Tool output against Baseline output.")
    parser.add_argument("--tool-output", required=True, help="Path to tool output JSON file")
    parser.add_argument("--baseline-output", required=True, help="Path to baseline output JSON file")
    parser.add_argument(
        "--task-definition",
        required=True,
        help="Path to approved benchmark task JSON with metric rubrics",
    )
    parser.add_argument("--report", required=True, help="Path to output markdown report file")
    parser.add_argument("--html-report", required=False, help="Path to output HTML radar dashboard file")
    args = parser.parse_args()

    evaluator = BenchmarkEvaluator(args.tool_output, args.baseline_output, args.task_definition)
    evaluator.load_data()
    evaluator.evaluate()
    evaluator.generate_report(args.report)
    if args.html_report:
        evaluator.generate_html_dashboard(args.html_report)


if __name__ == "__main__":
    main()
