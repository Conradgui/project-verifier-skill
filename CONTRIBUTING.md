# Contributing to AI-Agent Project Verifier

Thank you for your interest in contributing to the AI-Agent Project Verifier! We welcome contributions from developers, product managers, and open-source enthusiasts.

## How to Contribute

### 1. Reporting Bugs & Suggesting Enhancements
*   Please search the issue tracker first to ensure the topic hasn't been discussed yet.
*   If you find a bug, open an issue using the bug report template, explaining the steps to reproduce, actual behavior, and expected behavior.
*   If you want to suggest an feature, explain the use case and how it benefits the overall verification workflow.

### 2. Submitting Pull Requests
*   Fork the repository and create your branch from `main` or `dev`.
*   If you've added new features, update the corresponding workflow instruction file in `skills/project-verifier/workflows/`.
*   Ensure all Markdown links match local directory relative offsets cleanly.
*   Write clear, descriptive commit messages.
*   Submit your pull request and describe your changes.

## Development Setup

The skill relies on native Python scripts and standard Unix/Mac shell environments:
1.  Verify Python 3.10+ is installed.
2.  Install `pytest` and `vcrpy` locally to test templates changes:
    ```bash
    pip install pytest vcrpy
    ```

## Coding Conventions
*   Keep the core skill instructions (`SKILL.md` and `workflows/*.md`) highly structured with explicit step instructions for the LLM agents.
*   For python scripts (under `templates/`), use standard libraries where possible to limit the installation overhead for users running the verification suite.
*   For script outputs, prioritize writing JSON output to files rather than stdout to keep the agent's context window token-efficient.

## License
By contributing, you agree that your contributions will be licensed under the project's MIT License.
