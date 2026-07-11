import ast
import json
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
