# Current Stage 2 Quality Plan

The selected `stage2 / live_e2e` envelope has a material change from receipt
`DEC-STALE-S2-001`. Its canonical hash must not match the all-zero receipt hash.
The fixture is intentionally stale and must be rejected before any path script
is dispatched.

```json
{
  "schema_version": "1.0",
  "stage": "stage2",
  "decision_type": "live_e2e",
  "source_policy": {
    "mode": "exact",
    "base_revision": "fixture-rev",
    "allowed_fix_paths": []
  },
  "scope": {
    "path_ids": ["P0"],
    "targets": ["fixture"],
    "write_scope": ["project_verification_workbench"],
    "network": true,
    "credential_names": [],
    "sensitive_data": false,
    "side_effects": []
  },
  "interpretation": {
    "claim": null,
    "baseline": null,
    "dataset_id": null,
    "metric_ids": []
  },
  "limits": {
    "max_paths": 1,
    "max_calls_per_path": 2,
    "max_retries": 1,
    "timeout_seconds": 10
  }
}
```
