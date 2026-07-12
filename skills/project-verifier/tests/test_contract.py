import ast
import json
import re
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from helpers import REPO_ROOT, read, write_json


HISTORICAL_SUITES = (
    REPO_ROOT
    / "project_verifier_iteration_workbench/20260626_skill_hardening/template_behavior_tests.py",
    REPO_ROOT
    / "project_verifier_iteration_workbench/20260628_conditional_eval_gates/workflow_contract_tests.py",
    REPO_ROOT
    / "project_verifier_iteration_workbench/20260629_stage_gate_quality_v2/stage_gate_v2_tests.py",
    REPO_ROOT
    / "project_verifier_iteration_workbench/20260630_lean_core_simplification/lean_core_contract_tests.py",
)
MATRIX_PATH = (
    REPO_ROOT
    / "project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json"
)
V3_TEST_ROOT = REPO_ROOT / "skills/project-verifier/tests"
STAGE1_WORKFLOW = REPO_ROOT / "skills/project-verifier/workflows/stage1_understanding.md"
STAGE2_WORKFLOW = REPO_ROOT / "skills/project-verifier/workflows/stage2_quality.md"
FIXTURE_ROOT = REPO_ROOT / "skills/project-verifier/evals/fixtures"
FIXTURE_IDS = {
    "ai_assisted_mixed",
    "ai_local_backend",
    "ai_missing_credentials",
    "non_ai_cli",
    "partial_e2e_failure",
    "stale_authorization",
}
EVALS_PATH = REPO_ROOT / "skills/project-verifier/evals/evals.json"
EVIDENCE_REFERENCE = re.compile(r"^(?P<path>[^:]+):(?P<start>\d+)(?:-(?P<end>\d+))?$")
ALLOWED_STATUSES = {"pending", "ported", "covered_by", "retired_contract"}


def test_ids(paths):
    ids = []
    for path in paths:
        tree = ast.parse(read(path), filename=str(path))
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        ids.extend(
            f"{relative_path}::{node.name}"
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        )
    return ids


class HarnessTests(unittest.TestCase):
    def test_json_helper_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.json"
            write_json(path, {"value": 1})
            self.assertIn('"value": 1', read(path))


class MigrationMatrixTests(unittest.TestCase):
    def setUp(self):
        self.matrix = json.loads(read(MATRIX_PATH))

    def test_matrix_schema_and_retired_allowlist(self):
        self.assertEqual("1.0", self.matrix["schema_version"])
        self.assertEqual([], self.matrix["retired_contract_allowlist"])

    def test_matrix_enumerates_every_historical_test_exactly_once(self):
        expected = Counter(test_ids(HISTORICAL_SUITES))
        actual = Counter(entry.get("legacy_id") for entry in self.matrix["entries"])
        self.assertEqual(expected, actual)

    def test_matrix_statuses_and_v3_targets_are_valid(self):
        v3_test_ids = set(test_ids(sorted(V3_TEST_ROOT.glob("test_*.py"))))
        retired_allowlist = set(self.matrix["retired_contract_allowlist"])

        for entry in self.matrix["entries"]:
            legacy_id = entry["legacy_id"]
            status = entry["status"]
            v3_test = entry.get("v3_test")
            with self.subTest(legacy_id=legacy_id):
                self.assertIn(status, ALLOWED_STATUSES)
                if not v3_test:
                    self.assertEqual("pending", status)
                if status in {"ported", "covered_by"}:
                    self.assertIn(v3_test, v3_test_ids)
                if status == "retired_contract":
                    self.assertIn(legacy_id, retired_allowlist)


