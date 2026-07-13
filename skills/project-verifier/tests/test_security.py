import json
import os
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from helpers import SKILL_ROOT, load_module, run, write_json


RUNNER = SKILL_ROOT / "templates/run_security_template.sh"
NORMALIZER = SKILL_ROOT / "templates/security_normalizer_template.py"
VALIDATOR = SKILL_ROOT / "scripts/validate_gate.py"
GATE = load_module(VALIDATOR, "security_runner_v3_gate")


CAPABILITIES = {
    "offline_read_only",
    "tool_download",
    "vulnerability_database_update",
    "network",
    "passive_dynamic_scan",
    "active_scan",
}
TRUSTED_CUSTOM_BRIDGE_EXECUTION = "trusted_custom_bridge_execution"


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
        "runtimes": ["python3", "sh"],
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


def capabilities_payload(*allowed):
    return {capability: capability in allowed for capability in sorted(CAPABILITIES)}


def envelope_payload(revision, task_ids, targets, allowed_capabilities, side_effects=None):
    return {
        "schema_version": "1.0",
        "stage": "stage3",
        "decision_type": "security_execution",
        "source_policy": {"mode": "exact", "base_revision": revision, "allowed_fix_paths": []},
        "scope": {
            "path_ids": task_ids,
            "targets": targets,
            "write_scope": ["project_verification_workbench"],
            "network": allowed_capabilities["network"],
            "credential_names": [],
            "sensitive_data": False,
            "side_effects": side_effects or [TRUSTED_CUSTOM_BRIDGE_EXECUTION],
        },
        "interpretation": {"claim": None, "baseline": None, "dataset_id": None, "metric_ids": []},
        "limits": {
            "max_tasks": len(task_ids),
            "max_commands_per_task": 1,
            "timeout_seconds": 10,
            "capabilities": allowed_capabilities,
        },
    }


def approve_envelope(root, envelope):
    envelope_path = root / "envelope.json"
    receipt_path = root / "receipt.json"
    manifest_path = root / "manifest.json"
    write_json(envelope_path, envelope)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["decision_envelope_sha256"] = GATE.canonical_object_hash(envelope)
    receipt["approved_limits"] = envelope["limits"]
    write_json(receipt_path, receipt)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["decisions"] = [receipt]
    write_json(manifest_path, manifest)


