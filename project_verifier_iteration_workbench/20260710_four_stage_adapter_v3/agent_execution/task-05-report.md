# Task 5 Report: Stage 3 Project-Fit Security Boundary Verification

## Status

APPROVED_AND_FROZEN. The Task 5 subagent exhausted its
platform quota after writing its owned draft. The controller completed the
approved inline fallback. The first independent review returned
`CHANGES_REQUIRED`; its P0/P1 repairs were completed and the final independent
re-review returned `APPROVED`. The implementation adds a bounded V3 Stage 3 adapter
without modifying V2 consumers, README, CI, validator production code, or
target-project production code.

## Changed Files

- `skills/project-verifier/workflows/stage3_security.md`
- `skills/project-verifier/references/tool_adapters.md`
- `skills/project-verifier/templates/run_security_template.sh`
- `skills/project-verifier/templates/security_normalizer_template.py`
- `skills/project-verifier/tests/test_security.py`
- `skills/project-verifier/tests/test_contract.py`
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/agent_execution/task-05-report.md`

## RED Evidence

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/project-verifier-v3-pycache \
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_security.py' -v
```

Result: exit `1`; `8` tests ran, with `6` failures and `2` errors. The runner
was absent, so runner calls returned shell exit `127`; the normalizer was absent,
so direct import raised `FileNotFoundError`. No scanner, target, network, tool
download, vulnerability database update, or secret access occurred.

## GREEN Evidence

| Command | Exit | Result |
| --- | ---: | --- |
| Targeted `test_security.py` suite | `0` | `35/35` passed |
| Targeted `test_contract.py` suite | `0` | `12/12` passed |
| `bash -n skills/project-verifier/templates/run_security_template.sh` | `0` | Bash syntax valid |
| `bash skills/project-verifier/templates/run_security_template.sh` | `0` | Help only; no path discovery or task execution |
| `python3 -m py_compile skills/project-verifier/templates/security_normalizer_template.py` | `0` | Python syntax valid |
| Full V3 `unittest` discovery | `0` | `80/80` passed |
| `20260626_skill_hardening/template_behavior_tests.py` | `0` | `5/5` passed |
| `20260628_conditional_eval_gates/workflow_contract_tests.py` | `0` | `33/33` passed |
| `20260629_stage_gate_quality_v2/stage_gate_v2_tests.py` | `0` | `17/17` passed |
| `20260630_lean_core_simplification/lean_core_contract_tests.py` | `0` | `14/14` passed |
| `git diff --check` | `0` | No whitespace errors |

All execution tests use disposable local Git fixtures and fixture shell scripts.
They do not run a security scanner or access a real target.

## Independent Review And Repair

The first read-only review is recorded in `task-05-review.md` and found three
valid issues: arbitrary bridge scripts were not technically sandboxed despite
capability metadata, task IDs and targets were compared as independent sets,
and recursive redaction missed common secret field names.

- A project-supplied bridge now requires the already approved decision's
  explicit `trusted_custom_bridge_execution` side-effect marker. This is a
  single additional field in the existing decision, not an extra user gate.
  The runner labels all such executions `none_trusted_custom_bridge` and never
  claims that capability metadata is OS isolation.
- The authorization now compares exact `task_id -> target` pairs. The current
  source fingerprint already binds each approved pair to its script and
  descriptor at dispatch time.
- Redaction now recognizes normalized `api_key`, `password`, `authorization`,
  `access_token`, `client_secret`, `private_key`, and related common field
  names, including camel-case and separator variants.

The repair suite records RED failures for all three conditions, then passes
`12/12` targeted security tests and `12/12` Stage 3 contract tests. The prior
pre-review regression run passed V3 `68/68` and historical `5/5`, `33/33`,
`17/17`, and `14/14` suites.

## Second Independent Review And Repair

The second read-only review found no P0 issue but returned `CHANGES_REQUIRED`
for five P1 and two P2 gaps. Its findings are appended to
`task-05-review.md`.

- The runner now resolves its metadata directory and rejects `TMPDIR` when it
  is inside the target project. It also rejects a task directory under the
  workbench, which is deliberately excluded from source fingerprinting.
