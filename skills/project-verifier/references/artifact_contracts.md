# V3 Artifact Contracts

## State Model

Each V3 stage (`stage1` through `stage4`) records four independent dimensions:

- `phase_status`: progress through the stage.
- `result_outcome`: evidence result, including negative and inconclusive results.
- `execution_scope`: no execution, plan-only, pilot, or full execution.
- `claim_eligibility`: whether evidence can support no claim, a pilot claim, or a full claim.

`gate_state` records whether a material decision is required, pending, approved, or blocked. It does not replace any of the four dimensions.

## Decision Envelope And Receipt

The decision envelope is the complete material authorization surface. Its canonical JSON SHA-256 is stored in the receipt as `decision_envelope_sha256`. Markdown plans, log locations, and formatting are evidence aids and are not authorization inputs.

An authorization receipt has exactly these fields:

```text
decision_id
stage
decision_type
decision_envelope_sha256
source_revision
user_choice
approved_limits
approved_at
invalidated_at
```

The receipt and the matching manifest decision must be identical. The receipt's `approved_limits` must equal the envelope limits. A requested numeric limit may be lower than the approved maximum; strings, booleans, lists, and objects require exact equality.

## Source Policies

`exact` requires the current secret-safe fingerprint to equal `source_policy.base_revision`.

`approved_fix_scope` requires a clean `git:<commit>` base that is an ancestor of `HEAD`. The validator enumerates the Git difference from that base, including committed, staged, and unstaged changes, and separately enumerates untracked files. Every changed path must be within `allowed_fix_paths`. When the current fingerprint differs from the base, `source_history` must record both fingerprints and set `affected_artifacts_stale` to `true`; the receipt keeps the approved base as the authority for the unchanged objective.

## V3 Manifest

The V3 manifest has only `stages.stage1` through `stages.stage4`; it has no duplicate `phases` tree. It also records `source_history` and a `project_profile` reference. `paths` checks the manifest's approved write scope and rejects unsafe or out-of-scope relative paths.

## Project Profile

The stable Project Profile records factual project understanding: source identity, reviewed scope, runtimes, entry points, P0/P1/P2 paths, modules, state changes, trust boundaries, sensitive-data categories, feature-level AI classification, existing capabilities, evidence references, inferences, and unknowns.

It must not contain commands, selected tools, secret values, or transient execution limits. Credential references use names or categories only.
