# Current Stage 2 Plan

This envelope matches the approved receipt. The fixture instead models a source
change after Stage 1 confirmation and Stage 2 approval.

```json
{
  "schema_version": "1.0",
  "stage": "stage2",
  "decision_type": "live_e2e",
  "source_policy": {"mode": "exact", "base_revision": "fixture-rev", "allowed_fix_paths": []},
  "scope": {"path_ids": ["P0"], "targets": ["local"], "write_scope": ["project_verification_workbench"], "network": false, "credential_names": [], "sensitive_data": false, "side_effects": []},
  "interpretation": {"claim": null, "baseline": null, "dataset_id": null, "metric_ids": []},
  "limits": {"max_paths": 1, "max_calls_per_path": 2, "max_retries": 1, "timeout_seconds": 10}
}
```
