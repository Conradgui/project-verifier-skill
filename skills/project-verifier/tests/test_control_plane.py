import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from helpers import SKILL_ROOT, load_module, read, run, write_json


VALIDATOR = SKILL_ROOT / "scripts/validate_gate_v3.py"
VALIDATOR_MODULE = load_module(VALIDATOR, "v3_gate")
canonical_object_hash = VALIDATOR_MODULE.canonical_object_hash
requested_limit_is_within = VALIDATOR_MODULE.requested_limit_is_within

DECISION_TEMPLATE = SKILL_ROOT / "templates/decision_envelope_template.json"
PROFILE_TEMPLATE = SKILL_ROOT / "templates/project_profile_template.json"
MANIFEST_TEMPLATE = SKILL_ROOT / "templates/verification_manifest_v3_template.json"


def git(command, cwd):
    result = run(["git", *command], cwd)
    if result.returncode != 0:
        raise AssertionError(result.stdout)
    return result.stdout.strip()


def fingerprint(root):
    result = run(["python3", str(VALIDATOR), "fingerprint", "--root", str(root)], root)
    if result.returncode != 0:
        raise AssertionError(result.stdout)
    return result.stdout.strip()


def source_fixture(root):
    source = root / "source"
    source.mkdir()
    git(["init"], source)
    git(["config", "user.email", "fixture@example.com"], source)
    git(["config", "user.name", "Fixture"], source)
    approved = source / "src" / "approved.py"
    approved.parent.mkdir()
    approved.write_text("VALUE = 1\n", encoding="utf-8")
    git(["add", "src/approved.py"], source)
    git(["commit", "-m", "base"], source)
    return source, fingerprint(source)


def envelope_fixture(base_revision, mode="exact"):
    return {
        "schema_version": "1.0",
        "stage": "stage2",
        "decision_type": "live_e2e",
        "source_policy": {
            "mode": mode,
            "base_revision": base_revision,
            "allowed_fix_paths": ["src/approved.py"] if mode == "approved_fix_scope" else [],
        },
        "scope": {
            "path_ids": ["P0"],
            "targets": ["local"],
            "write_scope": ["project_verification_workbench"],
            "network": False,
            "credential_names": [],
            "sensitive_data": False,
            "side_effects": [],
        },
        "interpretation": {
            "claim": None,
            "baseline": None,
            "dataset_id": None,
            "metric_ids": [],
        },
        "limits": {"max_calls": 2, "timeout_seconds": 10},
    }


def receipt_fixture(envelope):
    return {
        "decision_id": "DEC-S2-001",
        "stage": envelope["stage"],
        "decision_type": envelope["decision_type"],
        "decision_envelope_sha256": canonical_object_hash(envelope),
        "source_revision": envelope["source_policy"]["base_revision"],
        "user_choice": "approved",
        "approved_limits": envelope["limits"],
        "approved_at": "2026-07-11T12:00:00+08:00",
        "invalidated_at": None,
    }


def manifest_fixture(current_revision, receipt):
    stages = {}
    for stage in ("stage1", "stage2", "stage3", "stage4"):
        stages[stage] = {
            "phase_status": "pending",
            "result_outcome": "not_run",
            "execution_scope": "none",
            "claim_eligibility": "none",
            "gate_state": "pending",
            "artifacts": [],
            "blockers": [],
            "recovery_conditions": [],
        }
    stages["stage2"]["gate_state"] = "approved"
    return {
        "schema_version": "3.0",
        "source_revision": {
            "revision": current_revision,
            "dirty": current_revision.startswith("dirty:"),
            "captured_at": "2026-07-11T12:01:00+08:00",
        },
        "user_intent": {
            "goal": "verify fixture",
            "target_users": ["owner"],
            "in_scope": ["P0"],
            "out_of_scope": [],
            "success_criteria": ["gate passes"],
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
            "status": "pending",
            "approved_fields_sha256": None,
        },
        "decisions": [receipt],
    }


