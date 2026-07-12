# Task 5 Independent Review

Reviewer: independent read-only subagent (`Newton`)

Verdict: `CHANGES_REQUIRED`

## Findings

1. `P0` - An arbitrary project bridge could exceed declared capabilities,
   limits, or write scope because the runner executed `.sh`/`.py` code without
   OS sandboxing.
2. `P1` - The runner checked task IDs and targets as separate sets, allowing
   two approved targets to be exchanged between two task IDs.
3. `P1` - The normalizer did not redact common secret keys such as `api_key`,
   `password`, `authorization`, `access_token`, `client_secret`, or
   `private_key`.

## Controller Repair Status

- Added a fail-closed `trusted_custom_bridge_execution` marker to the existing
  authorized envelope. It makes unsandboxed bridge execution explicit and does
  not claim technical isolation.
- Replaced independent set comparison with exact `task_id -> target` pair
  comparison, covered by a two-task target-swap regression.
- Expanded normalized recursive secret-key redaction and its regression fixture.

The repair awaits a fresh independent re-review. The reviewer did not edit,
commit, install software, execute a scan, access a network, or access secrets.

---

## Second Independent Review

Reviewer: independent read-only subagent (`Poincare`)

Verdict: `CHANGES_REQUIRED` with no P0 finding.

## Findings

1. `P1` - A caller-controlled `TMPDIR` could place preflight metadata in the
   target project.
2. `P1` - A bridge under the workbench could be changed without altering the
   source fingerprint.
3. `P1` - Declared task side effects were not compared with the authorized
   decision side effects.
4. `P1` - A stale raw output or a collision with runner artifacts could be
   accepted as current evidence.
5. `P1` - Common `secret` and provider-key field names could survive redaction.
6. `P2` - Source-location normalization discarded column/end-position fields
   before exact de-duplication.
7. `P2` - The normalizer CLI did not require an executed scope for a clean
   conclusion.

## Controller Repair Status

- Added external temporary-directory and source-bound bridge checks.
- Bound declared side effects to `scope.side_effects`.
- Rejected stale/colliding raw outputs before bridge dispatch.
- Extended conservative recursive key redaction, preserved supported source
  location precision, and made CLI scope explicit.

Fresh independent re-review is pending. The reviewer performed no edits,
installation, networking, real scan, or secret access.

---

## Fourth Through Sixth Review Repairs

Three additional read-only review passes found no P0 issue. Their P1 findings
were repaired before the final review request:

1. The runner now accepts only the exact bundled V3 gate validator and binds
   normalization to a task's recorded raw-output path.
2. Source-bound bridge discovery rejects nested `.git` paths and symlinked
   runner-owned output leaves.
3. Cookie/session-like evidence is redacted, and every completed task's
   `decision_id` must equal the result's execution authorization ID.

The final two repairs have direct focused regressions. A new independent
read-only reviewer is evaluating the resulting diff; no review conclusion has
been inferred from these tests.

---

## Third Independent Review

Reviewer: independent read-only subagent (`Volta`)

Verdict: `CHANGES_REQUIRED` with no P0 finding.

## Findings

1. `P1` - `.git/` and Git-ignored bridges were not covered by source
   fingerprinting.
2. `P1` - Actual runner output paths were not compared with the envelope write
   scope.
3. `P1` - Two task descriptors could reuse one raw-output path.
4. `P1` - The normalizer CLI accepted a caller-provided scope instead of the
   runner's actual completed result.
5. `P1` - `provider_key` was not included in redaction despite the stated
   provider-key coverage.

## Controller Repair Status

- Rejected Git metadata and ignored task/descriptor paths.
- Required runner outputs to be in both manifest and envelope write scopes.
- Rejected duplicate raw output paths.
- Derived normalizer scope and decision ID from completed Stage 3 results.
- Added provider/access/service-key redaction without broad `key` matching.

Fresh independent re-review is pending. The reviewer performed no edits,
installation, networking, real scan, or secret access.

---

## Final Closure Review

The fourth through tenth independent passes successively exposed and repaired
capability/side-effect mismatch, raw/result provenance, write-scope binding,
free-text and structured-value disclosure, bridge-supplied triage, reversible
hash references, and runner-owned hard-link overwrite paths. Each repair added
a focused local regression; no scanner, network, installation, or target run
occurred.

Reviewer: independent read-only subagent (`Galileo`)

Verdict: `APPROVED`

No P0/P1 remained within the declared boundary: explicit trusted bridges are
not represented as OS sandboxes, local files are not represented as
cryptographically tamper-proof, and normalized output contains only run-local
CSPRNG refs plus controlled fields. Task 5 is frozen.
