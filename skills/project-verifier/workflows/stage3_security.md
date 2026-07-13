# Stage 3: Project-Fit Security Boundary Verification

## Purpose

Stage 3 produces bounded evidence for selected security surfaces. It is not a
generic instruction to download a scanner, a certification, or a project-wide
security score. A clean result means only that no issue was found in the
executed scope; it does not establish the absence of vulnerabilities.

## Derive Surfaces Before Choosing Tools

Consume the confirmed Stage 1 Profile only after the Profile handoff gate
passes at the current source revision. Derive candidate surfaces from reviewed
paths, user flows, runtimes, dependency files, trust boundaries, sensitive-data
categories, configuration, entry points, and documented unknowns. State which
source, dependency/SBOM, secret, configuration, and Web/API surfaces are in
scope and which are not.

Use [tool_adapters.md](../references/tool_adapters.md) to compare existing
project-native commands with candidate backends. The comparison records fit,
coverage, offline capability, maintenance, version, output format, download or
database/network cost, target risk, and blind spots. Recommend one bounded
tool/scope combination. If the user declines it, record the fallback and its
reduced coverage; do not install a tool or silently switch one.

## One Concise Decision

Before execution, present one concise tool/scope/permission decision with the
selected tasks, local or isolated targets, expected side effects, output paths,
limits, tool versions, raw-output locations, and known blind spots. Write the
machine plan to `project_verification_workbench/stage3_security_plan.json` and
a human summary to `project_verification_workbench/stage3_security_plan.md`.

The decision envelope is `stage3 / security_execution` and has a complete
capability matrix for `offline_read_only`, `tool_download`,
`vulnerability_database_update`, `network`, `passive_dynamic_scan`, and
`active_scan`. Each is separately authorized: approval for one cannot inherit
approval for another. Active scanning is permitted only against a local or
isolated target. Any new tool download, vulnerability database update, network
use, passive dynamic scan, active scan, sensitive data, target, material side
effect, or increased limit requires renewed authority.

For a project-supplied `.sh` or `.py` bridge, the same one-decision envelope
must also list `trusted_custom_bridge_execution` in `scope.side_effects`.
This is an explicit acknowledgement that the bridge is trusted code, not a
sandboxed capability. Without this marker, `run` refuses dispatch and leaves a
plan-only result. Do not describe the runner as an OS sandbox or as technical
enforcement of a bridge's undeclared side effects. Where technical isolation is
required, use an already available isolated executor outside this Skill or do
not execute the bridge.

The decision lists every declared bridge side effect as well as the trusted
bridge marker; a task may not declare an effect outside that list. Store bridge
scripts and descriptors in a source-bound project directory, never under
`project_verification_workbench/`, `.git/`, or a Git-ignored path, because
those locations are not covered by the source fingerprint.
When a declared side effect is also a named capability (for example
`tool_download` or `network`), that capability must be `true` in the same
approved matrix; a side-effect label cannot bypass the separate capability
decision.

## No-Target Preflight And Run

Run `bash run_security_template.sh preflight` before requesting task dispatch.
Preflight validates the confirmed Stage 1 Profile, installed tool names, task
scripts and metadata, targets, output paths, limits, and task permissions. It
may inspect files and tool availability, but it must not execute a scanner,
execute a target, access a network, update a database, download a tool, or
write production source.

Preflight holds its own metadata in a verified temporary directory outside the
target project. It rejects a temporary directory inside the project, a bridge
directory inside the workbench, a pre-existing raw-output file, or a raw-output
path that collides with the runner's log or result paths. Each task must have a
distinct raw-output path. Before dispatch, every report, result, log, and raw
output must also be inside both the manifest and current envelope write scopes.
The authorization validator must come from the installed Skill, never from the
target project or its workbench; overrides are accepted only when they resolve
to the exact bundled validator. A task or descriptor is rejected when any path
component is `.git`, and runner log/result leaf paths must not be symlinks.

Preflight must not execute a target or infer any security result from tool
availability.

`bash run_security_template.sh run` re-runs preflight, then requires a current
envelope, receipt, exact source fingerprint, complete limits, exact
`task_id -> target` bindings, and each task's requested capability before
dispatch. Runner-owned artifacts stay in the workbench and it records command
identity, the task descriptor's declared tool version, exit code, duration,
raw-output path, target, network/active mode, declared side effects, isolation
status, and authorization decision ID. Task bridges are responsible for
producing the declared raw output; missing raw output remains incomplete
evidence. The runner records a SHA-256 for each present raw output and the
gate-validated source revision. These bind later normalization to the content
and source identity observed at dispatch; they are provenance checks, not a
claim that locally writable files are cryptographically tamper-proof.

## Normalize And Triage

Project bridges emit the adapter-intermediate format from
`tool_adapters.md`. Run `security_normalizer_template.py` to validate records,
preserve redacted raw evidence, recursively replace secret-like fields, create
missing deterministic IDs, and deduplicate only exact supported
category/rule/location matches. Its CLI takes the current Stage 3 result JSON,
requires one task ID, and accepts only the raw-input path recorded for that
complete task with present raw output. It records the runner decision ID and
must reject incomplete results or a raw file for a different task rather than
emit a clean conclusion for an arbitrary supplied scope. Unknown or
interpretation-changing triage remains `needs_review`.

The normalizer receives the project root, current manifest, and current
authorization envelope explicitly and accepts only existing raw/result files
within `project_verification_workbench/`. It refuses a stale source fingerprint,
changed raw SHA-256, mismatched or invalidated authorization, symlinked or
external paths, an output outside the shared write scope, and an existing output
path. It retains only opaque references, controlled enums, and numeric
positions in normalized output; no evidence tree, tool text, recommendation,
method, limitation, task, decision, or raw path is copied. Raw tool output stays
local evidence and must not be copied into reports or exports.

Normalization is one-way: scanner-provided category, rule, tool, source-path,
and user-path strings become run-local random opaque references, while only numeric
positions and controlled severity/confidence enums remain visible. Every finding
starts as `needs_review`; a bridge cannot mark a finding accepted or false
positive. Link a safe finding reference to a user path only in a later,
user-confirmed triage record.

Link normalized findings to the selected user path and ask the user to confirm
triage only where that interpretation would change a decision. Do not infer
exploitability, read secret values, state that a finding is exploitable, or
generate a security score.

The normalizer must not infer exploitability from tool severity or evidence.

## Output And Limitations

Write `project_verification_workbench/security_report.md` and
`project_verification_workbench/stage3_security_results.json`. Keep safe
finding and provenance references, non-executed surfaces, fallback coverage,
and limitations visible. Keep raw paths, decision IDs, task IDs, and tool text
only in the bounded runner results; do not copy them into the normalized or
user-facing report.
Separate `phase_status`, `result_outcome`, `execution_scope`, and
`claim_eligibility`; Stage 3 evidence alone is not a certification or a public
security claim.
