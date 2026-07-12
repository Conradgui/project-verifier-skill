import json
import os
import tempfile
import unittest
from pathlib import Path

from helpers import SKILL_ROOT, load_module, run, write_json


RUNNER = SKILL_ROOT / "templates/run_quality_template.sh"
VALIDATOR = SKILL_ROOT / "scripts/validate_gate_v3.py"
STALE_FIXTURE_ROOT = SKILL_ROOT / "evals/fixtures/stale_authorization"
GATE = load_module(VALIDATOR, "quality_runner_v3_gate")


def git(arguments, cwd):
    result = run(["git", *arguments], cwd)
    if result.returncode != 0:
        raise AssertionError(result.stdout)
    return result.stdout.strip()


def fingerprint(project_root):
    result = run(["python3", str(VALIDATOR), "fingerprint", "--root", str(project_root)], project_root)
    if result.returncode != 0:
        raise AssertionError(result.stdout)
    return result.stdout.strip()


def profile_payload(revision):
    return {
        "schema_version": "3.0",
        "source_identity": {
            "revision": revision,
            "captured_at": "2026-07-12T09:00:00+08:00",
            "repository_type": "git",
        },
        "reviewed_scope": {"in_scope": ["app.py"], "out_of_scope": [], "reviewed_paths": ["app.py"]},
        "runtimes": ["python3", "sh", "tsx"],
        "entry_points": [],
        "priority_paths": {"P0": [], "P1": [], "P2": []},
        "modules": [],
        "state_changes": [],
        "trust_boundaries": [],
        "sensitive_data_categories": [],
        "feature_ai_classification": [],
        "existing_capabilities": [],
        "evidence_references": [],
        "inferences": [],
        "unknowns": [],
    }


def envelope_payload(revision, path_ids):
    return {
        "schema_version": "1.0",
        "stage": "stage2",
        "decision_type": "live_e2e",
        "source_policy": {"mode": "exact", "base_revision": revision, "allowed_fix_paths": []},
        "scope": {
            "path_ids": path_ids,
            "targets": ["local-fixture"],
            "write_scope": ["project_verification_workbench"],
            "network": False,
            "credential_names": [],
            "sensitive_data": False,
            "side_effects": [],
        },
        "interpretation": {"claim": None, "baseline": None, "dataset_id": None, "metric_ids": []},
        "limits": {
            "max_paths": len(path_ids),
            "max_calls_per_path": 2,
            "max_retries": 1,
            "timeout_seconds": 10,
        },
    }


