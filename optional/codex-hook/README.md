# Optional Codex Hook

This directory is a separately installed Codex plugin. It is not installed by
`bootstrap.sh` and is not required to run `$project-verifier`.

The PreToolUse guard recognizes five visible action classes:

- `project_write`
- `dependency_install`
- `live_network`
- `destructive`
- `git_publish`

For a proposed event, generate the exact action hash before approval:

```bash
python3 pre_tool_guard.py --classify --project-root /path/to/project < event.json
```

An approved receipt must use the returned action class as `decision_type` and
store the returned hash as `approved_limits.action_sha256`. Before allowing the
event, the hook validates the receipt, proposal hash, current source revision,
manifest decision, and approved write scope through `validate_gate.py`.

Set these paths in the trusted Codex environment after creating the receipt:

```text
PROJECT_VERIFIER_PROJECT_ROOT
PROJECT_VERIFIER_HOOK_MANIFEST
PROJECT_VERIFIER_HOOK_RECEIPT
PROJECT_VERIFIER_HOOK_PROPOSAL
PROJECT_VERIFIER_GATE_VALIDATOR
```

Review and trust the Hook in Codex before use. Missing or invalid authorization
fails closed for recognized high-risk actions. Pattern classification cannot
detect every side effect hidden inside an arbitrary script, so this plugin is
experimental, Codex-only, and not a sandbox or security certification. It has
offline classifier tests; real host smoke validation is still required before
claiming runtime enforcement quality.