class SecurityRunnerTests(unittest.TestCase):
    def make_project(
        self,
        task_capability="offline_read_only",
        target="local-fixture",
        tool_name="sh",
        authorized_capabilities=None,
        additional_tasks=None,
        task_side_effects=None,
        authorized_side_effects=None,
        raw_output_path=None,
        writes_raw=True,
        additional_raw_output_paths=None,
    ):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        project = root / "project"
        project.mkdir()
        git(["init"], project)
        git(["config", "user.email", "fixture@example.com"], project)
        git(["config", "user.name", "Fixture"], project)
        (project / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        task_dir = project / "security/tasks"
        task_dir.mkdir(parents=True)
        task_specs = [("P0_fixture", target)] + list(additional_tasks or [])
        tasks = []
        for index, (task_id, task_target) in enumerate(task_specs):
            task = task_dir / f"security_{task_id}.sh"
            task_raw_output_path = (additional_raw_output_paths or {}).get(
                task_id,
                raw_output_path
                if index == 0 and raw_output_path is not None
                else f"project_verification_workbench/security-reports/raw_{task_id}.json",
            )
            task_script = (
                "#!/bin/sh\n"
                "touch security-task-executed\n"
                "mkdir -p project_verification_workbench/security-reports\n"
            )
            if writes_raw or index > 0:
                task_script += (
                    "printf '%s' '{\"tool\":{\"name\":\"sh\",\"version\":\"fixture\"},\"findings\":[]}' "
                    f"> {task_raw_output_path}\n"
                )
            task.write_text(task_script, encoding="utf-8")
            task.chmod(0o755)
            descriptor = {
                "task_id": task_id,
                "tool": {"name": tool_name, "version": "fixture", "fallback": "project-native review"},
                "target": task_target,
                "capability": task_capability,
                "network": task_capability == "network",
                "active": task_capability == "active_scan",
                "side_effects": list(task_side_effects or []) if index == 0 else [],
                "raw_output_path": task_raw_output_path,
            }
            write_json(task.with_suffix(".task.json"), descriptor)
            tasks.append(task)
        git(["add", "app.py", "security"], project)
        git(["commit", "-m", "fixture"], project)
        revision = fingerprint(project)

        workbench = project / "project_verification_workbench"
        workbench.mkdir()
        (workbench / "project_report.md").write_text("# Fixture report\n", encoding="utf-8")
        (workbench / "flow_matrix.md").write_text("# Fixture matrix\n", encoding="utf-8")
        profile = profile_payload(revision)
        profile_path = workbench / "project_profile.json"
        write_json(profile_path, profile)
        allowed = [task_capability] if authorized_capabilities is None else authorized_capabilities
        allowed_capabilities = capabilities_payload(*allowed)
        envelope = envelope_payload(
            revision,
            [task_id for task_id, _ in task_specs],
            [task_target for _, task_target in task_specs],
            allowed_capabilities,
            authorized_side_effects,
        )
        receipt = {
            "decision_id": "DEC-S3-FIXTURE",
            "stage": "stage3",
            "decision_type": "security_execution",
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
        stages["stage3"]["gate_state"] = "approved"
        manifest = {
            "schema_version": "3.0",
            "source_revision": {"revision": revision, "dirty": False, "captured_at": "2026-07-12T09:00:00+08:00"},
            "user_intent": {
                "goal": "run local security fixture",
                "target_users": ["fixture owner"],
                "in_scope": ["P0_fixture"],
                "out_of_scope": [],
                "success_criteria": ["runner validates gates"],
                "risk_tolerance": "low",
            },
            "permissions": {
                "write_scope": ["project_verification_workbench"],
                "production_code_changes": False,
                "dependency_install": False,
                "live_calls": task_capability in {"network", "passive_dynamic_scan", "active_scan"},
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
        reports = workbench / "security-reports"
        results = workbench / "stage3_security_results.json"
        env = {
            **os.environ,
            "SECURITY_TASK_DIR": str(task_dir),
            "SECURITY_REPORTS_DIR": str(reports),
            "SECURITY_RESULTS_JSON": str(results),
            "SECURITY_MANIFEST_FILE": str(manifest_path),
            "SECURITY_AUTHORIZATION_FILE": str(receipt_path),
            "SECURITY_ENVELOPE_FILE": str(envelope_path),
            "SECURITY_PROFILE_FILE": str(profile_path),
            "SECURITY_SOURCE_REVISION": revision,
            "SECURITY_MAX_TASKS": str(len(task_specs)),
            "SECURITY_MAX_COMMANDS_PER_TASK": "1",
            "SECURITY_TIMEOUT_SECONDS": "10",
            "PROJECT_VERIFIER_GATE_VALIDATOR": str(VALIDATOR),
            "PROJECT_VERIFIER_PROJECT_ROOT": str(project),
        }
        return tmp, root, project, tasks[0], envelope_path, results, env

    def runner(self, mode, cwd, env=None):
        return run(["bash", str(RUNNER), *([mode] if mode else [])], cwd, env)

    def test_no_argument_is_help_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.runner(None, Path(tmp))
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("Usage:", result.stdout)

    def test_preflight_checks_profile_tools_targets_and_paths_without_dispatch(self):
        tmp, _, project, _, _, _, env = self.make_project()
        with tmp:
            result = self.runner("preflight", project, env)
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("Profile handoff passed", result.stdout)
            self.assertIn("No security task was executed", result.stdout)
            self.assertFalse((project / "security-task-executed").exists())

    def test_preflight_uses_the_skill_validator_when_no_override_is_set(self):
        tmp, _, project, _, _, _, env = self.make_project()
        with tmp:
            default_env = {key: value for key, value in env.items() if key != "PROJECT_VERIFIER_GATE_VALIDATOR"}
            result = self.runner("preflight", project, default_env)
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("Profile handoff passed", result.stdout)

    def test_preflight_rejects_a_validator_inside_the_target_workbench(self):
        tmp, _, project, _, _, _, env = self.make_project()
        untrusted_validator = project / "project_verification_workbench/tools/validate_gate.py"
        untrusted_validator.parent.mkdir(parents=True)
        untrusted_validator.write_text(VALIDATOR.read_text(encoding="utf-8"), encoding="utf-8")
        with tmp:
            result = self.runner("preflight", project, {**env, "PROJECT_VERIFIER_GATE_VALIDATOR": str(untrusted_validator)})
            self.assertNotEqual(0, result.returncode)
            self.assertIn("validator", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_preflight_rejects_an_external_validator_override(self):
        tmp, root, project, _, _, _, env = self.make_project()
        fake_validator = root / "fake_validator.py"
        fake_validator.write_text("raise SystemExit(0)\n", encoding="utf-8")
        with tmp:
            result = self.runner("preflight", project, {**env, "PROJECT_VERIFIER_GATE_VALIDATOR": str(fake_validator)})
            self.assertNotEqual(0, result.returncode)
            self.assertIn("bundled", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_preflight_does_not_require_writing_the_target_workbench(self):
        tmp, _, project, _, _, _, env = self.make_project()
        workbench = project / "project_verification_workbench"
        original_mode = workbench.stat().st_mode
        try:
            workbench.chmod(0o555)
            result = self.runner("preflight", project, env)
        finally:
            workbench.chmod(original_mode)
        with tmp:
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("No security task was executed", result.stdout)
            self.assertFalse((project / "security-task-executed").exists())

    def test_preflight_rejects_a_tmpdir_inside_the_target_project(self):
        tmp, _, project, _, _, _, env = self.make_project()
        workbench = project / "project_verification_workbench"
        with tmp:
            result = self.runner("preflight", project, {**env, "TMPDIR": str(workbench)})
            self.assertNotEqual(0, result.returncode)
            self.assertIn("temporary", result.stdout.lower())
            self.assertFalse(list(workbench.glob(".security_metadata.*")))
            self.assertFalse((project / "security-task-executed").exists())

    def test_preflight_rejects_task_scripts_inside_the_workbench(self):
        tmp, _, project, task, _, _, env = self.make_project()
        workbench_tasks = project / "project_verification_workbench/security/tasks"
        workbench_tasks.mkdir(parents=True)
        copied_task = workbench_tasks / task.name
        copied_task.write_text(task.read_text(encoding="utf-8"), encoding="utf-8")
        copied_metadata = copied_task.with_suffix(".task.json")
        copied_metadata.write_text(task.with_suffix(".task.json").read_text(encoding="utf-8"), encoding="utf-8")
        with tmp:
            result = self.runner("preflight", project, {**env, "SECURITY_TASK_DIR": str(workbench_tasks)})
            self.assertNotEqual(0, result.returncode)
            self.assertIn("source-bound", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_preflight_rejects_task_scripts_inside_git_metadata(self):
        tmp, _, project, task, _, _, env = self.make_project()
        git_tasks = project / ".git/security/tasks"
        git_tasks.mkdir(parents=True)
        copied_task = git_tasks / task.name
        copied_task.write_text(task.read_text(encoding="utf-8"), encoding="utf-8")
        copied_task.with_suffix(".task.json").write_text(
            task.with_suffix(".task.json").read_text(encoding="utf-8"), encoding="utf-8"
        )
        with tmp:
            result = self.runner("preflight", project, {**env, "SECURITY_TASK_DIR": str(git_tasks)})
            self.assertNotEqual(0, result.returncode)
            self.assertIn("source-bound", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_preflight_rejects_task_scripts_inside_nested_git_metadata(self):
        tmp, _, project, task, _, _, env = self.make_project()
        nested_tasks = project / "security/tasks/.git"
        nested_tasks.mkdir(parents=True)
        hidden_task = nested_tasks / "security_P0_hidden.sh"
        hidden_task.write_text(task.read_text(encoding="utf-8"), encoding="utf-8")
        hidden_task.with_suffix(".task.json").write_text(
            json.dumps(
                {
                    **json.loads(task.with_suffix(".task.json").read_text(encoding="utf-8")),
                    "task_id": "P0_hidden",
                    "raw_output_path": "project_verification_workbench/security-reports/raw_P0_hidden.json",
                }
            ),
            encoding="utf-8",
        )
        with tmp:
            result = self.runner("preflight", project, {**env, "SECURITY_MAX_TASKS": "2"})
            self.assertNotEqual(0, result.returncode)
            self.assertIn("git metadata", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_preflight_rejects_ignored_task_scripts(self):
        tmp, _, project, task, _, _, env = self.make_project()
        ignored_tasks = project / "ignored-security/tasks"
        ignored_tasks.mkdir(parents=True)
        (project / ".gitignore").write_text("ignored-security/\n", encoding="utf-8")
        copied_task = ignored_tasks / task.name
        copied_task.write_text(task.read_text(encoding="utf-8"), encoding="utf-8")
        copied_task.with_suffix(".task.json").write_text(
            task.with_suffix(".task.json").read_text(encoding="utf-8"), encoding="utf-8"
        )
        with tmp:
            result = self.runner("preflight", project, {**env, "SECURITY_TASK_DIR": str(ignored_tasks)})
            self.assertNotEqual(0, result.returncode)
            self.assertIn("ignored", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_preflight_missing_tool_records_fallback_without_install_or_dispatch(self):
        tmp, _, project, _, _, _, env = self.make_project(tool_name="missing_scanner_fixture")
        with tmp:
            result = self.runner("preflight", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("missing_scanner_fixture", result.stdout)
            self.assertIn("project-native review", result.stdout)
            self.assertNotIn("install", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_preflight_rejects_invalid_limits_without_dispatch(self):
        tmp, _, project, _, _, _, env = self.make_project()
        with tmp:
            result = self.runner("preflight", project, {**env, "SECURITY_TIMEOUT_SECONDS": "0"})
            self.assertNotEqual(0, result.returncode)
            self.assertIn("SECURITY_MAX_TASKS", result.stdout)
            self.assertFalse((project / "security-task-executed").exists())

    def test_run_requires_each_capability_in_the_current_envelope(self):
        for capability in sorted(CAPABILITIES):
            with self.subTest(capability=capability):
                tmp, _, project, _, _, _, env = self.make_project(
                    task_capability=capability, authorized_capabilities=[]
                )
                with tmp:
                    result = self.runner("run", project, env)
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn(capability, result.stdout)
                    self.assertFalse((project / "security-task-executed").exists())

    def test_run_requires_explicit_authorization_for_a_trusted_custom_bridge(self):
        tmp, root, project, _, envelope_path, _, env = self.make_project()
        with tmp:
            envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
            envelope["scope"]["side_effects"] = []
            approve_envelope(root, envelope)
            result = self.runner("run", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("trusted custom bridge", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_run_rejects_task_side_effects_missing_from_the_decision(self):
        tmp, _, project, _, _, _, env = self.make_project(task_side_effects=["creates_external_record"])
        with tmp:
            result = self.runner("run", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("side effect", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_run_rejects_capability_named_side_effect_without_its_capability(self):
        tmp, _, project, _, _, _, env = self.make_project(
            task_side_effects=["tool_download"],
            authorized_side_effects=[TRUSTED_CUSTOM_BRIDGE_EXECUTION, "tool_download"],
            authorized_capabilities=["offline_read_only"],
        )
        with tmp:
            result = self.runner("run", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("tool_download", result.stdout)
            self.assertFalse((project / "security-task-executed").exists())

    def test_run_rejects_outputs_outside_the_envelope_write_scope(self):
        tmp, root, project, _, envelope_path, _, env = self.make_project()
        with tmp:
            envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
            envelope["scope"]["write_scope"] = ["other"]
            approve_envelope(root, envelope)
            result = self.runner("run", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("write scope", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_run_rejects_swapped_task_target_bindings_before_dispatch(self):
        tmp, root, project, _, envelope_path, _, env = self.make_project(
            additional_tasks=[("P0_second", "local-second")]
        )
        with tmp:
            envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
            envelope["scope"]["targets"] = ["local-second", "local-fixture"]
            approve_envelope(root, envelope)
            result = self.runner("run", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("task-target", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_run_rejects_preexisting_raw_output_before_dispatch(self):
        tmp, _, project, _, _, _, env = self.make_project(writes_raw=False)
        raw_output = project / "project_verification_workbench/security-reports/raw_P0_fixture.json"
        raw_output.parent.mkdir(parents=True)
        raw_output.write_text('{"stale": true}\n', encoding="utf-8")
        with tmp:
            result = self.runner("run", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("must not exist", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_preflight_rejects_raw_output_that_collides_with_results(self):
        tmp, _, project, _, _, _, env = self.make_project(
            raw_output_path="project_verification_workbench/stage3_security_results.json"
        )
        with tmp:
            result = self.runner("preflight", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("collides", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_preflight_rejects_duplicate_raw_outputs_across_tasks(self):
        tmp, _, project, _, _, _, env = self.make_project(
            additional_tasks=[("P0_second", "local-second")],
            additional_raw_output_paths={
                "P0_second": "project_verification_workbench/security-reports/raw_P0_fixture.json"
            },
        )
        with tmp:
            result = self.runner("preflight", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("duplicate", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_preflight_rejects_symlinked_runner_result_stream(self):
        tmp, root, project, _, _, _, env = self.make_project()
        reports = project / "project_verification_workbench/security-reports"
        reports.mkdir()
        external = root / "outside.jsonl"
        (reports / ".security_results.jsonl").symlink_to(external)
        with tmp:
            result = self.runner("preflight", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("new", result.stdout.lower())
            self.assertFalse(external.exists())

    def test_preflight_rejects_hardlinked_runner_result_stream(self):
        tmp, root, project, _, _, _, env = self.make_project()
        reports = project / "project_verification_workbench/security-reports"
        reports.mkdir()
        external = root / "outside.jsonl"
        external.write_text("outside content\n", encoding="utf-8")
        (reports / ".security_results.jsonl").hardlink_to(external)
        with tmp:
            result = self.runner("preflight", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("new", result.stdout.lower())
            self.assertEqual("outside content\n", external.read_text(encoding="utf-8"))
            self.assertFalse((project / "security-task-executed").exists())

    def test_active_scan_rejects_non_local_or_non_isolated_target_before_dispatch(self):
        tmp, _, project, _, _, _, env = self.make_project(
            task_capability="active_scan", target="https://example.invalid"
        )
        with tmp:
            result = self.runner("run", project, env)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("active", result.stdout.lower())
            self.assertIn("local", result.stdout.lower())
            self.assertFalse((project / "security-task-executed").exists())

    def test_run_records_identity_raw_output_and_authorization_id(self):
        tmp, _, project, _, _, results, env = self.make_project()
        with tmp:
            result = self.runner("run", project, env)
            self.assertEqual(0, result.returncode, result.stdout)
            payload = json.loads(results.read_text(encoding="utf-8"))
            task = payload["tasks"][0]
            self.assertEqual("DEC-S3-FIXTURE", task["decision_id"])
            self.assertEqual("sh", task["command_identity"][0])
            self.assertEqual("fixture", task["tool_and_version"]["declared_version"])
            self.assertEqual("none_trusted_custom_bridge", task["execution_isolation"])
            self.assertEqual("local-fixture", task["target"])
            self.assertIn("raw_output_path", task)
            self.assertRegex(task["raw_output_sha256"], r"^[0-9a-f]{64}$")
            self.assertFalse(task["network"])
            self.assertFalse(task["active"])


class SecurityNormalizerTests(unittest.TestCase):
    def normalizer(self):
        return load_module(NORMALIZER, "security_normalizer_v3")

    def make_workspace(self, write_scope=None):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        project = root / "project"
        project.mkdir()
        git(["init"], project)
        git(["config", "user.email", "fixture@example.com"], project)
        git(["config", "user.name", "Fixture"], project)
        (project / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        git(["add", "app.py"], project)
        git(["commit", "-m", "fixture"], project)
        workbench = project / "project_verification_workbench"
        workbench.mkdir()
        revision = fingerprint(project)
        scopes = write_scope or ["project_verification_workbench"]
        envelope = {
            "stage": "stage3",
            "decision_type": "security_execution",
            "scope": {"write_scope": scopes},
        }
        decision_hash = GATE.canonical_object_hash(envelope)
        receipt = {
            "decision_id": "DEC-S3-FIXTURE",
            "decision_envelope_sha256": decision_hash,
            "source_revision": revision,
            "user_choice": "approved",
            "invalidated_at": None,
        }
        manifest = {
            "source_revision": {"revision": revision},
            "permissions": {"write_scope": scopes},
            "decisions": [receipt],
        }
        manifest_path = workbench / "manifest.json"
        envelope_path = workbench / "envelope.json"
        write_json(manifest_path, manifest)
        write_json(envelope_path, envelope)
        return tmp, project, workbench, revision, manifest_path, envelope_path

    def completed_results(self, task_id, input_path, revision, envelope_path, decision_id="DEC-S3-FIXTURE"):
        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
        return {
            "schema_version": "3.0",
            "phase_status": "completed",
            "result_outcome": "pass",
            "source_revision": revision,
            "execution_authorization": {
                "decision_id": decision_id,
                "decision_envelope_sha256": GATE.canonical_object_hash(envelope),
                "current_source_revision": revision,
            },
            "tasks": [
                {
                    "task_id": task_id,
                    "decision_id": decision_id,
                    "exit_code": 0,
                    "raw_output_status": "present",
                    "raw_output_path": str(input_path),
                    "raw_output_sha256": sha256(input_path.read_bytes()).hexdigest(),
                }
            ],
        }

    def test_normalizer_preserves_redacted_raw_evidence_and_exactly_deduplicates(self):
        payload = {
            "tool": {"name": "fixture-tool", "version": "1.0"},
            "findings": [
                {
                    "finding_id": "raw-finding-id-should-not-escape",
                    "category": "secret",
                    "rule_id": "hardcoded-token",
                    "source_location": {"path": "app.py", "line": 7},
                    "severity": "high",
                    "triage_status": "accepted",
                    "affected_user_path": "raw-user-path-should-not-escape",
                    "recommended_action": "raw-recommendation-should-not-escape",
                    "verification_method": "raw-method-should-not-escape",
                    "limitations": ["raw-limitation-should-not-escape"],
                    "evidence": {
                        "match": "sentinel-match-8b708c1c",
                        "api_key": "value-api-123",
                        "password": "value-password-123",
                        "authorization": "value-authorization-123",
                        "secret": "value-secret-123",
                        "secret_key": "value-secret-key-123",
                        "Set-Cookie": "value-cookie-123",
                        "openaiApiKey": "value-provider-api-key-123",
                        "provider_key": "value-provider-key-123",
                        "nested": {
                            "token": "sentinel-token-2d4f7e91",
                            "accessToken": "value-access-token-123",
                            "sessionId": "value-session-id-123",
                            "client-secret": "value-client-secret-123",
                            "private_key": "value-private-key-123",
                            "context": "kept",
                        },
                        "otp": 123456,
                        "trusted": True,
                    },
                    "exploit_preconditions": ["raw-precondition-should-not-escape"],
                },
                {
                    "category": "secret",
                    "rule_id": "hardcoded-token",
                    "source_location": {"path": "app.py", "line": 7},
                    "severity": "high",
                    "evidence": {"raw_secret": "sentinel-raw-secret-5a0ce3d8"},
                },
                {
                    "category": "secret",
                    "rule_id": "other-rule",
                    "source_location": {"path": "app.py", "line": 7},
                    "severity": "high",
                    "evidence": {"secret_value": "sentinel-secret-value-6f1b9a40"},
                },
            ],
        }
        normalized = self.normalizer().normalize(payload, executed_scope=["P0_fixture"])
        self.assertEqual(2, len(normalized["findings"]))
        self.assertEqual(1, normalized["deduplication"]["duplicates_removed"])
        self.assertEqual("needs_review", normalized["findings"][0]["triage_status"])
        serialized = json.dumps(normalized, sort_keys=True)
        for secret in (
            "sentinel-match-8b708c1c",
            "value-api-123",
            "value-password-123",
            "value-authorization-123",
            "value-secret-123",
            "value-secret-key-123",
            "value-cookie-123",
            "value-provider-api-key-123",
            "value-provider-key-123",
            "sentinel-token-2d4f7e91",
            "value-access-token-123",
            "value-session-id-123",
            "value-client-secret-123",
            "value-private-key-123",
            "raw-finding-id-should-not-escape",
            "raw-user-path-should-not-escape",
            "raw-recommendation-should-not-escape",
            "raw-method-should-not-escape",
            "raw-limitation-should-not-escape",
            "raw-precondition-should-not-escape",
            "fixture-tool",
            "hardcoded-token",
            "app.py",
            "123456",
            "sentinel-raw-secret-5a0ce3d8",
            "sentinel-secret-value-6f1b9a40",
        ):
            self.assertNotIn(secret, serialized)
        self.assertNotIn("kept", serialized)
        self.assertNotIn('"otp"', serialized)
        self.assertEqual("needs_review", normalized["findings"][0]["triage_status"])
        self.assertRegex(normalized["findings"][0]["finding_id"], r"^SEC-[0-9a-f]{32}$")
        self.assertIn("category_ref", normalized["findings"][0])
        self.assertIn("rule_ref", normalized["findings"][0])
        self.assertIn("source_ref", normalized["findings"][0]["source_location"])
        self.assertRegex(normalized["findings"][0]["evidence_ref"], r"^EVD-[0-9a-f]{32}$")
        self.assertRegex(normalized["findings"][0]["exploit_preconditions_ref"], r"^PRE-[0-9a-f]{32}$")
        self.assertNotIn("raw_evidence", normalized)
        self.assertRegex(normalized["raw_evidence_ref"], r"^RAW-[0-9a-f]{32}$")
        self.assertNotIn("security_score", normalized)
        self.assertNotIn("exploitability", normalized["findings"][0])
        second = self.normalizer().normalize(payload, executed_scope=["P0_fixture"])
        self.assertNotEqual(normalized["findings"][0]["evidence_ref"], second["findings"][0]["evidence_ref"])
        self.assertNotEqual(normalized["raw_evidence_ref"], second["raw_evidence_ref"])

    def test_normalizer_keeps_distinct_supported_source_locations_separate(self):
        normalized = self.normalizer().normalize(
            {
                "tool": {"name": "fixture-tool", "version": "1.0"},
                "findings": [
                    {
                        "category": "source",
                        "rule_id": "same-rule",
                        "source_location": {"path": "app.py", "line": 7, "column": 3},
                    },
                    {
                        "category": "source",
                        "rule_id": "same-rule",
                        "source_location": {"path": "app.py", "line": 7, "column": 12},
                    },
                ],
            },
            executed_scope=["P0_fixture"],
        )
        self.assertEqual(2, len(normalized["findings"]))
        self.assertEqual(0, normalized["deduplication"]["duplicates_removed"])
        self.assertEqual(3, normalized["findings"][0]["source_location"]["column"])
        self.assertEqual(12, normalized["findings"][1]["source_location"]["column"])

    def test_normalizer_cli_binds_one_raw_input_to_one_completed_task(self):
        payload = {"tool": {"name": "fixture-tool", "version": "1.0"}, "findings": []}
        tmp, project, workbench, revision, manifest_path, envelope_path = self.make_workspace()
        with tmp:
            input_path = workbench / "input.json"
            output_path = workbench / "output.json"
            results_path = workbench / "results.json"
            write_json(input_path, payload)
            write_json(results_path, self.completed_results("P0_fixture", input_path, revision, envelope_path))
            missing_results = run(["python3", str(NORMALIZER), str(input_path), str(output_path)], project)
            self.assertNotEqual(0, missing_results.returncode)
            complete = run(
                ["python3", str(NORMALIZER), str(input_path), str(output_path), str(results_path), "P0_fixture", str(project), str(manifest_path), str(envelope_path)],
                project,
            )
            self.assertEqual(0, complete.returncode, complete.stdout)
            normalized = json.loads(output_path.read_text(encoding="utf-8"))
            serialized = json.dumps(normalized, sort_keys=True)
            self.assertTrue(any("completed authorized task scope" in limitation for limitation in normalized["limitations"]))
            self.assertNotIn("DEC-S3-FIXTURE", serialized)
            self.assertNotIn(str(input_path.resolve()), serialized)
            self.assertRegex(normalized["execution_evidence"]["decision_ref"], r"^DEC-[0-9a-f]{32}$")
            self.assertRegex(normalized["execution_evidence"]["raw_evidence_ref"], r"^RAW-[0-9a-f]{32}$")

    def test_normalizer_cli_rejects_raw_input_for_a_different_completed_task(self):
        payload = {"tool": {"name": "fixture-tool", "version": "1.0"}, "findings": []}
        tmp, project, workbench, revision, manifest_path, envelope_path = self.make_workspace()
        with tmp:
            input_path = workbench / "raw_a.json"
            output_path = workbench / "output.json"
            results_path = workbench / "results.json"
            write_json(input_path, payload)
            results = self.completed_results("P0_a", input_path, revision, envelope_path)
            results["tasks"].append(
                {
                    "task_id": "P0_b",
                    "decision_id": "DEC-S3-FIXTURE",
                    "exit_code": 0,
                    "raw_output_status": "present",
                    "raw_output_path": str(workbench / "raw_b.json"),
                    "raw_output_sha256": "0" * 64,
                }
            )
            write_json(results_path, results)
            mismatch = run(
                ["python3", str(NORMALIZER), str(input_path), str(output_path), str(results_path), "P0_b", str(project), str(manifest_path), str(envelope_path)],
                project,
            )
            self.assertNotEqual(0, mismatch.returncode)
            self.assertIn("raw input", mismatch.stdout.lower())

    def test_normalizer_cli_rejects_task_with_a_different_decision_id(self):
        payload = {"tool": {"name": "fixture-tool", "version": "1.0"}, "findings": []}
        tmp, project, workbench, revision, manifest_path, envelope_path = self.make_workspace()
        with tmp:
            input_path = workbench / "input.json"
            output_path = workbench / "output.json"
            results_path = workbench / "results.json"
            write_json(input_path, payload)
            results = self.completed_results("P0_fixture", input_path, revision, envelope_path, "DEC-S3-CURRENT")
            results["tasks"][0]["decision_id"] = "DEC-S3-STALE"
            write_json(results_path, results)
            mismatch = run(
                ["python3", str(NORMALIZER), str(input_path), str(output_path), str(results_path), "P0_fixture", str(project), str(manifest_path), str(envelope_path)],
                project,
            )
            self.assertNotEqual(0, mismatch.returncode)
            self.assertIn("decision_id", mismatch.stdout.lower())

    def test_normalizer_cli_rejects_changed_raw_output_and_an_external_destination(self):
        payload = {"tool": {"name": "fixture-tool", "version": "1.0"}, "findings": []}
        tmp, project, workbench, revision, manifest_path, envelope_path = self.make_workspace()
        with tmp:
            input_path = workbench / "input.json"
            results_path = workbench / "results.json"
            write_json(input_path, payload)
            write_json(results_path, self.completed_results("P0_fixture", input_path, revision, envelope_path))
            write_json(input_path, {"tool": {"name": "fixture-tool", "version": "1.0"}, "findings": [{"changed": True}]})
            changed = run(
                ["python3", str(NORMALIZER), str(input_path), str(workbench / "output.json"), str(results_path), "P0_fixture", str(project), str(manifest_path), str(envelope_path)],
                project,
            )
            self.assertNotEqual(0, changed.returncode)
            self.assertIn("sha256", changed.stdout.lower())

            write_json(input_path, payload)
            write_json(results_path, self.completed_results("P0_fixture", input_path, revision, envelope_path))
            external = run(
                ["python3", str(NORMALIZER), str(input_path), str(project.parent / "outside.json"), str(results_path), "P0_fixture", str(project), str(manifest_path), str(envelope_path)],
                project,
            )
            self.assertNotEqual(0, external.returncode)
            self.assertIn("workbench", external.stdout.lower())

    def test_normalizer_cli_rejects_output_outside_the_current_write_scope(self):
        payload = {"tool": {"name": "fixture-tool", "version": "1.0"}, "findings": []}
        tmp, project, workbench, revision, manifest_path, envelope_path = self.make_workspace(
            ["project_verification_workbench/security-reports"]
        )
        with tmp:
            reports = workbench / "security-reports"
            reports.mkdir()
            input_path = reports / "input.json"
            results_path = reports / "results.json"
            write_json(input_path, payload)
            write_json(results_path, self.completed_results("P0_fixture", input_path, revision, envelope_path))
            rejected = run(
                ["python3", str(NORMALIZER), str(input_path), str(workbench / "output.json"), str(results_path), "P0_fixture", str(project), str(manifest_path), str(envelope_path)],
                project,
            )
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn("write scope", rejected.stdout.lower())

    def test_clean_normalization_is_limited_to_the_executed_scope(self):
        normalized = self.normalizer().normalize(
            {"tool": {"name": "fixture-tool", "version": "1.0"}, "findings": []},
            executed_scope=["P0_fixture"],
        )
        self.assertEqual("no_issue_found_in_executed_scope", normalized["status"])
        self.assertTrue(any("completed authorized task scope" in limitation for limitation in normalized["limitations"]))
        self.assertNotIn("score", json.dumps(normalized).lower())

    def test_normalizer_requires_an_executed_scope_for_every_result(self):
        with self.assertRaises(ValueError):
            self.normalizer().normalize({"tool": {"name": "fixture-tool", "version": "1.0"}, "findings": []})


if __name__ == "__main__":
    unittest.main()