class Stage1UnderstandingContractTests(unittest.TestCase):
    def setUp(self):
        self.workflow = read(STAGE1_WORKFLOW)

    def test_stage1_defines_source_backed_artifacts_and_coverage_limits(self):
        for phrase in (
            "project_verification_workbench/project_report.md",
            "project_verification_workbench/flow_matrix.md",
            "project_verification_workbench/project_profile.json",
            "reviewed files",
            "excluded directories",
            "unreviewed areas",
            "coverage limitations",
            "repository-wide inventory",
            "risk-based deep reading",
            "must not claim line-by-line-complete coverage",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.workflow)

    def test_stage1_binds_paths_to_evidence_and_embeds_four_mermaid_views(self):
        for phrase in (
            "Every P0, P1, and P2 path must include source evidence",
            "| Path ID | Priority |",
            "Architecture",
            "Module/data flow",
            "User flow",
            "Failure recovery",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.workflow)
        self.assertGreaterEqual(self.workflow.count("```mermaid"), 4)
        self.assertIn("Mermaid evidence legend", self.workflow)
        self.assertIn("Every non-`unknown` relationship", self.workflow)
        self.assertGreaterEqual(
            self.workflow.count("| Relationship | Evidence | Status | Rationale |"),
            4,
        )

    def test_stage1_completion_contract_blocks_unconfirmed_or_stale_handoffs(self):
        for phrase in (
            "stage1.artifacts",
            "project_profile.status",
            "confirmed",
            "source_identity.revision",
            "Stage 2, Stage 3, and Stage 4 must refuse to consume the Profile",
            "`stages.stage1.phase_status` is not `completed`",
            "`approved_fields_sha256` is missing",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.workflow)

    def test_stage1_profile_and_single_confirmation_preserve_epistemic_boundaries(self):
        for phrase in (
            "facts",
            "inferences",
            "unknowns",
            "feature-level AI classification",
            "exactly one concise user confirmation",
            "goal",
            "P0 paths",
            "factual corrections",
            "interpretation-changing unknowns",
            "README rewriting is a separate optional output",
            "approved_fields_sha256",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.workflow)

    def test_stage1_prohibits_unsafe_or_out_of_scope_actions(self):
        for phrase in (
            "Do not read secret values",
            "Do not install dependencies",
            "Do not access networks",
            "Do not write production source",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.workflow)

    def test_fixture_descriptors_hold_only_evidence_backed_stage1_fields(self):
        descriptors = {
            path.parent.name: json.loads(read(path))
            for path in sorted(FIXTURE_ROOT.glob("*/fixture.json"))
        }
        self.assertEqual(FIXTURE_IDS, set(descriptors))

        for fixture_id, descriptor in descriptors.items():
            with self.subTest(fixture_id=fixture_id):
                self.assertEqual(fixture_id, descriptor["id"])
                for field in (
                    "feature_classification",
                    "entry_points",
                    "path_ids",
                    "trust_boundaries",
                    "expected_capabilities",
                ):
                    self.assertIn(field, descriptor)
                    self.assertIsInstance(descriptor[field], list)
                    for item in descriptor[field]:
                        self.assertIn("evidence", item)
                        self.assertTrue(item["evidence"])
                        for reference in item["evidence"]:
                            match = EVIDENCE_REFERENCE.fullmatch(reference)
                            self.assertIsNotNone(match, reference)
                            evidence_path = FIXTURE_ROOT / fixture_id / match["path"]
                            self.assertTrue(evidence_path.is_file(), evidence_path)
                            last_line = int(match["end"] or match["start"])
                            self.assertGreaterEqual(int(match["start"]), 1)
                            self.assertLessEqual(
                                last_line,
                                len(read(evidence_path).splitlines()),
                                reference,
                            )
                if "features" in descriptor:
                    classifications = {
                        item["feature_id"]: item["classification"]
                        for item in descriptor["feature_classification"]
                    }
                    self.assertEqual(descriptor["features"], classifications)

        mixed = descriptors["ai_assisted_mixed"]
        self.assertEqual("AI-assisted", mixed["features"]["optional_generation"])
        self.assertTrue(
            all(reference.startswith("app.py:") for reference in mixed["feature_classification"][1]["evidence"])
        )
        self.assertIn("optional generation path is AI-assisted", read(EVALS_PATH))


class Stage2QualityContractTests(unittest.TestCase):
    def test_stage2_separates_offline_quality_from_authorized_smoke_and_live_e2e(self):
        workflow = read(STAGE2_WORKFLOW)
        normalized_workflow = re.sub(r"\s+", " ", workflow)
        for phrase in (
            "project-native lint, build, unit, and integration commands",
            "fixture/mock oracles",
            "does not execute offline unit tests itself",
            "stage2 / live_e2e",
            "confirmed Stage 1 Profile",
            "decision-envelope authorization",
            "exactly one concise selected-quality-scope user gate",
            "production fixes, dependency installations, live calls, sensitive data, or changed side effects",
            "Pass rate is not code coverage",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized_workflow)