def profile_fixture(revision):
    return {
        "schema_version": "3.0",
        "source_identity": {
            "revision": revision,
            "captured_at": "2026-07-11T12:01:00+08:00",
            "repository_type": "git",
        },
        "reviewed_scope": {"in_scope": ["src"], "out_of_scope": [], "reviewed_paths": ["src/approved.py"]},
        "runtimes": ["python3"],
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


def check_command(root, manifest, receipt, envelope, current_revision):
    return [
        "python3",
        str(VALIDATOR),
        "check",
        "--manifest",
        str(manifest),
        "--receipt",
        str(receipt),
        "--envelope",
        str(envelope),
        "--source-revision",
        current_revision,
        "--project-root",
        str(root),
        "--stage",
        "stage2",
        "--decision-type",
        "live_e2e",
        "--limit",
        "max_calls=1",
        "--limit",
        "timeout_seconds=10",
    ]


class DecisionEnvelopeUnitTests(unittest.TestCase):
    def test_json_formatting_does_not_change_envelope_hash(self):
        payload = {"stage": "stage2", "limits": {"timeout_seconds": 10}}
        formatted_copy = json.loads(json.dumps(payload, indent=4))
        self.assertEqual(canonical_object_hash(payload), canonical_object_hash(formatted_copy))

    def test_material_field_change_invalidates_receipt(self):
        approved = {"scope": {"network": False}}
        changed = {"scope": {"network": True}}
        self.assertNotEqual(canonical_object_hash(approved), canonical_object_hash(changed))

    def test_lower_numeric_execution_limit_is_allowed(self):
        self.assertTrue(requested_limit_is_within(10, 5))

    def test_higher_numeric_execution_limit_is_rejected(self):
        self.assertFalse(requested_limit_is_within(10, 11))

    def test_non_numeric_limits_require_exact_equality(self):
        self.assertTrue(requested_limit_is_within("local", "local"))
        self.assertFalse(requested_limit_is_within(["P0"], ["P0", "P1"]))
        self.assertFalse(requested_limit_is_within(True, 1))


class ControlPlaneCliTests(unittest.TestCase):
    def write_gate_files(self, root, source, base_revision, mode="exact"):
        current_revision = fingerprint(source)
        envelope = envelope_fixture(base_revision, mode)
        receipt = receipt_fixture(envelope)
        manifest = manifest_fixture(current_revision, receipt)
        if mode == "approved_fix_scope" and current_revision != base_revision:
            manifest["source_history"] = [
                {
                    "base_revision": base_revision,
                    "current_revision": current_revision,
                    "affected_artifacts_stale": True,
                    "recorded_at": "2026-07-11T12:01:00+08:00",
                }
            ]
        envelope_path = root / "envelope.json"
        receipt_path = root / "receipt.json"
        manifest_path = root / "manifest.json"
        write_json(envelope_path, envelope)
        write_json(receipt_path, receipt)
        write_json(manifest_path, manifest)
        return envelope, receipt, manifest, envelope_path, receipt_path, manifest_path, current_revision

    def test_check_accepts_exact_source_and_lower_requested_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, revision = source_fixture(root)
            _, _, _, envelope, receipt, manifest, current = self.write_gate_files(root, source, revision)
            result = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertEqual(0, result.returncode, result.stdout)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["approved"])
            self.assertEqual(revision, payload["approved_source_revision"])
            self.assertEqual(current, payload["current_source_revision"])

    def test_profile_handoff_accepts_only_confirmed_current_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, revision = source_fixture(root)
            envelope = envelope_fixture(revision)
            receipt = receipt_fixture(envelope)
            manifest_payload = manifest_fixture(revision, receipt)
            manifest_payload["stages"]["stage1"]["phase_status"] = "completed"
            manifest_payload["stages"]["stage1"]["artifacts"] = [
                "project_verification_workbench/project_report.md",
                "project_verification_workbench/flow_matrix.md",
                "project_verification_workbench/project_profile.json",
            ]
            profile = profile_fixture(revision)
            profile_path = source / "project_verification_workbench/project_profile.json"
            profile_path.parent.mkdir()
            write_json(profile_path, profile)
            manifest_payload["project_profile"] = {
                "path": "project_verification_workbench/project_profile.json",
                "status": "confirmed",
                "approved_fields_sha256": canonical_object_hash(profile),
            }
            manifest_path = root / "manifest.json"
            write_json(manifest_path, manifest_payload)
            command = [
                "python3", str(VALIDATOR), "profile", "--manifest", str(manifest_path),
                "--profile", str(profile_path), "--project-root", str(source),
            ]
            accepted = run(command, root)
            self.assertEqual(0, accepted.returncode, accepted.stdout)

            manifest_payload["project_profile"]["status"] = "pending"
            write_json(manifest_path, manifest_payload)
            pending = run(command, root)
            self.assertNotEqual(0, pending.returncode)
            self.assertIn("confirmed", pending.stdout.lower())

            manifest_payload["project_profile"]["status"] = "confirmed"
            profile["source_identity"]["revision"] = "git:" + "0" * 40
            write_json(profile_path, profile)
            manifest_payload["project_profile"]["approved_fields_sha256"] = canonical_object_hash(profile)
            write_json(manifest_path, manifest_payload)
            stale = run(command, root)
            self.assertNotEqual(0, stale.returncode)
            self.assertIn("source revision", stale.stdout.lower())

    def test_check_requires_project_root_for_live_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, revision = source_fixture(root)
            _, _, _, envelope, receipt, manifest, current = self.write_gate_files(root, source, revision)
            command = check_command(source, manifest, receipt, envelope, current)
            index = command.index("--project-root")
            del command[index : index + 2]
            result = run(command, root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("--project-root", result.stdout)

    def test_check_requires_every_approved_limit_to_be_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, revision = source_fixture(root)
            _, _, _, envelope, receipt, manifest, current = self.write_gate_files(root, source, revision)
            command = check_command(source, manifest, receipt, envelope, current)
            command = command[: command.index("--limit")]
            result = run(command, root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("limit keys", result.stdout.lower())

    def test_check_rejects_receipt_with_missing_or_extra_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, revision = source_fixture(root)
            _, receipt, _, envelope, receipt_path, manifest, current = self.write_gate_files(root, source, revision)
            receipt.pop("approved_at")
            write_json(receipt_path, receipt)
            missing = run(check_command(source, manifest, receipt_path, envelope, current), root)
            self.assertNotEqual(0, missing.returncode)
            self.assertIn("exactly", missing.stdout.lower())

            receipt = receipt_fixture(envelope_fixture(revision))
            receipt["unexpected"] = True
            write_json(receipt_path, receipt)
            extra = run(check_command(source, manifest, receipt_path, envelope, current), root)
            self.assertNotEqual(0, extra.returncode)
            self.assertIn("exactly", extra.stdout.lower())

    def test_check_rejects_duplicate_or_missing_manifest_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, revision = source_fixture(root)
            envelope_payload, receipt_payload, manifest_payload, envelope, receipt, manifest, current = self.write_gate_files(root, source, revision)
            manifest_payload["decisions"].append(receipt_payload)
            write_json(manifest, manifest_payload)
            duplicate = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertNotEqual(0, duplicate.returncode)
            self.assertIn("uniquely", duplicate.stdout.lower())

            manifest_payload["decisions"] = []
            write_json(manifest, manifest_payload)
            missing = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertNotEqual(0, missing.returncode)
            self.assertIn("uniquely", missing.stdout.lower())

    def test_check_rejects_invalidated_receipt_or_changed_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, revision = source_fixture(root)
            envelope_payload, receipt_payload, _, envelope, receipt, manifest, current = self.write_gate_files(root, source, revision)
            envelope_payload["scope"]["network"] = True
            write_json(envelope, envelope_payload)
            changed = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertNotEqual(0, changed.returncode)
            self.assertIn("hash", changed.stdout.lower())

            write_json(envelope, envelope_fixture(revision))
            receipt_payload["invalidated_at"] = "2026-07-11T12:02:00+08:00"
            write_json(receipt, receipt_payload)
            invalidated = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertNotEqual(0, invalidated.returncode)
            self.assertIn("invalidated", invalidated.stdout.lower())

    def test_check_rejects_duplicate_requested_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, revision = source_fixture(root)
            _, _, _, envelope, receipt, manifest, current = self.write_gate_files(root, source, revision)
            command = check_command(source, manifest, receipt, envelope, current)
            command.extend(["--limit", "max_calls=2"])
            result = run(command, root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("more than once", result.stdout.lower())

    def test_check_rejects_invalid_state_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, revision = source_fixture(root)
            _, _, manifest_payload, envelope, receipt, manifest, current = self.write_gate_files(root, source, revision)
            manifest_payload["stages"]["stage2"]["result_outcome"] = "unsupported"
            write_json(manifest, manifest_payload)
            result = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("result_outcome", result.stdout.lower())

    def test_exact_source_policy_rejects_changed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, revision = source_fixture(root)
            _, _, _, envelope, receipt, manifest, _ = self.write_gate_files(root, source, revision)
            (source / "src" / "approved.py").write_text("VALUE = 2\n", encoding="utf-8")
            current = fingerprint(source)
            manifest_payload = json.loads(read(manifest))
            manifest_payload["source_revision"]["revision"] = current
            manifest_payload["source_revision"]["dirty"] = True
            write_json(manifest, manifest_payload)
            result = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("exact source policy", result.stdout.lower())

    def test_approved_fix_scope_accepts_allowed_working_tree_change(self):
        self.assert_approved_fix_scope_accepts("working")

    def test_approved_fix_scope_accepts_allowed_staged_change(self):
        self.assert_approved_fix_scope_accepts("staged")

    def test_approved_fix_scope_accepts_allowed_committed_change(self):
        self.assert_approved_fix_scope_accepts("committed")

    def assert_approved_fix_scope_accepts(self, change_kind):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, base_revision = source_fixture(root)
            approved_path = source / "src" / "approved.py"
            approved_path.write_text("VALUE = 2\n", encoding="utf-8")
            if change_kind == "staged":
                git(["add", "src/approved.py"], source)
            elif change_kind == "committed":
                git(["add", "src/approved.py"], source)
                git(["commit", "-m", "allowed fix"], source)
            _, _, _, envelope, receipt, manifest, current = self.write_gate_files(
                root, source, base_revision, "approved_fix_scope"
            )
            result = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertEqual(0, result.returncode, result.stdout)

    def test_approved_fix_scope_rejects_clean_out_of_scope_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, base_revision = source_fixture(root)
            production = source / "config" / "prod.yml"
            production.parent.mkdir()
            production.write_text("enabled: true\n", encoding="utf-8")
            git(["add", "config/prod.yml"], source)
            git(["commit", "-m", "out of scope"], source)
            _, _, _, envelope, receipt, manifest, current = self.write_gate_files(
                root, source, base_revision, "approved_fix_scope"
            )
            result = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("outside approved fix scope", result.stdout.lower())

    def test_approved_fix_scope_rejects_hidden_staged_out_of_scope_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, _ = source_fixture(root)
            production = source / "config" / "prod.yml"
            production.parent.mkdir()
            production.write_text("enabled: false\n", encoding="utf-8")
            git(["add", "config/prod.yml"], source)
            git(["commit", "-m", "add production config"], source)
            base_revision = fingerprint(source)
            production.write_text("enabled: true\n", encoding="utf-8")
            git(["add", "config/prod.yml"], source)
            production.write_text("enabled: false\n", encoding="utf-8")
            _, _, _, envelope, receipt, manifest, current = self.write_gate_files(
                root, source, base_revision, "approved_fix_scope"
            )
            result = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("outside approved fix scope", result.stdout.lower())

    def test_approved_fix_scope_rejects_untracked_out_of_scope_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, base_revision = source_fixture(root)
            (source / "private.env").write_text("not inspected\n", encoding="utf-8")
            _, _, _, envelope, receipt, manifest, current = self.write_gate_files(
                root, source, base_revision, "approved_fix_scope"
            )
            result = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("outside approved fix scope", result.stdout.lower())

    def test_approved_fix_scope_rejects_untracked_path_with_newline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, base_revision = source_fixture(root)
            (source / "src" / "approved.py\nshadow.txt").write_text("not inspected\n", encoding="utf-8")
            _, _, _, envelope, receipt, manifest, current = self.write_gate_files(
                root, source, base_revision, "approved_fix_scope"
            )
            result = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("outside approved fix scope", result.stdout.lower())

    def test_approved_fix_scope_rejects_dirty_base_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, _ = source_fixture(root)
            (source / "src" / "approved.py").write_text("VALUE = 2\n", encoding="utf-8")
            dirty_base = fingerprint(source)
            _, _, _, envelope, receipt, manifest, current = self.write_gate_files(
                root, source, dirty_base, "approved_fix_scope"
            )
            result = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("clean git commit", result.stdout.lower())

    def test_approved_fix_scope_requires_stale_source_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, base_revision = source_fixture(root)
            (source / "src" / "approved.py").write_text("VALUE = 2\n", encoding="utf-8")
            _, _, manifest_payload, envelope, receipt, manifest, current = self.write_gate_files(
                root, source, base_revision, "approved_fix_scope"
            )
            manifest_payload["source_history"] = []
            write_json(manifest, manifest_payload)
            result = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("source_history", result.stdout.lower())

    def test_approved_fix_scope_rejects_non_ancestor_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, _ = source_fixture(root)
            primary_branch = git(["branch", "--show-current"], source)
            git(["checkout", "-b", "other"], source)
            (source / "other.py").write_text("OTHER = True\n", encoding="utf-8")
            git(["add", "other.py"], source)
            git(["commit", "-m", "other branch"], source)
            non_ancestor = git(["rev-parse", "HEAD"], source)
            git(["checkout", primary_branch], source)
            base_revision = f"git:{non_ancestor}"
            _, _, _, envelope, receipt, manifest, current = self.write_gate_files(
                root, source, base_revision, "approved_fix_scope"
            )
            result = run(check_command(source, manifest, receipt, envelope, current), root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("ancestor", result.stdout.lower())

    def test_paths_enforces_write_scope_and_rejects_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, revision = source_fixture(root)
            _, _, _, _, _, manifest, _ = self.write_gate_files(root, source, revision)
            allowed = run(
                ["python3", str(VALIDATOR), "paths", "--manifest", str(manifest), "--changed-file", "project_verification_workbench/report.md"],
                root,
            )
            self.assertEqual(0, allowed.returncode, allowed.stdout)
            outside = run(
                ["python3", str(VALIDATOR), "paths", "--manifest", str(manifest), "--changed-file", "src/app.py"],
                root,
            )
            self.assertNotEqual(0, outside.returncode)
            self.assertIn("write scope", outside.stdout.lower())
            unsafe = run(
                ["python3", str(VALIDATOR), "paths", "--manifest", str(manifest), "--changed-file", "../outside.py"],
                root,
            )
            self.assertNotEqual(0, unsafe.returncode)
            self.assertIn("safe project-relative", unsafe.stdout.lower())

    def test_fingerprint_is_secret_safe_and_ignores_workbench_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, _ = source_fixture(root)
            clean = fingerprint(source)
            workbench = source / "project_verification_workbench"
            workbench.mkdir()
            workbench_secret = "never-print-this-secret"
            (workbench / "run.log").write_text(workbench_secret, encoding="utf-8")
            self.assertEqual(clean, fingerprint(source))
            (source / ".env").write_text(workbench_secret, encoding="utf-8")
            dirty = fingerprint(source)
            self.assertTrue(dirty.startswith("dirty:"))
            self.assertNotIn(workbench_secret, dirty)


class TemplateContractTests(unittest.TestCase):
    def test_v3_manifest_uses_only_four_stages_and_state_dimensions(self):
        manifest = json.loads(read(MANIFEST_TEMPLATE))
        self.assertEqual("3.0", manifest["schema_version"])
        self.assertEqual({"stage1", "stage2", "stage3", "stage4"}, set(manifest["stages"]))
        self.assertNotIn("phases", manifest)
        for state in manifest["stages"].values():
            self.assertTrue({"phase_status", "result_outcome", "execution_scope", "claim_eligibility"} <= set(state))
        self.assertEqual([], manifest["source_history"])
        self.assertEqual(
            {"path", "status", "approved_fields_sha256"},
            set(manifest["project_profile"]),
        )

    def test_templates_are_secret_safe_and_profile_is_stable_facts_only(self):
        envelope = json.loads(read(DECISION_TEMPLATE))
        profile = json.loads(read(PROFILE_TEMPLATE))
        self.assertEqual("1.0", envelope["schema_version"])
        self.assertIn("credential_names", envelope["scope"])
        self.assertEqual("3.0", profile["schema_version"])
        rendered = json.dumps({"envelope": envelope, "profile": profile}).lower()
        self.assertNotIn("secret_value", rendered)
        self.assertNotIn("api_key", rendered)
        self.assertNotIn("password", rendered)
        self.assertNotIn("command", rendered)
        self.assertNotIn("tool_choice", rendered)
        self.assertNotIn("timeout_seconds", rendered)
        self.assertIn("source_identity", profile)
        self.assertIn("trust_boundaries", profile)
        self.assertIn("unknowns", profile)


if __name__ == "__main__":
    unittest.main()