- A task's declared side effects must be a subset of the authorized decision's
  `scope.side_effects`; this preserves the explicit trusted-bridge marker while
  refusing undeclared task effects.
- Raw-output paths must be new and must not collide with runner logs, results,
  or the internal result stream. This prevents an old output from qualifying as
  evidence for a new authorization.
- Redaction now conservatively matches normalized secret, token, credential,
  password, authorization, API-key, and provider-key variants. Supported source
  locations preserve column/end positions for exact de-duplication; unsupported
  location fields are rejected rather than discarded.
- The normalizer CLI now requires a JSON executed-scope file and passes it into
  normalization, so an empty result cannot claim an unspecified clean scope.

These repairs add targeted RED-to-GREEN regressions. A final scope-required
normalizer regression raises the Stage 3 suite to `20/20`. The final full run
passes V3 `76/76` and historical `5/5`, `33/33`, `17/17`, and `14/14` suites;
the document contract remains `12/12`.

## Third Independent Review And Repair

The third read-only review found no P0 but returned `CHANGES_REQUIRED` for five
P1 gaps. Its findings are appended to `task-05-review.md`.

- Source-bound bridge discovery now rejects `.git/` and Git-ignored task or
  descriptor paths in addition to the workbench. Accepted bridge files are
  therefore covered by the source fingerprint as tracked or non-ignored
  untracked content.
- Every runner-owned report, result, log, and raw-output path is checked against
  both `manifest.permissions.write_scope` and `envelope.scope.write_scope`
  before dispatch.
- A raw-output path must be unique across the complete task set, as well as new
  and distinct from runner logs/results.
- The normalizer CLI derives scope only from a completed, passing Stage 3 result
  whose task evidence is complete; it records the associated decision ID rather
  than accepting a caller-supplied clean-scope list.
- Redaction now includes conservative provider, access, and service-key names
  without using a generic `key` matcher that would hide unrelated evidence.

The suite later reached `31/31` for Stage 3 security and remains `12/12` for
its document contract. The full V3 and historical commands from the preceding
review were not repeated after the final local redaction/provenance changes:
the mid-course necessity review records why release-wide verification is
reserved for the public-contract migration and final closeout.

## Later Review Repairs

Two subsequent read-only reviews found no P0 issue but identified narrowly
scoped P1 provenance and output-boundary gaps. The controller corrected them
without adding a scanner, a sandbox claim, or a new user gate:

- The runner accepts only its exact bundled V3 validator, refuses source paths
  below nested Git metadata, and refuses symlinked runner output leaves.
- The normalizer binds a supplied raw file to one completed task and rejects a
  task whose decision ID differs from the result's execution authorization.
- Recursive redaction now covers cookie and session-like field names, including
  common header-style variants such as `Set-Cookie`.

The last two changes have direct regressions in the `31/31` targeted suite.
An independent read-only review is in progress. No Task 5 scope expansion is
authorized while it runs.

## Tool-Selection Boundary

`tool_adapters.md` defines `detect -> propose -> preflight -> run -> normalize`.
Detection derives source, dependency/SBOM, secret, configuration, and Web/API
surfaces from the confirmed Profile. Recommendation compares language/file fit,
coverage, offline behavior, maintenance, version, output format, database or
network cost, target risk, and blind spots. Semgrep, OSV-Scanner/Trivy,
Gitleaks, ZAP, and project-native tools are documented as optional backends,
not dependencies. A missing tool emits its named fallback and reduced coverage;
the runner never installs or substitutes a tool. A project-provided bridge is
trusted code rather than a sandboxed capability; dispatch requires the explicit
trusted-bridge acknowledgement in the same user-approved envelope.

## Authorization Coverage

`preflight` validates Profile handoff, task metadata, tool-name availability,
targets, workbench-only output paths, limits, and active-target locality without
dispatching a task. Its metadata is held in a verified external temporary
directory, so preflight also succeeds when the target workbench is read-only.
`run` repeats preflight, then calls `validate_gate_v3.py` `check` with `stage3 /
security_execution`, current source, receipt, envelope, and all limits.

