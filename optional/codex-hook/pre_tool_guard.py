#!/usr/bin/env python3
"""Optional Codex PreToolUse guard for project-verifier receipts."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ACTION_CLASSES = (
    "project_write",
    "dependency_install",
    "live_network",
    "destructive",
    "git_publish",
)
WRITE_TOOLS = {"edit", "write", "multiedit", "apply_patch", "applypatch"}
WORKBENCH_PREFIX = "project_verification_workbench/"


def canonical_action_hash(action_class, tool_name, tool_input):
    payload = {
        "action_class": action_class,
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def extract_paths(tool_input):
    paths = []
    if isinstance(tool_input, dict):
        for key in ("path", "file_path", "filePath", "target_path", "targetPath"):
            value = tool_input.get(key)
            if isinstance(value, str) and value:
                paths.append(value)
        patch = tool_input.get("patch") or tool_input.get("input")
        if isinstance(patch, str):
            paths.extend(re.findall(r"^\+\+\+\s+(?:b/)?(.+)$", patch, flags=re.MULTILINE))
            paths.extend(re.findall(r"^\*\*\* (?:Add|Update|Delete) File:\s+(.+)$", patch, flags=re.MULTILINE))
    return sorted(set(paths))


def relative_path(path, root):
    candidate = Path(path)
    if not candidate.is_absolute():
        return candidate.as_posix().lstrip("./")
    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def only_workbench_paths(paths, root):
    return bool(paths) and all(relative_path(path, root).startswith(WORKBENCH_PREFIX) for path in paths)


def shell_action(command):
    lowered = command.lower()
    if re.search(r"(^|[;&|]\s*)(rm\s|mv\s|dd\s|mkfs\b|truncate\s|git\s+(reset\s+--hard|clean\s+-))", lowered):
        return "destructive"
    if re.search(r"\b(npm|pnpm|yarn|bun)\s+(install|add|remove|update)\b", lowered) or re.search(
        r"\b(pip3?|uv)\s+install\b|\b(poetry\s+add|cargo\s+add|go\s+get|brew\s+install|apt(-get)?\s+install)\b",
        lowered,
    ):
        return "dependency_install"
    if re.search(r"\bgit\s+(commit|push|tag)\b|\bgh\s+(pr\s+create|release\s+create)\b", lowered):
        return "git_publish"
    if re.search(r"\b(curl|wget)\b|\bgh\s+api\b|https?://", lowered):
        return "live_network"
    if re.search(r"(^|\s)(sed\s+-i|tee\s|cp\s)|(^|[^>])>{1,2}[^>]", lowered):
        return "project_write"
    return None


def classify(payload, root):
    tool_name = str(payload.get("tool_name") or payload.get("toolName") or "")
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    lowered = tool_name.lower()
    paths = extract_paths(tool_input)
    if lowered in WRITE_TOOLS:
        return (None if only_workbench_paths(paths, root) else "project_write"), tool_name, tool_input, paths
    if lowered in {"bash", "shell", "exec_command"}:
        command = tool_input.get("command") or tool_input.get("cmd") or "" if isinstance(tool_input, dict) else ""
        return shell_action(str(command)), tool_name, tool_input, paths
    return None, tool_name, tool_input, paths


def decision_output(decision, reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }


def run_json(command):
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if completed.returncode != 0:
        raise ValueError((completed.stderr or completed.stdout or "validator failed").strip())
    return json.loads(completed.stdout)


def authorize(action_class, action_hash, paths, root):
    required = {
        "manifest": os.environ.get("PROJECT_VERIFIER_HOOK_MANIFEST"),
        "receipt": os.environ.get("PROJECT_VERIFIER_HOOK_RECEIPT"),
        "proposal": os.environ.get("PROJECT_VERIFIER_HOOK_PROPOSAL"),
        "validator": os.environ.get("PROJECT_VERIFIER_GATE_VALIDATOR"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError("missing hook authorization inputs: " + ", ".join(missing))
    receipt = json.loads(Path(required["receipt"]).read_text(encoding="utf-8"))
    current_revision = run_json_fingerprint(required["validator"], root)
    command = [
        "python3", required["validator"], "check",
        "--manifest", required["manifest"],
        "--receipt", required["receipt"],
        "--proposal", required["proposal"],
        "--source-revision", current_revision,
        "--phase", str(receipt.get("phase", "")),
        "--decision-type", action_class,
        "--limit", f"action_sha256={action_hash}",
    ]
    run_json(command)
    if action_class == "project_write":
        if not paths:
            raise ValueError("project write has no machine-verifiable target path")
        path_command = ["python3", required["validator"], "paths", "--manifest", required["manifest"]]
        for path in paths:
            path_command.extend(["--changed-file", relative_path(path, root)])
        run_json(path_command)


def run_json_fingerprint(validator, root):
    completed = subprocess.run(
        ["python3", validator, "fingerprint", "--root", str(root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError((completed.stderr or completed.stdout or "cannot fingerprint source").strip())
    return completed.stdout.strip()


def process(payload, root, classify_only=False):
    action_class, tool_name, tool_input, paths = classify(payload, root)
    if action_class is None:
        result = {"action_class": None, "action_sha256": None, "paths": paths}
        return result if classify_only else decision_output("allow", "No guarded high-risk action detected.")
    action_hash = canonical_action_hash(action_class, tool_name, tool_input)
    if classify_only:
        return {"action_class": action_class, "action_sha256": action_hash, "paths": paths}
    try:
        authorize(action_class, action_hash, paths, root)
    except Exception as exc:
        return decision_output("deny", f"project-verifier guard denied {action_class}: {exc}")
    return decision_output("allow", f"Validated current-revision authorization for {action_class}.")


def main():
    parser = argparse.ArgumentParser(description="Classify or guard a Codex PreToolUse event")
    parser.add_argument("--classify", action="store_true", help="Print the action class and hash without authorizing")
    parser.add_argument("--project-root", default=os.environ.get("PROJECT_VERIFIER_PROJECT_ROOT", "."))
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("hook input must be a JSON object")
        output = process(payload, Path(args.project_root), classify_only=args.classify)
    except Exception as exc:
        output = decision_output("deny", f"project-verifier guard input error: {exc}")
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
