# Midcourse Necessity Review

Date: 2026-07-13

## Decision

The V3 effort remains necessary, but its dominant risk has moved from an
individual runner defect to an incomplete public-contract migration. The
current root `SKILL.md` and README still expose the legacy five-phase workflow,
while V3 Stage 1--3 files are transitional and not yet the user entry path.
Completing more isolated hardening before that migration would have declining
product value.

## Keep

- The four-stage target: understanding, quality/E2E, scoped security, and
  conditional AI Benchmark.
- Fail-closed authorization, source revision binding, preflight, raw evidence,
  negative-result preservation, and explicit limitations.
- The bounded security adapter: it selects a project-fit backend and does not
  install, network, or scan without authorization.

## Stop Expanding In Task 5

- Do not add a generic sandbox, scanner download path, new security backend, or
  universal security score.
- Do not repeatedly execute all historical suites for local Task 5 edits.
- The project bridge remains explicitly trusted, not technically isolated; the
  workflow must continue to state this limitation.

## Required Closure For Task 5

1. Protect the two last changed trust boundaries with focused tests: cookie /
   session-like evidence redaction and per-task decision-ID binding.
2. Run the focused security and contract suites plus syntax/compile/diff checks.
3. Obtain one fresh independent read-only review. Any P0/P1 defect is repaired
   once and re-reviewed; otherwise Task 5 is frozen and committed.

## Revised Validation Cadence

- Tasks 5 and 6: focused tests for owned files, plus shared-contract tests only
  when those interfaces change.
- Task 7: complete V3 suite and historical compatibility checks because it
  changes the public contract and replaces legacy paths.
- Task 8: one release-closeout validation and staged-diff hygiene review.

This does not reduce the evidence standard. It avoids treating repeated
execution of unchanged tests as a substitute for integrating the user-visible
workflow.
