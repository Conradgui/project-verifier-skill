# 2026-06-26 Deliverable Taxonomy Correction Plan

## Objective

Correct the project-verifier public and skill-facing deliverable taxonomy from three output families to four output families, making `interview_evidence_pack/` visible as an independent user-facing deliverable while preserving the rule that it is derived from workbench evidence.

## Planned Changes

- Update `README.md` so the "what it generates" table lists four deliverable families:
  - project understanding package
  - verification workbench
  - README update copy
  - interview / presentation evidence pack
- Add a short relationship statement: workbench is the evidence source, project understanding is the understanding layer, README copy is the public documentation layer, and interview pack is the role-specific presentation layer.
- Update `skills/project-verifier/SKILL.md` with a user-facing deliverables section so future agents do not confuse the workbench contract with the full output contract.
- Update `skills/project-verifier/workflows/phase6_interview.md` to state that interview materials are derived and must trace strong claims to the source map or prior phase artifacts.

## Acceptance Criteria

- README no longer says the skill generates only three deliverable families.
- README deliverables table includes `interview_evidence_pack/`.
- `SKILL.md` lists `project_understanding/`, `README_updated_[Date]_[RandomID].md`, and `interview_evidence_pack/`.
- Phase 6 still requires the existing four Markdown files and `phase6_interview_source_map.md`.
- Existing shell and Python syntax checks continue to pass.
