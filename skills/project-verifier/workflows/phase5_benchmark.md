# Phase 5: Evidence-First AI Comparative Evaluation

## Purpose

Evaluate an AI or AI-assisted feature only when a concrete product decision and defensible comparison exist. Negative and inconclusive results are valid outcomes.

## Applicability Gate

Load current architecture, flow matrix, prior results, and feature-level classification. Phase 5 is `not_applicable` for non-AI features or when no meaningful comparison claim exists.

First define:

- business question and decision this Eval will inform;
- target user and selected path IDs;
- comparison claim and why the Baseline is relevant.

Do not default to a bare LLM. A Baseline may be an older version, no-RAG configuration, different model/setup, manual workflow, or another approved alternative.

## Guided Direction Selection

Propose 3–5 directions and recommend 1–2. For each include user value, path IDs, claim, Baseline, inputs, raw metrics, assertions, dependencies, estimated calls, and limitations.

Let the user accept recommendations, select all, customize, add a direction, or skip. Ask detailed questions only for selected directions: real inputs, expected outputs, sensitive data, budget, tolerance, and minimum samples.

Classify each selected direction as `ready_now`, `needs_setup`, `plan_only`, or `rejected`.

## Metric Contract

Every metric requires:

- `rubric_approved: true` at the task-definition level after user approval;
- `measurement_method`
- `success_threshold`
- `minimum_samples`
- `evidence_fields`

For claims backed by generated files or logs, also set `require_evidence_files: true` and an approved `evidence_root`. The evaluator must verify those files exist inside that root; a path string alone is not evidence.

Report raw values, units, thresholds, `sample_adequacy`, evidence, and limitations. Without an approved definition or sufficient evidence, return `not_measured` with a reason. Do not generate normalized scores, a universal project score, or a radar chart.

A single run cannot prove stability. Compute P95/P99 only when a preapproved repeated-performance method meets its sample requirement.

LLM Judge may evaluate subjective semantic criteria only. Save the full prompt, model, model version, evidence, blinded identity, and randomized order. It cannot alone prove safety, security, privacy, or leakage.

## Plan, Authorization, and Execution

Create `project_verification_workbench/phase5_benchmark_plan.md` with selected scenarios, Baselines, metric contracts, equivalence deviations, budget, feasibility, and stop conditions.

Create task JSON only after plan approval. Tool and Baseline runs must use equivalent inputs, versions, sampling settings, resources, and failure policy, or disclose every deviation.

Run `run_benchmark.sh preflight`; it must not call the model, API, tool, or Baseline. Real pilot/full execution requires a current receipt bound to plan hash, source revision, calls, retries, and timeout.

A pilot tests harness feasibility only:

- `phase_status: completed`
- `result_outcome: inconclusive`
- `execution_scope: pilot`
- `claim_eligibility: pilot`

## Results and Exit

Write `project_verification_workbench/phase5_benchmark_results.json` with applicability, authorization, runs, raw metrics, evidence, errors, limitations, and recovery conditions. Empty output, missing evidence, task identity mismatch, or nonzero runner exit cannot be a win.

After review, ask whether the user wants the optional README or interview/portfolio export. Choosing no ends the workflow without creating presentation files.
