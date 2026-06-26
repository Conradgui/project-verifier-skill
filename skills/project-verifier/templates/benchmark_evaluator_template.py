#!/usr/bin/env python3
"""
Evidence-backed benchmark evaluator template.

This evaluator intentionally avoids default high scores. A metric receives a
numeric score only when the runner output contains evidence for that metric.
Missing evidence is reported as not measured instead of being treated as proof.
"""

import argparse
import json
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


def metric_result(score=None, confidence="not_measured", evidence=None, not_measured_reason=""):
    return {
        "score": score,
        "confidence": confidence,
        "evidence": evidence or [],
        "not_measured_reason": not_measured_reason,
    }


def score_display(result):
    return "N/A" if result["score"] is None else str(result["score"])


def evidence_display(result):
    if result["evidence"]:
        return "<br>".join(result["evidence"])
    return f"Not measured: {result['not_measured_reason']}"


class BenchmarkEvaluator:
    def __init__(self, tool_output_path, baseline_output_path):
        self.tool_output_path = tool_output_path
        self.baseline_output_path = baseline_output_path
        self.scores = {
            "tool": {metric: metric_result() for metric in METRICS},
            "baseline": {metric: metric_result() for metric in METRICS},
        }
        self.tool_data = {}
        self.baseline_data = {}

    def load_data(self):
        self.tool_data = self._load_json(self.tool_output_path, "tool")
        self.baseline_data = self._load_json(self.baseline_output_path, "baseline")

    def _load_json(self, path, runner_type):
        try:
            with open(path, "r", encoding="utf-8") as file:
                payload = json.load(file)
            payload.setdefault("runner_type", runner_type)
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
        self.scores["tool"] = self._evaluate_runner(self.tool_data, self.baseline_data)
        self.scores["baseline"] = self._evaluate_runner(self.baseline_data, self.tool_data)

    def _evaluate_runner(self, data, comparison_data):
        return {
            "completeness": self._score_completeness(data),
            "auditability": self._score_auditability(data),
            "stability": self._score_stability(data),
            "control": self._score_control(data),
            "cost_efficiency": self._score_cost_efficiency(data, comparison_data),
            "latency": self._score_latency(data, comparison_data),
            "ux": self._score_ux(data),
        }

    def _score_completeness(self, data):
        assertions = data.get("assertions", [])
        artifacts = data.get("artifacts_created", [])
        output = data.get("output") or data.get("response") or ""
        if data.get("exit_code") != 0:
            return metric_result(
                2,
                "high",
                [f"Runner exited with code {data.get('exit_code')}.", *self._error_evidence(data)],
            )
        if assertions:
            passed = sum(1 for item in assertions if item.get("passed") is True)
            total = len(assertions)
            score = round((passed / total) * 10)
            return metric_result(
                score,
                "high",
                [f"{passed}/{total} task assertions passed."],
            )
        if artifacts or len(str(output)) > 20:
            return metric_result(
                7,
                "medium",
                ["Runner completed and produced output, but no task assertions were supplied."],
            )
        return metric_result(
            None,
            "not_measured",
            not_measured_reason="No assertions, artifacts, or substantial output were supplied.",
        )

    def _score_auditability(self, data):
        evidence = []
        if data.get("logs_created") is True:
            evidence.append("Runner reported logs_created=true.")
        log_paths = data.get("log_paths") or data.get("logs") or []
        if log_paths:
            evidence.append(f"Runner reported {len(log_paths)} log path(s).")
        trace = data.get("trace") or data.get("steps")
        if trace:
            evidence.append("Runner reported step trace data.")
        if not evidence:
            return metric_result(
                None,
                "not_measured",
                not_measured_reason="No logs, trace data, or audit artifacts were reported.",
            )
        score = 10 if len(evidence) >= 2 else 7
        return metric_result(score, "medium", evidence)

    def _score_stability(self, data):
        errors = data.get("errors") or []
        if data.get("exit_code") == 0 and not errors:
            return metric_result(10, "high", ["Runner exited successfully with no recorded errors."])
        if data.get("exit_code") == 0 and errors:
            return metric_result(6, "medium", ["Runner exited successfully but recorded errors."])
        return metric_result(
            2,
            "high",
            [f"Runner failed with exit_code={data.get('exit_code')}.", *self._error_evidence(data)],
        )

    def _score_control(self, data):
        evidence = []
        for field in ("control_evidence", "safety_evidence", "security_boundaries"):
            values = data.get(field) or []
            if isinstance(values, str):
                values = [values]
            evidence.extend(str(value) for value in values if value)
        tagged_assertions = [
            item
            for item in data.get("assertions", [])
            if item.get("passed") is True
            and any(tag in item.get("tags", []) for tag in ("safety", "control", "security"))
        ]
        evidence.extend(item.get("text", "Safety/control assertion passed.") for item in tagged_assertions)
        if not evidence:
            return metric_result(
                None,
                "not_measured",
                not_measured_reason="No safety/control assertions or boundary evidence were supplied.",
            )
        score = 10 if len(evidence) >= 2 else 7
        return metric_result(score, "medium", evidence)

    def _score_cost_efficiency(self, data, comparison_data):
        tokens = data.get("token_count")
        comparison_tokens = comparison_data.get("token_count")
        if not tokens or not comparison_tokens:
            return metric_result(
                None,
                "not_measured",
                not_measured_reason="Both runners must report non-zero token_count.",
            )
        ratio = tokens / comparison_tokens
        if ratio <= 0.8:
            score = 10
        elif ratio <= 1.2:
            score = 8
        elif ratio <= 1.8:
            score = 5
        else:
            score = 2
        return metric_result(score, "high", [f"Token ratio vs comparison runner: {ratio:.2f}."])

    def _score_latency(self, data, comparison_data):
        duration = data.get("duration_seconds", data.get("duration"))
        comparison_duration = comparison_data.get("duration_seconds", comparison_data.get("duration"))
        if not duration or not comparison_duration:
            return metric_result(
                None,
                "not_measured",
                not_measured_reason="Both runners must report non-zero duration_seconds.",
            )
        ratio = duration / comparison_duration
        if ratio <= 0.8:
            score = 10
        elif ratio <= 1.2:
            score = 8
        elif ratio <= 1.8:
            score = 5
        else:
            score = 2
        return metric_result(score, "high", [f"Latency ratio vs comparison runner: {ratio:.2f}."])

    def _score_ux(self, data):
        evidence = []
        for field in ("diagnostics", "user_messages", "failure_stage", "output_schema"):
            value = data.get(field)
            if value:
                evidence.append(f"Runner reported {field}.")
        tagged_assertions = [
            item
            for item in data.get("assertions", [])
            if item.get("passed") is True and any(tag in item.get("tags", []) for tag in ("ux", "diagnostics"))
        ]
        evidence.extend(item.get("text", "UX/diagnostics assertion passed.") for item in tagged_assertions)
        if not evidence:
            return metric_result(
                None,
                "not_measured",
                not_measured_reason="No diagnostics, user-facing messages, or UX assertions were supplied.",
            )
        score = 10 if len(evidence) >= 2 else 7
        return metric_result(score, "medium", evidence)

    def _error_evidence(self, data):
        errors = data.get("errors") or []
        return [f"Error: {error}" for error in errors[:3]]

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
                "| **{label}** | {tool_score} | {baseline_score} | Tool: {tool_evidence}<br>Baseline: {base_evidence} |".format(
                    label=METRIC_LABELS[metric],
                    tool_score=score_display(tool_result),
                    baseline_score=score_display(baseline_result),
                    tool_evidence=evidence_display(tool_result),
                    base_evidence=evidence_display(baseline_result),
                )
            )
            if tool_result["score"] is None or baseline_result["score"] is None:
                not_measured.append(metric)
            else:
                measured.append(metric)

        report_content = """# Benchmark Comparison Report
Generated: {timestamp}

## Performance Overview

| Metric Dimension | Tool Score (0-10) | Baseline Score (0-10) | Evidence / Measurement Boundary |
|---|:---:|:---:|---|
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
        output_dir = os.path.dirname(output_html_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        tool_scores = [self.scores["tool"][metric]["score"] for metric in METRICS]
        baseline_scores = [self.scores["baseline"][metric]["score"] for metric in METRICS]

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
            labels: {json.dumps([METRIC_LABELS[metric] for metric in METRICS])},
            datasets: [{{
                label: 'Tool Runner',
                data: {json.dumps(tool_scores)},
                fill: true,
                backgroundColor: 'rgba(37, 99, 235, 0.12)',
                borderColor: 'rgb(37, 99, 235)',
                pointBackgroundColor: 'rgb(37, 99, 235)',
                borderWidth: 2
            }}, {{
                label: 'Baseline Runner',
                data: {json.dumps(baseline_scores)},
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


def main():
    parser = argparse.ArgumentParser(description="Evaluate Tool output against Baseline output.")
    parser.add_argument("--tool-output", required=True, help="Path to tool output JSON file")
    parser.add_argument("--baseline-output", required=True, help="Path to baseline output JSON file")
    parser.add_argument("--report", required=True, help="Path to output markdown report file")
    parser.add_argument("--html-report", required=False, help="Path to output HTML radar dashboard file")
    args = parser.parse_args()

    evaluator = BenchmarkEvaluator(args.tool_output, args.baseline_output)
    evaluator.load_data()
    evaluator.evaluate()
    evaluator.generate_report(args.report)
    if args.html_report:
        evaluator.generate_html_dashboard(args.html_report)


if __name__ == "__main__":
    main()
