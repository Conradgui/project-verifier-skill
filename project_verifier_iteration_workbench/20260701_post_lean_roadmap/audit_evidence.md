# Post-Lean Audit Evidence

Audit date: 2026-07-01

## Confirmed State

- Active work is staged on `codex/stage-gate-quality-v2` at base `b0fa305`; it
  has not been committed, merged, pushed, or installed.
- Public `origin/main` is still at `1d05a75`; local `main` is one commit ahead.
- The installed copy at `~/.codex/skills/project-verifier` is the old six-phase
  version and differs from every core file in the current worktree.
- Current offline evidence covers 66 tests. There is no GitHub Actions workflow
  and no completed model-backed Agent behavior comparison.
- Root documentation includes README, CONTRIBUTING, and LICENSE. SECURITY,
  CHANGELOG, issue templates, and release/version policy are absent.
- CONTRIBUTING still asks contributors to install `pytest` and `vcrpy`, while
  the current verification suite intentionally uses the Python standard library.

## Credibility Gaps

1. Receipts bind the target project revision and proposal, but not the Skill,
   Validator, Evaluator, Runner, Hook, or schema revision.
2. Receipts have approval and invalidation timestamps but no required expiry for
   live calls, dependency installation, destructive actions, or publication.
3. Runner limits for calls and retries are validated against the receipt, but
   actual counts are supplied by the executed script's telemetry file. They are
   self-reported unless a project provides independent instrumentation.
4. The default Validator path may point into the target workbench. That path is
   excluded from source fingerprinting and is not independently hash-bound.
5. The optional Codex Hook has offline classifier/receipt tests but has not been
   installed and contract-tested against a real Codex Hook runtime.
6. Hook command classification is pattern-based. Arbitrary scripts can hide
   writes, network calls, installs, or publication actions; the Hook is not a
   sandbox.
7. `require_evidence_files` is optional. A file-backed metric can omit it unless
   the generated task contract is strengthened.
8. The Evaluator does not independently require `rubric_approved: true` or a
   rubric hash, and baseline equivalence remains mostly a workflow instruction.
9. Git-based source fingerprinting has no non-Git fallback and intentionally
   ignores workbench files; ignored runtime configuration needs a separate,
   secret-safe identity policy.

## Product and Maintenance Gaps

- Canonical tests live inside iteration workbenches instead of a stable `tests/`
  tree.
- Historical workbenches have no index or superseded-status map.
- Bootstrap lists several Agent directories, but only link placement is tested;
  runtime behavior on those hosts is not proven.
- There is no automated release artifact, checksum, compatibility matrix, or
  migration policy for manifest schema changes.
- There is no sanitized end-to-end example showing the exact workbench output a
  new user should expect.