The envelope requires a complete capability matrix for `offline_read_only`,
`tool_download`, `vulnerability_database_update`, `network`,
`passive_dynamic_scan`, and `active_scan`. A task's primary capability and any
declared network capability are checked individually; no permission implies
another. Active tasks reject non-local/non-isolated targets before dispatch.
Task IDs and targets are checked as exact pairs rather than independent sets.
Task descriptors must be source-bound, use a verified external temporary
directory for runner metadata, avoid `.git/` and Git-ignored paths, and may
declare only user-authorized side effects. Raw output must be new, unique across
tasks, and must not collide with runner artifacts. Every runner-owned output is
also checked against both manifest and envelope write scopes.
After authorization, the runner writes result artifacts only under
`project_verification_workbench` and records bridge command identity, tool name
and descriptor-declared version, exit code, timeout-bounded duration, raw-output
path, target, network/active mode, declared side effects, and decision ID.

## Normalizer Behavior

The standard-library normalizer accepts only the adapter-intermediate
`tool`/`findings` payload. It preserves a recursively redacted `raw_evidence`
copy, replaces `secret_value`, `match`, `raw_secret`, and `token` at any depth,
and also redacts normalized `api_key`, `password`, `authorization`,
`access_token`, `client_secret`, `private_key`, credential, session, and cookie
field names, plus secret and provider-key variants. It creates deterministic
finding IDs when missing and collapses only an exact supported
category/rule/source-location match. The CLI derives scope and decision ID from
a completed Stage 3 result with complete task evidence; it does not accept an
arbitrary executed-scope list. Unknown triage becomes `needs_review`.

It reports `no_issue_found_in_executed_scope` only for an empty finding set and
states the supplied executed scope in limitations. It does not add a security
score, certification, or inferred exploitability conclusion.

## Migration Matrix

No legacy evaluator row moved to `ported`. An early draft attempted to map the
legacy Benchmark raw-evidence evaluator test to the new security normalizer.
That is not an equivalent behavior, so the migration-matrix row was restored to
`pending`. The new normalizer test is Stage 3 coverage only; legacy evaluator
coverage remains for its actual V3 Benchmark successor.

## Limitations And Blockers

There are no blockers within the Task 5 owned-file scope. The runner validates
authorization and metadata around project task bridges, but cannot establish
that a future bridge truthfully reports every tool side effect or that an
available tool's database is current. The task descriptor version is an
approved declaration, not independent proof of an installed binary version.
Normalization removes known secret-like field values but cannot prove that
arbitrary non-secret-key text contains no sensitive value. Clean output remains
limited to the executed scope and is not a security assurance.

Custom bridge scripts are not sandboxed. The explicit trusted-bridge decision
makes this remaining risk visible and fail-closed when missing; it does not
turn a bridge into technically isolated code.

No dependencies or security tools were installed. No vulnerability database was
updated, no network was accessed, no target was scanned, no secret value was
read. Repository bookkeeping after this closure records the implementation
only; it does not change the security-execution boundary.

## Final Closure (Supersedes Earlier Normalizer Descriptions)

Later review passes found that field-name redaction alone remained too weak for
a security summary. The final normalizer is intentionally one-way:

- It emits only CSPRNG run-local refs, controlled severity/confidence values,
  numeric location positions, and boolean/count indicators. It never serializes
  scanner text, evidence trees, source paths, task IDs, decision IDs, tool
  names, or raw-output paths.
- It derives every finding ID and assigns every finding `needs_review`; a bridge
  cannot accept or dismiss a finding. User-confirmed triage is a later record.
- It requires a matching raw SHA-256, current source fingerprint, current
  approved receipt in the manifest, matching envelope hash, and the shared
  manifest/envelope write scope before it creates a new output file.
- The runner rejects existing runner-owned result/log/stream paths, including
  symlinks and hard links, then uses exclusive creation for those files.

The final focused evidence is `35/35` Stage 3 tests, `12/12` V3 document
contract tests, Bash syntax/help, Python compilation, and `git diff --check`.
The final independent read-only review (`Galileo`) returned `APPROVED` with no
P0/P1 finding in the declared boundary. This does not make a local workbench
tamper-proof, a bridge sandboxed, or a clean result a security certification.
