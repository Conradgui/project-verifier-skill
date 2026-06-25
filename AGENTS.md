# AGENTS.md

This repository contains a Codex-compatible skill package.

## Codex Skill Install Target

- Repository: `https://github.com/Conradgui/project-verifier-skill.git`
- Skill path inside this repository: `skills/project-verifier`
- Skill name: `project-verifier`
- Codex invocation name: `$project-verifier`

When a user asks Codex to install this repository from the repository root URL,
first locate `skills/project-verifier/SKILL.md`, then install that directory as
the skill. Do not install the repository root as the skill directory.

Manual installer equivalent:

```bash
python3 /Users/conrad/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --url https://github.com/Conradgui/project-verifier-skill/tree/main/skills/project-verifier
```

