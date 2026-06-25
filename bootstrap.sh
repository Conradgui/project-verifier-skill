#!/bin/bash
# project-verifier Skill Installer / Linker
# Links this repository's skill into local Agent skill directories.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_SRC="$SCRIPT_DIR/skills/project-verifier"
SKILL_NAME="project-verifier"
DRY_RUN=0

usage() {
    cat <<EOF
Usage: ./bootstrap.sh <agent_name | all> [--dry-run]

Examples:
  ./bootstrap.sh codex --dry-run
  ./bootstrap.sh codex
  ./bootstrap.sh all --dry-run

Supported agents:
  codex       -> \${CODEX_HOME:-\$HOME/.codex}/skills
  claude      -> \$HOME/.claude/skills
  gemini      -> \$HOME/.gemini/skills
  opencode    -> \$HOME/.config/opencode/skills
  antigravity -> \$HOME/.agents/skills
EOF
}

target_root_for() {
    case "$1" in
        codex)
            if [ -n "$CODEX_HOME" ]; then
                printf '%s\n' "$CODEX_HOME/skills"
            else
                printf '%s\n' "$HOME/.codex/skills"
            fi
            ;;
        claude)
            printf '%s\n' "$HOME/.claude/skills"
            ;;
        gemini)
            printf '%s\n' "$HOME/.gemini/skills"
            ;;
        opencode)
            printf '%s\n' "$HOME/.config/opencode/skills"
            ;;
        antigravity)
            printf '%s\n' "$HOME/.agents/skills"
            ;;
        *)
            return 1
            ;;
    esac
}

print_plan() {
    agent="$1"
    target_root="$(target_root_for "$agent")"
    dest_link="$target_root/$SKILL_NAME"

    echo "Agent: $agent"
    echo "  Source: $SKILL_SRC"
    echo "  Target: $dest_link"

    if [ -L "$dest_link" ]; then
        echo "  Existing target: symlink, will replace"
    elif [ -d "$dest_link" ]; then
        echo "  Existing target: directory, real install will stop to avoid moving user files"
    elif [ -e "$dest_link" ]; then
        echo "  Existing target: file, real install will stop"
    else
        echo "  Existing target: none"
    fi
}

link_skill() {
    agent="$1"
    target_root="$(target_root_for "$agent")"
    dest_link="$target_root/$SKILL_NAME"

    print_plan "$agent"

    if [ "$DRY_RUN" -eq 1 ]; then
        echo "  Result: dry run only"
        return 0
    fi

    mkdir -p "$target_root"

    if [ -L "$dest_link" ]; then
        rm "$dest_link"
    elif [ -e "$dest_link" ]; then
        echo "Error: $dest_link already exists and is not a symlink." >&2
        echo "Remove or rename it manually before reinstalling." >&2
        return 1
    fi

    ln -s "$SKILL_SRC" "$dest_link"
    echo "  Result: linked"
}

if [ ! -d "$SKILL_SRC" ] || [ ! -f "$SKILL_SRC/SKILL.md" ]; then
    echo "Error: skill source not found at $SKILL_SRC" >&2
    exit 1
fi

if [ "$#" -eq 0 ]; then
    usage
    exit 1
fi

AGENT=""
for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        all|codex|claude|gemini|opencode|antigravity)
            if [ -n "$AGENT" ]; then
                echo "Error: pass only one agent name or all." >&2
                usage
                exit 1
            fi
            AGENT="$arg"
            ;;
        *)
            echo "Error: unknown argument: $arg" >&2
            usage
            exit 1
            ;;
    esac
done

if [ -z "$AGENT" ]; then
    echo "Error: missing agent name." >&2
    usage
    exit 1
fi

echo "=============================================="
echo " project-verifier Skill Linker / Installer"
echo "=============================================="

if [ "$AGENT" = "all" ]; then
    linked_any=0
    for candidate in codex claude gemini opencode antigravity; do
        target_root="$(target_root_for "$candidate")"
        if [ -d "$target_root" ]; then
            link_skill "$candidate"
            linked_any=1
        fi
    done
    if [ "$linked_any" -eq 0 ]; then
        echo "No existing agent skill directories detected; using Codex default."
        link_skill codex
    fi
else
    link_skill "$AGENT"
fi

echo "=============================================="
if [ "$DRY_RUN" -eq 1 ]; then
    echo "Dry run complete. No files changed."
else
    echo "Setup complete. Restart your Agent CLI or Codex session."
fi
echo "=============================================="
