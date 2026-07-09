# Optional Interview, Defense, or Portfolio Export

## Entry Gate

Run only after the user explicitly requests this export. It is not a verification phase and creates no new primary evidence.

Ask for the audience or job description. If none is available, let the user choose a clearly labeled general mode or stop. Do not silently assume an AI product manager profile.

## Evidence and Claim Approval

1. Load `verification_manifest.json`, `project_report.md`, flow matrix, completed result files, and raw logs referenced by those results.
2. Ask focused questions about the user's actual decisions, trade-offs, contribution, limitations, and learning. Do not infer ownership from repository contents.
3. Draft a candidate-claim table containing claim, evidence path, source revision, evidence scope, limitation, and excluded stronger claim.
4. Ask the user to approve or revise candidate claims before writing presentation material.

Architecture evolution requires Git history or another dated source. Without it, describe only current architecture and future options.

## Output

Create:

- `project_verification_workbench/interview_evidence_source_map.md`
- `interview_evidence_pack.md`

The single evidence pack may contain concise project narratives, product/technical decisions, verified results, limitations, likely questions, and evidence-backed answers. Neutral outcomes such as “no measured improvement” or “not yet verified” are valid.

Every strong claim must cite the source map or an earlier current-revision artifact. Do not create claims from conversation context alone.
