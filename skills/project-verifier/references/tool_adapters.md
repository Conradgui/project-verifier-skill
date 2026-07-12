# Project-Fit Tool Adapters

## Boundary

Project Verifier owns project understanding, user decisions, no-call preflight,
authorization, raw-evidence custody, normalization, and claim limits. A tool
adapter is only a project-owned trusted bridge from an already available backend
to the adapter-intermediate JSON contract. Detection and recommendation never install
a tool, update a vulnerability database, access a network, or scan a target.

Capability metadata binds a proposed bridge to a user decision; it is not an OS
sandbox. A custom `.sh` or `.py` bridge can run only when the same approved
envelope explicitly includes `trusted_custom_bridge_execution`. If technical
isolation is required and an existing isolated executor is unavailable, retain
the plan and do not dispatch the bridge.

Bridge descriptors must live outside `project_verification_workbench/`, `.git/`,
and Git-ignored paths, which are not covered by source fingerprinting. Each
descriptor's declared side effects must be a subset of the user-approved
`scope.side_effects`. The runner rejects raw-output paths that already exist,
repeat across tasks, or collide with its own logs/results, so a previous attempt
cannot be reused as fresh evidence.
When a descriptor names a side effect that is also a capability, the matching
capability must be separately authorized; side-effect metadata cannot turn an
unapproved download, database update, or network operation into an approved
bridge action.

## Detect, Propose, Preflight, Run, Normalize

1. **Detect:** derive relevant source, dependency/SBOM, secret, configuration,
   and Web/API surfaces from the confirmed Profile, P0/P1 user paths, trust
   boundaries, runtimes, and unknowns. Record existing tools by name and
   version when available; record only credential names or categories.
2. **Propose:** compare the current project-native option and at least one
   appropriate backend. State the selected scope, expected evidence, blind
   spots, fallback, and reduced coverage if the recommendation is declined.
3. **Preflight:** validate task metadata, installed tool names, scripts,
   targets, output paths, limits, and confirmed Profile without executing a
   scanner against a target.
4. **Run:** a project task bridge may execute only after its current V3
   `stage3 / security_execution` envelope authorizes every requested capability
   and explicitly acknowledges `trusted_custom_bridge_execution`.
5. **Normalize:** convert bridge output to redacted evidence records. Tool
   output is not exploitability proof, a certification, or a project-wide score.

## Comparison Record

For each candidate, record the following before asking for a decision:

| Dimension | Question |
| --- | --- |
| Fit and coverage | Which language/files does it cover, and is it source, dependency/SBOM, secret, configuration, or Web/API evidence? |
| Offline behavior | Can it operate from local evidence, and what data is unavailable offline? |
| Output and maintenance | Does it have machine-readable output, an identifiable version, current maintenance, and a stable bridge format? |
| Cost and state | Does it require a download, database update, network access, credentials, or persistent state? |
| Target risk | Is it read-only local analysis, passive dynamic observation, or an active request against a local/isolated target? |
| Blind spots | What formats, generated code, dependency provenance, false positives, runtime behavior, or unreviewed paths remain outside its evidence? |

The recommended backend is the smallest existing or readily available tool that
fits the selected surface. A rejected recommendation records the chosen
fallback and reduced coverage; it never silently installs, substitutes, or
downgrades a tool.

## Optional Backends

These are examples, not dependencies: Semgrep for source patterns;
OSV-Scanner or Trivy for dependency/SBOM vulnerabilities; Gitleaks for secret
scanning; ZAP for separately authorized passive or active Web/API testing; and
project-native scanners where they have equal or better fit. Every bridge must
record backend name, version, command identity, raw-output path, scope, and
known blind spots. The task descriptor version is the approved selection, not
independent proof of the installed binary; a bridge may preserve tool-reported
version in its raw evidence when available.

## Authorization Matrix

The security envelope has a complete boolean `limits.capabilities` matrix.
Each task declares one primary capability; a task that declares network use
also requires `network`. A permission does not imply another permission.

| Capability | Separate decision required | Target rule |
| --- | --- | --- |
| `offline_read_only` | Yes | Local files only; no target execution in preflight. |
| `tool_download` | Yes | Name/version/source and cost must be explicit. |
| `vulnerability_database_update` | Yes | Database source, time, and network cost must be explicit. |
| `network` | Yes | Destination class and expected external effect must be explicit. |
| `passive_dynamic_scan` | Yes | Observation-only target and traffic scope must be explicit. |
| `active_scan` | Yes | Target must be local or isolated; non-local targets are rejected. |

For an authorized run, the runner validates the complete Stage 1 Profile
handoff, current source fingerprint, receipt, envelope hash, all limits, exact
`task_id -> target` bindings, and each capability before it creates outputs or
dispatches a task. This binds the declared bridge plan, including side effects,
to the authorization; it does not sandbox the bridge or technically enforce its
side effects. The
envelope must have `stage3` and `security_execution`; lower numeric limits are
allowed only where the gate already permits them.

Runner-owned reports, logs, results, and raw outputs must be within both the
manifest write scope and the current envelope write scope. The normalizer CLI
derives its scope and decision ID from a completed Stage 3 results file, then
requires the requested task ID and its exact recorded raw-output path. It does
not accept an arbitrary clean-scope list or use one task's raw evidence for
another task. The runner records raw SHA-256 and current source revision; the
normalizer rejects a changed raw file or stale source and writes only a new,
non-symlink file under the shared manifest-plus-envelope write scope. It checks
that the current manifest records the same approved, non-invalidated decision
and envelope hash before writing. Its output contains only opaque references,
controlled enums, numeric positions, and boolean/count indicators; it does not
copy scanner evidence trees, tool text, paths, task IDs, decision IDs, or
tool-supplied recommendation text.

The Stage 3 validator is bundled with the Skill and must stay outside the
target project. A target-supplied or workbench-supplied validator is rejected,
because validation code excluded from the target source fingerprint cannot be a
trusted authorization gate. Any override must resolve to that exact bundled
validator. Nested `.git` task paths and runner-owned log/result symlinks are
also rejected before dispatch.

## Intermediate Finding Contract

A project bridge emits exactly:

```json
{
  "tool": {"name": "tool-name", "version": "known-version"},
  "findings": []
}
```

Each finding needs `category`, `rule_id`, and `source_location`; optional
evidence is adapter input only and never enters normalized output. The
normalizer emits run-local random opaque `category_ref`, `rule_ref`, `tool_ref`,
`source_ref`, and evidence-reference values plus numeric location positions,
controlled severity/confidence enums, and boolean/count indicators. It always
derives the finding ID, deduplicates only an exact original `category + rule_id
+ source_location` identity, and never copies task IDs, decision IDs, raw paths,
or arbitrary evidence keys/values. Every normalized finding is `needs_review`;
only a separate, user-confirmed triage record may assign a later disposition.
It does not infer exploitability, transform severity into a security score, or
turn clean output into a security conclusion.

Deduplication uses an exact category, rule identity, and source-location match
only; nearby lines, different rules, or different categories stay separate.
