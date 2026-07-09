#!/usr/bin/env python3
"""Task-defined, raw-metric-first benchmark evaluator template."""

import argparse
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def positive_int(value):
    if isinstance(value, bool) or (isinstance(value, float) and not value.is_integer()):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def metric_result(
    metric_id,
    label,
    raw_value=None,
    unit=None,
    sample_count=0,
    sample_adequacy="not_measured",
    threshold_met=None,
    evidence=None,
    limitations=None,
    not_measured_reason="",
):
    return {
        "metric_id": metric_id,
        "label": label,
        "raw_value": raw_value,
        "unit": unit,
        "sample_count": sample_count,
        "sample_adequacy": sample_adequacy,
        "threshold_met": threshold_met,
        "evidence": evidence or [],
        "limitations": limitations or [],
        "not_measured_reason": not_measured_reason,
    }


class BenchmarkEvaluator:
    def __init__(self, tool_output_path, baseline_output_path, task_definition_path=None):
        self.tool_output_path = tool_output_path
        self.baseline_output_path = baseline_output_path
        self.task_definition_path = task_definition_path
        self.tool_data = {}
        self.baseline_data = {}
        self.task_definition = {}
        self.tool_label = "Tool"
        self.baseline_label = "Baseline"
        self.validation_errors = []
        self.results = {"tool": {}, "baseline": {}}

    def load_data(self):
        self.tool_data = self._load_json(self.tool_output_path, "tool")
        self.baseline_data = self._load_json(self.baseline_output_path, "baseline")
        self.task_definition = self._load_json(self.task_definition_path, "task") if self.task_definition_path else {}
        self.tool_label = str(self.task_definition.get("tool_label", "Tool"))
        baseline = self.task_definition.get("baseline")
        baseline = baseline if isinstance(baseline, dict) else {}
        self.baseline_label = str(baseline.get("label", self.task_definition.get("baseline_label", "Baseline")))

    def _load_json(self, path, label):
        try:
            with open(path, "r", encoding="utf-8") as file:
                payload = json.load(file)
            if not isinstance(payload, dict):
                raise ValueError("root value must be an object")
            return payload
        except Exception as exc:
            print(f"Error loading {label} JSON: {exc}", file=sys.stderr)
            return {"load_error": str(exc)}

    def evaluate(self):
        definitions = self._metric_definitions()
        self.validation_errors = self._validate_comparison()
        if self.validation_errors:
            reason = "Comparison validation failed: " + "; ".join(self.validation_errors)
            for role in ("tool", "baseline"):
                self.results[role] = {
                    item["id"]: metric_result(item["id"], item["label"], not_measured_reason=reason)
                    for item in definitions
                }
            return self.results
        self.results["tool"] = self._evaluate_runner(self.tool_data, self.baseline_data, definitions)
        self.results["baseline"] = self._evaluate_runner(self.baseline_data, self.tool_data, definitions)
        return self.results

    def _metric_definitions(self):
        definitions = []
        seen = set()
        for item in self.task_definition.get("metrics") or []:
            if not isinstance(item, dict):
                continue
            metric_id = item.get("id")
            if not isinstance(metric_id, str) or not metric_id or metric_id in seen:
                continue
            copied = dict(item)
            copied["label"] = str(item.get("label") or metric_id.replace("_", " ").title())
            definitions.append(copied)
            seen.add(metric_id)
        return definitions

    def _validate_comparison(self):
        errors = []
        task_id = self.task_definition.get("task_id")
        if self.task_definition.get("rubric_approved") is not True:
            errors.append("task definition must declare rubric_approved=true before metrics can be measured")
        if not task_id or task_id != self.tool_data.get("task_id") or task_id != self.baseline_data.get("task_id"):
            errors.append(
                "task_id mismatch (task={!r}, tool={!r}, baseline={!r})".format(
                    task_id, self.tool_data.get("task_id"), self.baseline_data.get("task_id")
                )
            )
        if self.tool_data.get("runner_type") != "tool":
            errors.append("tool output must declare runner_type=tool")
        if self.baseline_data.get("runner_type") != "baseline":
            errors.append("baseline output must declare runner_type=baseline")
        for role, data in (("tool", self.tool_data), ("baseline", self.baseline_data)):
            if data.get("status") != "completed":
                errors.append(f"{role} status is {data.get('status', 'unknown')}, not completed")
            if data.get("execution_mode") != "full":
                errors.append(f"{role} execution_mode is {data.get('execution_mode', 'missing')}, not full")
            if data.get("exit_code") != 0:
                errors.append(f"{role} exit_code is {data.get('exit_code', 'missing')}, not 0")
        return errors

    def _evaluate_runner(self, data, comparison, definitions):
        return {
            definition["id"]: self._evaluate_metric(definition, data, comparison)
            for definition in definitions
        }

    def _evaluate_metric(self, definition, data, comparison):
        metric_id = definition["id"]
        label = definition["label"]
        required = ("measurement_method", "success_threshold", "minimum_samples", "evidence_fields")
        missing = [field for field in required if field not in definition]
        if missing:
            return metric_result(metric_id, label, not_measured_reason="Metric definition is missing: " + ", ".join(missing))

        threshold = definition.get("success_threshold")
        if (
            not isinstance(threshold, dict)
            or threshold.get("operator") not in (">=", "<=", ">", "<", "==")
            or not finite_number(threshold.get("value"))
        ):
            return metric_result(metric_id, label, not_measured_reason="success_threshold is invalid")
        minimum = positive_int(definition.get("minimum_samples"))
        if minimum is None:
            return metric_result(metric_id, label, not_measured_reason="minimum_samples must be a positive integer")
        evidence_fields = definition.get("evidence_fields")
        if not isinstance(evidence_fields, list) or not evidence_fields or not all(
            isinstance(field, str) and field for field in evidence_fields
        ):
            return metric_result(metric_id, label, not_measured_reason="evidence_fields must contain field names")
        absent = [field for field in evidence_fields if field not in data or data[field] in (None, [], "")]
        if absent:
            return metric_result(
                metric_id,
                label,
                not_measured_reason="Runner output is missing evidence fields: " + ", ".join(absent),
            )

        method = definition["measurement_method"]
        if method == "numeric_value":
            measured = self._numeric_value(definition, data, minimum)
        elif method == "numeric_ratio":
            measured = self._numeric_ratio(definition, data, comparison, minimum)
        elif method == "assertion_rate":
            measured = self._assertion_rate(definition, data, minimum)
        elif method == "repeated_success_rate":
            measured = self._repeated_success(definition, data, minimum)
        elif method == "llm_judge_score":
            measured = self._llm_judge(definition, data, minimum)
        else:
            return metric_result(metric_id, label, not_measured_reason=f"Unsupported measurement_method: {method}")

        if measured.get("not_measured_reason"):
            return metric_result(metric_id, label, **measured)
        raw_value = measured["raw_value"]
        return metric_result(
            metric_id,
            label,
            raw_value=raw_value,
            unit=definition.get("unit"),
            sample_count=measured["sample_count"],
            sample_adequacy=self._sample_adequacy(measured["sample_count"], minimum),
            threshold_met=self._threshold_met(threshold, raw_value),
            evidence=measured.get("evidence"),
            limitations=measured.get("limitations"),
        )

    def _numeric_value(self, definition, data, minimum):
        field = definition.get("source_field")
        value = data.get(field) if isinstance(field, str) else None
        samples = positive_int(data.get("sample_count"))
        if not finite_number(value):
            return {"not_measured_reason": f"{field} must be a finite numeric value"}
        if samples is None or samples < minimum:
            return {"not_measured_reason": f"sample_count does not meet minimum_samples={minimum}"}
        return {"raw_value": value, "sample_count": samples, "evidence": [f"{field}={value}"]}

    def _numeric_ratio(self, definition, data, comparison, minimum):
        field = definition.get("source_field")
        value = data.get(field) if isinstance(field, str) else None
        other = comparison.get(field) if isinstance(field, str) else None
        samples = positive_int(data.get("sample_count"))
        other_samples = positive_int(comparison.get("sample_count"))
        if not finite_number(value) or not finite_number(other) or other == 0:
            return {"not_measured_reason": f"Both runners need finite {field}; comparison must be non-zero"}
        if samples is None or other_samples is None or min(samples, other_samples) < minimum:
            return {"not_measured_reason": f"sample_count does not meet minimum_samples={minimum}"}
        ratio = value / other
        return {
            "raw_value": ratio,
            "sample_count": min(samples, other_samples),
            "evidence": [f"{field} ratio={ratio:.6f}; observed={value}; comparison={other}"],
        }

    def _assertion_rate(self, definition, data, minimum):
        tags = definition.get("assertion_tags") or [definition["id"]]
        if not isinstance(data.get("assertions"), list) or not isinstance(tags, list):
            return {"not_measured_reason": "assertions and assertion_tags must be lists"}
        assertions = [
            item
            for item in data["assertions"]
            if isinstance(item, dict)
            and isinstance(item.get("tags"), list)
            and set(tags).intersection(item["tags"])
            and item.get("text")
            and isinstance(item.get("passed"), bool)
            and item.get("evidence")
        ]
        if definition.get("require_evidence_files") is True:
            assertions = [item for item in assertions if self._evidence_file_exists(item["evidence"])]
            if len(assertions) < minimum:
                return {
                    "not_measured_reason":
                        f"Only {len(assertions)} assertions have existing evidence files; minimum_samples={minimum}"
                }
        if len(assertions) < minimum:
            return {"not_measured_reason": f"Only {len(assertions)} evidenced assertions; minimum_samples={minimum}"}
        passed = sum(item["passed"] for item in assertions)
        return {
            "raw_value": passed / len(assertions),
            "sample_count": len(assertions),
            "evidence": [f"{passed}/{len(assertions)} assertions passed"] + [
                f"{item['text']}: {item['evidence']}" for item in assertions
            ],
        }

    def _evidence_file_exists(self, value):
        root_value = self.task_definition.get("evidence_root")
        if not isinstance(root_value, str) or not root_value or not isinstance(value, str) or not value:
            return False
        root = Path(root_value).resolve()
        candidate = Path(value)
        candidate = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return False
        return candidate.is_file()

    def _repeated_success(self, definition, data, minimum):
        if not isinstance(data.get("runs"), list):
            return {"not_measured_reason": "runs must be a list"}
        runs = [item for item in data["runs"] if isinstance(item, dict)]
        if len(runs) < minimum:
            return {"not_measured_reason": f"Only {len(runs)} runs; minimum_samples={minimum}"}
        successes = sum(item.get("exit_code") == 0 and not item.get("errors") for item in runs)
        return {
            "raw_value": successes / len(runs),
            "sample_count": len(runs),
            "evidence": [f"{successes}/{len(runs)} repeated runs succeeded"],
        }

    def _llm_judge(self, definition, data, minimum):
        category = str(definition.get("category", "")).lower()
        if category in {"safety", "security", "leakage", "privacy"}:
            return {"not_measured_reason": "Safety, security, leakage, and privacy cannot rely on LLM Judge alone"}
        if not isinstance(data.get("judge_results"), list):
            return {"not_measured_reason": "judge_results must be a list"}
        valid = []
        for item in data["judge_results"]:
            if not isinstance(item, dict) or item.get("metric_id") != definition["id"]:
                continue
            required = ("score", "evidence", "judge_prompt", "model", "model_version")
            if not all(item.get(field) is not None for field in required):
                continue
            if not finite_number(item["score"]) or not 0 <= item["score"] <= 10:
                continue
            if item.get("blinded") is not True or item.get("randomized_order") is not True:
                continue
            valid.append(item)
        if len(valid) < minimum:
            return {"not_measured_reason": f"Only {len(valid)} blinded judge results; minimum_samples={minimum}"}
        value = sum(item["score"] for item in valid) / len(valid)
        return {
            "raw_value": round(value, 4),
            "sample_count": len(valid),
            "evidence": [
                "model={}; version={}; evidence={}".format(item["model"], item["model_version"], item["evidence"])
                for item in valid
            ],
            "limitations": ["LLM Judge output is subjective evidence, not ground truth."],
        }

    def _sample_adequacy(self, samples, minimum):
        if samples < minimum:
            return "below_minimum"
        if samples == minimum:
            return "meets_minimum"
        return "above_minimum"

    def _threshold_met(self, threshold, value):
        expected = threshold["value"]
        return {
            ">=": value >= expected,
            "<=": value <= expected,
            ">": value > expected,
            "<": value < expected,
            "==": value == expected,
        }[threshold["operator"]]

    def generate_report(self, output_markdown_path):
        output_dir = os.path.dirname(output_markdown_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        header = "| Metric | Tool Raw Value | Baseline Raw Value | Tool Threshold | Baseline Threshold | Tool Samples | Baseline Samples | Evidence / Limitations |"
        divider = "|---|:---:|:---:|:---:|:---:|:---:|:---:|---|"
        rows = []
        measured = []
        unmeasured = []
        for metric_id, tool in self.results["tool"].items():
            baseline = self.results["baseline"][metric_id]
            if tool["raw_value"] is None or baseline["raw_value"] is None:
                unmeasured.append(metric_id)
            else:
                measured.append(metric_id)
            evidence = self._evidence_text(tool, self.tool_label) + "<br>" + self._evidence_text(baseline, self.baseline_label)
            rows.append(
                "| {label} | {tool_raw} | {base_raw} | {tool_threshold} | {base_threshold} | {tool_n} | {base_n} | {evidence} |".format(
                    label=tool["label"], tool_raw=self._display(tool["raw_value"]), base_raw=self._display(baseline["raw_value"]),
                    tool_threshold=self._threshold_display(tool["threshold_met"]), base_threshold=self._threshold_display(baseline["threshold_met"]),
                    tool_n=tool["sample_count"], base_n=baseline["sample_count"], evidence=evidence,
                )
            )
        content = """# Benchmark Comparison Report
Generated: {timestamp}

Raw measurements and thresholds are the result. Metrics with different units are not collapsed into a universal score.

## Measured Results

{header}
{divider}
{rows}

## Measurement Coverage

- Measured: {measured}
- Not measured: {unmeasured}
""".format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            header=header,
            divider=divider,
            rows="\n".join(rows),
            measured=", ".join(measured) or "None",
            unmeasured=", ".join(unmeasured) or "None",
        )
        with open(output_markdown_path, "w", encoding="utf-8") as file:
            file.write(content)
        print(f"Report generated successfully: {output_markdown_path}")

    def _evidence_text(self, result, label):
        if result["not_measured_reason"]:
            return f"{label}: Not measured - {result['not_measured_reason']}"
        details = "; ".join(str(item) for item in result["evidence"])
        limitations = "; ".join(str(item) for item in result["limitations"])
        suffix = f" Limitations: {limitations}" if limitations else ""
        return f"{label}: {details}.{suffix}"

    def _display(self, value):
        if value is None:
            return "N/A"
        return f"{value:.6g}" if isinstance(value, float) else str(value)

    def _threshold_display(self, value):
        return "Yes" if value is True else "No" if value is False else "N/A"

def main():
    parser = argparse.ArgumentParser(description="Evaluate tool and baseline outputs using task-defined metrics")
    parser.add_argument("--tool-output", required=True)
    parser.add_argument("--baseline-output", required=True)
    parser.add_argument("--task-definition", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    evaluator = BenchmarkEvaluator(args.tool_output, args.baseline_output, args.task_definition)
    evaluator.load_data()
    evaluator.evaluate()
    evaluator.generate_report(args.report)


if __name__ == "__main__":
    main()