class QualityRunnerTests(unittest.TestCase):
    def make_project(self, scripts):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        project = root / "project"
        project.mkdir()
        git(["init"], project)
        git(["config", "user.email", "fixture@example.com"], project)
        git(["config", "user.name", "Fixture"], project)
        (project / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        test_dir = project / "tests/quality-e2e"
        test_dir.mkdir(parents=True)
        for name, content in scripts.items():
            path = test_dir / name
            path.write_text(content, encoding="utf-8")
            path.chmod(0o755)
        git(["add", "app.py", "tests"], project)
        git(["commit", "-m", "fixture"], project)
        revision = fingerprint(project)

        workbench = project / "project_verification_workbench"
        workbench.mkdir()
        (workbench / "project_report.md").write_text("# Fixture report\n", encoding="utf-8")
        (workbench / "flow_matrix.md").write_text("# Fixture matrix\n", encoding="utf-8")
        profile = profile_payload(revision)
        profile_path = workbench / "project_profile.json"
        write_json(profile_path, profile)

        path_ids = [Path(name).stem.removeprefix("quality_") for name in scripts]
        envelope = envelope_payload(revision, path_ids)
        receipt = {
            "decision_id": "DEC-S2-FIXTURE",
            "stage": "stage2",
            "decision_type": "live_e2e",
            "decision_envelope_sha256": GATE.canonical_object_hash(envelope),
            "source_revision": revision,
            "user_choice": "approved",
            "approved_limits": envelope["limits"],
            "approved_at": "2026-07-12T09:00:00+08:00",
            "invalidated_at": None,
        }
        stages = {
            stage: {
                "phase_status": "pending",
                "result_outcome": "not_run",
                "execution_scope": "none",
                "claim_eligibility": "none",
                "gate_state": "pending",
                "artifacts": [],
                "blockers": [],
                "recovery_conditions": [],
            }
            for stage in ("stage1", "stage2", "stage3", "stage4")
        }
        stages["stage1"].update(
            phase_status="completed",
            gate_state="not_required",
            artifacts=[
                "project_verification_workbench/project_report.md",
                "project_verification_workbench/flow_matrix.md",
                "project_verification_workbench/project_profile.json",
            ],
        )
        stages["stage2"]["gate_state"] = "approved"
        manifest = {
            "schema_version": "3.0",
            "source_revision": {
                "revision": revision,
                "dirty": False,
                "captured_at": "2026-07-12T09:00:00+08:00",
            },
            "user_intent": {
                "goal": "run local fixture",
                "target_users": ["fixture owner"],
                "in_scope": path_ids,
                "out_of_scope": [],
                "success_criteria": ["runner validates gates"],
                "risk_tolerance": "low",
            },
            "permissions": {
                "write_scope": ["project_verification_workbench"],
                "production_code_changes": False,
                "dependency_install": False,
                "live_calls": True,
                "public_claims": False,
            },
            "stages": stages,
            "source_history": [],
            "project_profile": {
                "path": "project_verification_workbench/project_profile.json",
                "status": "confirmed",
                "approved_fields_sha256": GATE.canonical_object_hash(profile),
            },
            "decisions": [receipt],
        }
        manifest_path = root / "manifest.json"
        receipt_path = root / "receipt.json"
        envelope_path = root / "envelope.json"
        write_json(manifest_path, manifest)
        write_json(receipt_path, receipt)
        write_json(envelope_path, envelope)
        reports = workbench / "quality-e2e-reports"
        results = workbench / "phase2_quality_results.json"
        env = {
            **os.environ,
            "QUALITY_TEST_DIR": str(test_dir),
            "QUALITY_REPORTS_DIR": str(reports),
            "QUALITY_RESULTS_JSON": str(results),
            "QUALITY_MANIFEST_FILE": str(manifest_path),
            "QUALITY_AUTHORIZATION_FILE": str(receipt_path),
            "QUALITY_ENVELOPE_FILE": str(envelope_path),
            "QUALITY_PROFILE_FILE": str(profile_path),
            "QUALITY_SOURCE_REVISION": revision,
            "QUALITY_MAX_PATHS": str(envelope["limits"]["max_paths"]),
            "QUALITY_MAX_CALLS_PER_PATH": "2",
            "QUALITY_MAX_RETRIES": "1",
            "QUALITY_TIMEOUT_SECONDS": "10",
            "PROJECT_VERIFIER_GATE_VALIDATOR": str(VALIDATOR),
            "PROJECT_VERIFIER_PROJECT_ROOT": str(project),
        }
        return tmp, root, project, manifest_path, envelope_path, results, env

    def runner(self, mode, cwd, env=None):
        return run(["bash", str(RUNNER), *([mode] if mode else [])], cwd, env)

    def test_no_argument_prints_help_without_finding_or_executing_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "executed"
            result = self.runner(None, Path(tmp), {**os.environ, "QUALITY_TEST_DIR": str(marker)})
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("Usage:", result.stdout)
            self.assertFalse(marker.exists())

    def test_preflight_uses_confirmed_profile_without_executing_scripts(self):
        script = "#!/bin/sh\ntouch preflight-executed\n"
        tmp, root, project, _, _, _, env = self.make_project({"quality_P0_marker.sh": script})
        with tmp:
            result = self.runner("preflight", project, env)
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("Profile handoff passed", result.stdout)
            self.assertIn("No Smoke/live scripts were executed", result.stdout)
            self.assertFalse((project / "preflight-executed").exists())

    def test_preflight_rejects_invalid_names_and_bounds_without_executing_scripts(self):
        script = "#!/bin/sh\ntouch invalid-preflight-executed\n"
        tmp, _, project, _, _, _, env = self.make_project({"quality_P0_marker.sh": script})
        with tmp:
            result = self.runner(
                "preflight",
                project,
                {**env, "QUALITY_REQUIRED_ENV": "INVALID-NAME", "QUALITY_TIMEOUT_SECONDS": "0"},
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("Invalid environment variable name", result.stdout)
            self.assertIn("QUALITY_TIMEOUT_SECONDS", result.stdout)
            self.assertFalse((project / "invalid-preflight-executed").exists())

    def test_preflight_enforces_max_paths_without_executing_scripts(self):
        scripts = {
            "quality_P0_one.sh": "#!/bin/sh\ntouch max-paths-executed\n",
            "quality_P0_two.sh": "#!/bin/sh\ntouch max-paths-executed\n",
        }
        tmp, _, project, _, _, _, env = self.make_project(scripts)
        with tmp:
            result = self.runner("preflight", project, {**env, "QUALITY_MAX_PATHS": "1"})
            self.assertNotEqual(0, result.returncode)
            self.assertIn("exceeding approved max_paths", result.stdout)
            self.assertFalse((project / "max-paths-executed").exists())

    def test_preflight_rejects_output_paths_outside_workbench_without_dispatch(self):
        script = "#!/bin/sh\ntouch output-path-executed\n"
        tmp, root, project, _, _, _, env = self.make_project({"quality_P0_marker.sh": script})
        with tmp:
            result = self.runner(
                "preflight",
                project,
                {**env, "QUALITY_REPORTS_DIR": str(root / "outside-reports")},
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("workbench", result.stdout.lower())
            self.assertFalse((project / "output-path-executed").exists())

    def test_run_validates_profile_and_envelope_before_dispatch(self):
        script = "#!/bin/sh\ntouch should-not-execute\n"
        tmp, _, project, _, envelope_path, _, env = self.make_project({"quality_P0_guard.sh": script})
        with tmp:
            envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
            envelope["scope"]["network"] = True
            write_json(envelope_path, envelope)
            result = self.runner("run", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("envelope", result.stdout.lower())
            self.assertFalse((project / "should-not-execute").exists())

    def test_run_rejects_unconfirmed_profile_before_dispatch(self):
        script = "#!/bin/sh\ntouch profile-should-not-execute\n"
        tmp, _, project, manifest_path, _, _, env = self.make_project({"quality_P0_guard.sh": script})
        with tmp:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["project_profile"]["status"] = "pending"
            write_json(manifest_path, manifest)
            result = self.runner("run", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("profile", result.stdout.lower())
            self.assertFalse((project / "profile-should-not-execute").exists())

    def test_run_rejects_missing_and_over_limit_authorization_before_dispatch(self):
        script = "#!/bin/sh\ntouch authorization-should-not-execute\n"
        tmp, _, project, _, _, _, env = self.make_project({"quality_P0_guard.sh": script})
        with tmp:
            missing = self.runner("run", project, {**env, "QUALITY_AUTHORIZATION_FILE": ""})
            self.assertNotEqual(0, missing.returncode)
            self.assertIn("Missing execution authorization input", missing.stdout)
            self.assertFalse((project / "authorization-should-not-execute").exists())

            over_limit = self.runner("run", project, {**env, "QUALITY_MAX_CALLS_PER_PATH": "3"})
            self.assertNotEqual(0, over_limit.returncode)
            self.assertIn("exceeds", over_limit.stdout.lower())
            self.assertFalse((project / "authorization-should-not-execute").exists())

    def test_run_accepts_lower_call_and_timeout_limits(self):
        script = (
            "#!/bin/sh\n"
            "mkdir -p project_verification_workbench/quality-e2e-reports\n"
            "printf '%s' '{\"external_calls_actual\":0,\"retries_actual\":0,\"side_effects\":[]}' "
            "> project_verification_workbench/quality-e2e-reports/quality_P0_lower.telemetry.json\n"
        )
        tmp, _, project, _, _, results, env = self.make_project({"quality_P0_lower.sh": script})
        with tmp:
            result = self.runner(
                "run",
                project,
                {**env, "QUALITY_MAX_CALLS_PER_PATH": "1", "QUALITY_MAX_RETRIES": "0", "QUALITY_TIMEOUT_SECONDS": "5"},
            )
            self.assertEqual(0, result.returncode, result.stdout)
            payload = json.loads(results.read_text(encoding="utf-8"))
            self.assertEqual(1, payload["execution_bounds"]["max_calls_per_path"])
            self.assertEqual(5, payload["execution_bounds"]["timeout_seconds"])

    def test_run_dispatches_python_shell_and_typescript_with_telemetry(self):
        telemetry = "'{\"external_calls_actual\":0,\"retries_actual\":0,\"side_effects\":[]}'"
        scripts = {
            "quality_P0_python.py": (
                "from pathlib import Path\n"
                "reports = Path('project_verification_workbench/quality-e2e-reports')\n"
                "reports.mkdir(parents=True, exist_ok=True)\n"
                "(reports / 'quality_P0_python.telemetry.json').write_text(" + telemetry + ")\n"
                "print('python-dispatch-ok')\n"
            ),
            "quality_P0_shell.sh": (
                "#!/bin/sh\n"
                "mkdir -p project_verification_workbench/quality-e2e-reports\n"
                "printf %s " + telemetry + " > project_verification_workbench/quality-e2e-reports/quality_P0_shell.telemetry.json\n"
                "echo shell-dispatch-ok\n"
            ),
            "quality_P0_typescript.ts": (
                "#!/bin/sh\n"
                "mkdir -p project_verification_workbench/quality-e2e-reports\n"
                "printf %s " + telemetry + " > project_verification_workbench/quality-e2e-reports/quality_P0_typescript.telemetry.json\n"
                "echo typescript-dispatch-ok\n"
            ),
        }
        tmp, root, project, _, _, results, env = self.make_project(scripts)
        with tmp:
            bin_dir = root / "bin"
            bin_dir.mkdir()
            tsx = bin_dir / "tsx"
            tsx.write_text("#!/bin/sh\nexec sh \"$1\"\n", encoding="utf-8")
            tsx.chmod(0o755)
            result = self.runner("run", project, {**env, "PATH": f"{bin_dir}:{env['PATH']}"})
            self.assertEqual(0, result.returncode, result.stdout)
            payload = json.loads(results.read_text(encoding="utf-8"))
            self.assertEqual("pass", payload["result_outcome"])
            self.assertEqual(3, len(payload["paths"]))
            self.assertEqual({"P0_python", "P0_shell", "P0_typescript"}, {item["path_id"] for item in payload["paths"]})
            self.assertTrue(all(item["telemetry_status"] == "valid" for item in payload["paths"]))
            self.assertTrue(all(item["telemetry_provenance"]["exit_code"] == "wrapper_observed" for item in payload["paths"]))
            self.assertTrue(all(item["telemetry_provenance"]["external_calls_actual"] == "script_self_reported" for item in payload["paths"]))
            self.assertTrue(all(item["external_calls_actual"] == 0 for item in payload["paths"]))
            self.assertEqual("DEC-S2-FIXTURE", payload["execution_authorization"]["decision_id"])

    def test_partial_and_missing_telemetry_preserve_non_pass_outcomes(self):
        telemetry = "'{\"external_calls_actual\":0,\"retries_actual\":0,\"side_effects\":[]}'"
        scripts = {
            "quality_P0_success.sh": (
                "#!/bin/sh\nmkdir -p project_verification_workbench/quality-e2e-reports\n"
                "printf %s " + telemetry + " > project_verification_workbench/quality-e2e-reports/quality_P0_success.telemetry.json\nexit 0\n"
            ),
            "quality_P0_failure.sh": (
                "#!/bin/sh\nmkdir -p project_verification_workbench/quality-e2e-reports\n"
                "printf %s " + telemetry + " > project_verification_workbench/quality-e2e-reports/quality_P0_failure.telemetry.json\nexit 7\n"
            ),
        }
        tmp, _, project, _, _, results, env = self.make_project(scripts)
        with tmp:
            partial = self.runner("run", project, env)
            self.assertNotEqual(0, partial.returncode)
            partial_payload = json.loads(results.read_text(encoding="utf-8"))
            self.assertEqual("completed", partial_payload["phase_status"])
            self.assertEqual("partial", partial_payload["result_outcome"])
            self.assertEqual(7, next(item for item in partial_payload["paths"] if item["path_id"] == "P0_failure")["exit_code"])

        tmp, _, project, _, _, results, env = self.make_project({"quality_P0_missing.sh": "#!/bin/sh\nexit 0\n"})
        with tmp:
            missing = self.runner("run", project, env)
            self.assertNotEqual(0, missing.returncode)
            missing_payload = json.loads(results.read_text(encoding="utf-8"))
            self.assertEqual("inconclusive", missing_payload["result_outcome"])
            self.assertEqual("none", missing_payload["claim_eligibility"])

    def test_stale_authorization_fixture_uses_v3_stage2_envelope_identity(self):
        receipt = json.loads((STALE_FIXTURE_ROOT / "stage2_live_execution.json").read_text(encoding="utf-8"))
        manifest = json.loads((STALE_FIXTURE_ROOT / "verification_manifest_v3.json").read_text(encoding="utf-8"))
        plan = (STALE_FIXTURE_ROOT / "stage2_quality_plan.md").read_text(encoding="utf-8")
        GATE.validate_receipt(receipt)
        GATE.validate_manifest(manifest)
        self.assertEqual("stage2", receipt["stage"])
        self.assertEqual("live_e2e", receipt["decision_type"])
        self.assertEqual(receipt, manifest["decisions"][0])
        self.assertIn("must not match", plan)
        envelope = json.loads(plan.split("```json\n", 1)[1].split("\n```", 1)[0])
        GATE.validate_decision_envelope(envelope)
        self.assertNotEqual(receipt["decision_envelope_sha256"], GATE.canonical_object_hash(envelope))
